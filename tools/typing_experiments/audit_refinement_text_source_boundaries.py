#!/usr/bin/env python3
"""Trace refinement historical unknown text fragments to complete public source tokens."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/ci'), str(ROOT / 'tools/morphology')]
import control_ledger as control
from audit_selector_text_exposure import PARTS
from audit_all_text_source_boundaries import derive
from ranker import PymorphyLexicon
import historical_data_fixtures as fixtures

HELPERS = (
    'tools/typing_experiments/audit_all_text_source_boundaries.py',
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


def run(parquet, output):
    import pyarrow.parquet as pq
    parquet, output = Path(parquet), Path(output)
    if output.exists() or not output.resolve().is_relative_to(ROOT / 'build'):
        raise ValueError('REFINEMENT_SOURCE_OUTPUT')
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
        raise ValueError('REFINEMENT_SOURCE_SOURCE_IDENTITY')
    archive = fixtures.verify()
    names = {part: f'typing-refinement/data/{part}-text.jsonl' for part in PARTS}
    parts = {part: [json.loads(line) for line in archive[name].splitlines()] for part, name in names.items()}
    wanted = {r['articleId'] for records in parts.values() for r in records}
    sources = {}
    for batch in pq.ParquetFile(parquet).iter_batches(batch_size=128, columns=['id', 'text']):
        for ident, text in zip(batch.column(0).to_pylist(), batch.column(1).to_pylist(), strict=True):
            ident = str(ident)
            if ident in wanted:
                if ident in sources:
                    raise ValueError('REFINEMENT_SOURCE_DUPLICATE_SOURCE')
                sources[ident] = text
    if set(sources) != wanted:
        raise ValueError('REFINEMENT_SOURCE_MISSING_SOURCE')
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
            raise ValueError('REFINEMENT_SOURCE_SOURCE_DRIFT')
    current_archive = fixtures.verify()
    if (lock_path.read_bytes() != lock or control_path.read_bytes() != control_bytes or
            analyzer_path.read_bytes() != analyzer_bytes or dictionary.receipt() != dictionary_receipt or
            any(current_archive[name] != archive[name] for name in names.values()) or
            any(digest((ROOT / name).read_bytes()) != value for name, value in helper_hashes.items())):
        raise ValueError('REFINEMENT_SOURCE_INPUT_DRIFT')
    output.mkdir(parents=True, mode=0o700)
    (output / 'contexts.jsonl').write_bytes(raw)
    receipt = {'scope': 'disclosed-historical-refinement-text-source-boundary', 'independentQualification': False,
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
