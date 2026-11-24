#!/usr/bin/env python3
"""Trace all historical unknown text fragments to complete public source tokens."""
import argparse
import bisect
import hashlib
import json
from pathlib import Path
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/ci'), str(ROOT / 'tools/morphology')]
import control_ledger as control
from audit_selector_text_exposure import PARTS, WORD
from audit_wordrank_source_boundaries import TOKEN
from independent_corpus_guard import selector_segments
from ranker import PymorphyLexicon
import historical_model_fixtures as fixtures

HELPERS = (
    'tools/typing_experiments/audit_shared_text_source_boundaries.py',
    'tools/typing_experiments/audit_selector_text_exposure.py',
    'tools/typing_experiments/audit_wordrank_source_boundaries.py',
    'tools/typing_experiments/independent_corpus_guard.py',
    'tools/typing_experiments/control_ledger.py',
    'tools/typing_experiments/holdout_ledger.py',
    'tools/typing_experiments/source_identities.py',
    'tools/morphology/ranker.py',
    'tools/ci/historical_model_fixtures.py',
    'tools/ci/historical_model_sources.py',
    'tools/ci/historical_data_fixtures.py',
)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def derive(parts, sources, lexicon):
    if set(parts) != set(PARTS):
        raise ValueError('ALL_TEXT_PARTITIONS')
    cache = {}
    unknown = {}
    for part in PARTS:
        if not isinstance(parts[part], list) or any(
            not isinstance(r, dict) or set(r) != {'articleId', 'text'} or
            not isinstance(r['articleId'], str) or not isinstance(r['text'], str) or not r['text']
            for r in parts[part]
        ):
            raise ValueError('ALL_TEXT_RECORD')
        ids = [r['articleId'] for r in parts[part]]
        if len(ids) != len(set(ids)):
            raise ValueError('ALL_TEXT_DUPLICATE_ARTICLE')
        words = {m.group().casefold() for r in parts[part] for m in WORD.finditer(r['text'])}
        for word in words:
            if word not in cache:
                cache[word] = bool(lexicon.analyses(word))
        unknown[part] = {word for word in words if not cache[word]}
    unknown_words = set().union(*(unknown[part] for part in PARTS))
    seen = set()
    dedup = {}
    partial = set()
    for part in PARTS:
        for record in parts[part]:
            article, fragment = record['articleId'], record['text']
            if not isinstance(article, str) or article not in sources or not isinstance(fragment, str) or not fragment:
                raise ValueError('ALL_TEXT_SOURCE')
            source = unicodedata.normalize('NFC', sources[article] or '')
            clean = ' '.join(WORD.findall(source.lower()))
            if not clean.startswith(fragment):
                raise ValueError('ALL_TEXT_MISMATCH')
            original = list(WORD.finditer(source))
            if [m.group().lower() for m in original] != WORD.findall(source.lower()):
                raise ValueError('ALL_TEXT_CASE_MAPPING')
            tokens = list(TOKEN.finditer(source))
            starts = [m.start() for m in tokens]
            segments = list(selector_segments(source))
            segment_starts = [start for _, start in segments]
            for i, match in enumerate(WORD.finditer(fragment)):
                word = match.group().casefold()
                if word not in unknown_words:
                    continue
                if match.end() == len(fragment) and len(fragment) < len(clean) and clean[len(fragment)].isalpha():
                    partial.add(word)
                    continue
                if i >= len(original) or original[i].group().casefold() != word:
                    raise ValueError('ALL_TEXT_WORD_MAPPING')
                item = original[i]
                index = bisect.bisect_right(starts, item.start()) - 1
                if index < 0 or tokens[index].end() < item.end():
                    raise ValueError('ALL_TEXT_TOKEN_MAPPING')
                token = tokens[index]
                seen.add(word)
                if token.group().casefold() == word:
                    continue
                seg_index = bisect.bisect_right(segment_starts, token.start()) - 1
                if seg_index < 0:
                    raise ValueError('ALL_TEXT_SEGMENT')
                segment, start = segments[seg_index]
                position = token.start() - start
                if position < 0 or segment[position:position + len(token.group())] != token.group():
                    raise ValueError('ALL_TEXT_SEGMENT')
                prefix = segment[max(0, position - 128):position].lstrip()
                identity = f'{part}:{article}:{token.start()}:{token.end()}:{i}'
                row = {'id': digest(identity.encode()), 'partition': part, 'language': 'ru',
                       'article': article, 'prefix': prefix, 'typed': token.group(),
                       'expectedSpelling': token.group(), 'head': word, 'wordOrdinal': i,
                       'sourceStart': token.start(), 'sourceEnd': token.end()}
                if identity in dedup and dedup[identity] != row:
                    raise ValueError('ALL_TEXT_DUPLICATE')
                dedup[identity] = row
    if unknown_words != seen | partial:
        raise ValueError('ALL_TEXT_COVERAGE')
    return sorted(dedup.values(), key=lambda r: r['id']), {'unknownSurfaces': len(unknown_words),
        'completeSeen': len(seen), 'truncatedSeen': len(partial), 'contexts': len(dedup)}


def run(parquet, output):
    import pyarrow.parquet as pq
    parquet, output = Path(parquet), Path(output)
    if output.exists() or not output.resolve().is_relative_to(ROOT / 'build'):
        raise ValueError('ALL_TEXT_OUTPUT')
    lock_path = ROOT / 'tools/model/rune-text-0.2/source-lock.json'
    control_path = ROOT / 'tools/typing_experiments/control-ledger.json'
    analyzer_path = Path(__file__).resolve()
    lock = lock_path.read_bytes()
    control_bytes = control_path.read_bytes()
    analyzer_bytes = analyzer_path.read_bytes()
    helper_hashes = {name: digest((ROOT / name).read_bytes()) for name in HELPERS}
    expected = json.loads(lock)['wikipediaContext']['files']['ru-0007.parquet']
    with parquet.open('rb') as f:
        source_sha = hashlib.file_digest(f, 'sha256').hexdigest()
    if source_sha != expected['sha256'] or parquet.stat().st_size != expected['bytes']:
        raise ValueError('ALL_TEXT_SOURCE_IDENTITY')
    _, archive = fixtures.verify()
    names = {part: f'build/typing-word-ranking/data/{part}-text.jsonl' for part in PARTS}
    parts = {part: [json.loads(line) for line in archive[name].splitlines()] for part, name in names.items()}
    wanted = {r['articleId'] for records in parts.values() for r in records}
    sources = {}
    for batch in pq.ParquetFile(parquet).iter_batches(batch_size=128, columns=['id', 'text']):
        for ident, text in zip(batch.column(0).to_pylist(), batch.column(1).to_pylist(), strict=True):
            ident = str(ident)
            if ident in wanted:
                if ident in sources:
                    raise ValueError('ALL_TEXT_DUPLICATE_SOURCE')
                sources[ident] = text
    if set(sources) != wanted:
        raise ValueError('ALL_TEXT_MISSING_SOURCE')
    dictionary = PymorphyLexicon(cache_size=16384)
    dictionary_receipt = dictionary.receipt()
    rows, counts = derive(parts, sources, dictionary)
    raw = ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in rows).encode()
    ledger = control.validate(json.loads(control_bytes))
    blocked = {key for entry in ledger['entries'] for key in entry.get('surfaceKeys', [])}
    keys = {control.surface_key('ru', r['typed']) for r in rows}
    counts.update(distinctFullForms=len(keys), alreadyExcluded=len(keys & blocked), newSurfaces=len(keys - blocked))
    with parquet.open('rb') as f:
        if hashlib.file_digest(f, 'sha256').hexdigest() != source_sha:
            raise ValueError('ALL_TEXT_SOURCE_DRIFT')
    _, current_archive = fixtures.verify()
    if (lock_path.read_bytes() != lock or control_path.read_bytes() != control_bytes or
            analyzer_path.read_bytes() != analyzer_bytes or dictionary.receipt() != dictionary_receipt or
            any(current_archive[name] != archive[name] for name in names.values()) or
            any(digest((ROOT / name).read_bytes()) != value for name, value in helper_hashes.items())):
        raise ValueError('ALL_TEXT_INPUT_DRIFT')
    output.mkdir(parents=True, mode=0o700)
    (output / 'contexts.jsonl').write_bytes(raw)
    receipt = {'scope': 'disclosed-historical-all-text-source-boundary', 'independentQualification': False,
        'sourceSha256': source_sha, 'sourceLockSha256': digest(lock), 'contextsSha256': digest(raw),
        'archiveTextSha256': {part: digest(archive[name]) for part, name in names.items()},
        'dictionary': dictionary_receipt, 'controlLedgerSha256': digest(control_bytes),
        'analyzerSha256': digest(analyzer_bytes), 'helperSha256': helper_hashes, 'counts': counts}
    (output / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    return counts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parquet', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.parquet, args.output), sort_keys=True))
