"""Recheck disclosed retrieval rows with the source-attestation diagnostic.

The public source is read in place; this tool writes no dataset or model and
never certifies a fresh holdout. Historical source windows are reconstructed,
not claimed to be originally stored annotations.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'tools/ci'), str(ROOT/'tools/morphology')]
import register_retrieval_history as fixture
from audit_selector_text_exposure import WORD
import selector_text_preflight_files_v1 as target


def inspect(rows, articles, lexicon, generator):
    prepared = []
    counts = Counter()
    for original in rows:
        if (not isinstance(original, dict) or original.get('partition') != 'test' or
                original.get('language') != 'ru' or not isinstance(original.get('articleId'), str) or
                original['articleId'] not in articles or not isinstance(original.get('prefix'), str) or
                not isinstance(original.get('expectedSpelling'), str)):
            raise ValueError('RETRIEVAL_ATTESTATION_ROW')
        text = articles[original['articleId']]
        if not isinstance(text, str):
            raise ValueError('RETRIEVAL_ATTESTATION_SOURCE')
        text = unicodedata.normalize('NFC', text)
        matches = []
        for sentence, start in target.guard.selector_segments(text):
            for match in WORD.finditer(sentence):
                if (match.group() == original['expectedSpelling'] and
                        sentence[max(0,match.start()-128):match.start()].lstrip() == original['prefix']):
                    matches.append((sentence, start, match))
        if len(matches) != 1:
            counts['unmatchedOrAmbiguousOriginal'] += 1
            continue
        sentence, start, match = matches[0]
        if not target.guard.whole_selector_token(text, sentence, start, match, {}):
            counts['partialSourceToken'] += 1
            continue
        families = sorted({a.lemma for a in lexicon.analyses(original['expectedSpelling'])})
        if not families:
            counts['dictionaryUnresolved'] += 1
            continue
        row = original.copy()
        target.guard.attach_selector_source(row, text, sentence, start, match, {})
        row['families'] = families
        prepared.append(row)
    attest = target.attest_word_rows({'train':[], 'dev':[], 'test':prepared}, articles, lexicon, generator)
    if attest['rows'] != len(prepared) or attest['verified'] != len(prepared):
        raise ValueError('RETRIEVAL_ATTESTATION_MISMATCH')
    return prepared, dict(sorted(counts.items())), attest


def run(source):
    import pyarrow.parquet as parquet
    from ranker import PymorphyLexicon
    source = Path(source)
    lock_raw = target.SOURCE_LOCK.read_bytes()
    expected = json.loads(lock_raw)['wikipediaContext']['files']['ru-0007.parquet']
    if source.stat().st_size != expected['bytes'] or target.file_sha(source) != expected['sha256']:
        raise ValueError('RETRIEVAL_ATTESTATION_SOURCE_IDENTITY')
    rows, _, parent_bindings = fixture.inputs()
    wanted = {row['articleId'] for row in rows}
    articles = {}
    for batch in parquet.ParquetFile(source).iter_batches(batch_size=128, columns=['id','text']):
        for ident, text in zip(batch.column(0).to_pylist(), batch.column(1).to_pylist(), strict=True):
            ident = str(ident)
            if ident in wanted:
                if ident in articles:
                    raise ValueError('RETRIEVAL_ATTESTATION_DUPLICATE_ARTICLE')
                articles[ident] = text
    if set(articles) != wanted:
        raise ValueError('RETRIEVAL_ATTESTATION_MISSING_ARTICLE')
    paths = {name:Path(target.__file__).with_name(name) for name in target.HELPERS}
    paths['qualification-v2/generate_corpus.py'] = target.selector.GENERATOR
    paths['ranker.py'] = ROOT/'tools/morphology/ranker.py'
    paths['audit_retrieval_row_attestation.py'] = Path(__file__).resolve()
    helpers = {name:target.file_sha(path) for name,path in paths.items()}
    lexicon = PymorphyLexicon(cache_size=16384)
    dictionary = json.dumps(lexicon.receipt(), sort_keys=True, separators=(',', ':')).encode()
    generator = target.selector.load_generator()
    prepared, refused, attestation = inspect(rows, articles, lexicon, generator)
    if not prepared:
        raise ValueError('RETRIEVAL_ATTESTATION_EMPTY')
    probe = prepared[0] | {'families':['несуществующая_семья']}
    negative = target.attest_word_rows({'train':[], 'dev':[], 'test':[probe]}, articles, lexicon, generator)
    if negative['dictionaryMismatch'] != 1:
        raise ValueError('RETRIEVAL_ATTESTATION_NEGATIVE')
    if (target.SOURCE_LOCK.read_bytes() != lock_raw or target.file_sha(source) != expected['sha256'] or
            fixture.inputs()[2] != parent_bindings or any(target.file_sha(p) != helpers[n] for n,p in paths.items()) or
            json.dumps(lexicon.receipt(), sort_keys=True, separators=(',', ':')).encode() != dictionary):
        raise ValueError('RETRIEVAL_ATTESTATION_DRIFT')
    return dict(scope='disclosed-retrieval-source-attestation-not-qualification', independentQualification=False,
        historicalRows=len(rows), sourceArticles=len(articles), prepared=len(prepared), preparationRefusals=refused,
        sourceAttestation=attestation, forgedFamilyRefused=negative['dictionaryMismatch'], sourceSha256=expected['sha256'],
        sourceLockSha256=target.sha(lock_raw), parentBindings=parent_bindings, helperSha256=helpers,
        dictionaryReceiptSha256=hashlib.sha256(dictionary).hexdigest())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.source), sort_keys=True))
