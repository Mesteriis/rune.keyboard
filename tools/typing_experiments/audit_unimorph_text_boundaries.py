"""Source-bound standalone-word projection for disclosed historical text."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/ci'))
import historical_data_fixtures as data
import historical_model_fixtures as model
from selector_text_preflight_v1 import source_fragment
from source_identities import unsupported_surface_key

SOURCE_SHA = '39b59952cd92a148b301f4d2b3ae1fb71e4caab987c6abe278f0dbdf0b01bb88'
UNIMORPH_SHA = '6c13f849fc12844b23f46e70a02a45a2f537e60c62c8ffd8798bdff3991dc880'
WORD = re.compile('[а-яё]+', re.IGNORECASE)
TEXT_PARENTS = tuple('public-refinement-text-families-' + part for part in ('train', 'dev', 'test')) + tuple(
    'public-word-epoch-text-families-wordrank-' + part for part in ('train', 'dev', 'test')) + (
    'public-word-epoch-text-families-extra-test',)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def file_sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def specs():
    archived = data.verify()
    _, word = model.verify()
    result = {}
    for part in ('train', 'dev', 'test'):
        result['public-refinement-text-families-' + part] = archived['typing-refinement/data/' + part + '-text.jsonl']
        result['public-word-epoch-text-families-wordrank-' + part] = word['build/typing-word-ranking/data/' + part + '-text.jsonl']
    result[TEXT_PARENTS[-1]] = archived['typing-extra-epochs/data/test-text.jsonl']
    return result


def source_matches(parent, rows, sources, unknown, dictionary_keys):
    """Choose one reproducible source occurrence for each parent/surface key."""
    result = {}
    for row in rows:
        article, fragment = row['articleId'], row['text']
        if article not in sources or not isinstance(sources[article], str):
            raise ValueError('UNIMORPH_TEXT_SOURCE')
        source = unicodedata.normalize('NFC', sources[article])
        clean = ' '.join(WORD.findall(source.lower()))
        if not clean.startswith(fragment):
            raise ValueError('UNIMORPH_TEXT_MISMATCH')
        original = list(WORD.finditer(source))
        if [m.group().lower() for m in original] != WORD.findall(source.lower()):
            raise ValueError('UNIMORPH_TEXT_CASE_MAPPING')
        for ordinal, match in enumerate(WORD.finditer(fragment)):
            if match.end() == len(fragment) and len(fragment) < len(clean) and clean[len(fragment)].isalpha():
                continue
            if ordinal >= len(original) or original[ordinal].group().lower() != match.group():
                raise ValueError('UNIMORPH_TEXT_WORD_MAPPING')
            original_match = original[ordinal]
            key = unsupported_surface_key(match.group())
            if key not in unknown or key not in dictionary_keys or source_fragment(source, original_match.start(), original_match.end()):
                continue
            record = dict(parent=parent, article=article, ordinal=ordinal, surfaceKey=key,
                          sourceStart=original_match.start(), sourceEnd=original_match.end())
            if key not in result or (article, ordinal) < (result[key]['article'], result[key]['ordinal']):
                result[key] = record
    return [result[key] for key in sorted(result)]


def capture(parquet, unimorph):
    import pyarrow
    import pyarrow.parquet as pq
    if pyarrow.__version__ != '25.0.1':
        raise ValueError('UNIMORPH_TEXT_DECODER_VERSION')
    helpers = (Path(__file__).resolve(), ROOT / 'tools/typing_experiments/selector_text_preflight_v1.py',
               ROOT / 'tools/typing_experiments/source_identities.py')
    helper_hashes = {path: file_sha(path) for path in helpers}
    dictionary_bytes = Path(unimorph).read_bytes()
    if file_sha(parquet) != SOURCE_SHA or sha(dictionary_bytes) != UNIMORPH_SHA:
        raise ValueError('UNIMORPH_TEXT_SOURCE_IDENTITY')
    keys = set()
    for line in dictionary_bytes.decode('utf-8').splitlines():
        fields = line.split('\t')
        if len(fields) == 3:
            lemma = unicodedata.normalize('NFC', fields[0]).casefold()
            form = unicodedata.normalize('NFC', fields[1]).casefold()
            if re.fullmatch('[а-яё]{1,32}', lemma) and (key := unsupported_surface_key(form)):
                keys.add(key)
    archives = specs()
    parts = {name: [json.loads(line) for line in raw.splitlines()] for name, raw in archives.items()}
    wanted = {row['articleId'] for rows in parts.values() for row in rows}
    sources = {}
    for batch in pq.ParquetFile(parquet).iter_batches(batch_size=128, columns=['id', 'text']):
        for article, text in zip(batch.column(0).to_pylist(), batch.column(1).to_pylist(), strict=True):
            if article in wanted:
                if article in sources: raise ValueError('UNIMORPH_TEXT_DUPLICATE')
                sources[article] = text
    if set(sources) != wanted: raise ValueError('UNIMORPH_TEXT_MISSING')
    ledger_path = ROOT / 'tools/typing_experiments/holdout-ledger.json'
    raw_ledger = ledger_path.read_bytes()
    entries = {entry['id']: entry for entry in json.loads(raw_ledger)['entries']}
    records = []
    for name in TEXT_PARENTS:
        records.extend(source_matches(name, parts[name], sources, set(entries[name]['unsupportedSurfaceKeys']), keys))
    if (file_sha(parquet) != SOURCE_SHA or sha(Path(unimorph).read_bytes()) != UNIMORPH_SHA or
            ledger_path.read_bytes() != raw_ledger or specs() != archives or
            any(file_sha(path) != digest for path, digest in helper_hashes.items())):
        raise ValueError('UNIMORPH_TEXT_INPUT_DRIFT')
    return dict(schema=1, sourceSha256=SOURCE_SHA, unimorphSha256=UNIMORPH_SHA,
                archiveSha256={name: sha(raw) for name, raw in archives.items()}, records=records)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parquet', type=Path, required=True)
    parser.add_argument('--unimorph', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(capture(args.parquet, args.unimorph), ensure_ascii=False, sort_keys=True, indent=2))
