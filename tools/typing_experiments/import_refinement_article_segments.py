"""Quarantine historical refinement source-article segments from a pinned shard."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/ci'))
import historical_data_fixtures as data
import import_word_epoch_article_segments as article_segments
import import_word_epoch_text_segments as text_segments
from holdout_ledger import keys_for, pack_ledger, validate_ledger

PREFIX = 'public-refinement-article-segments-'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def partition_sets(manifest, parents):
    sets = {}
    for part in ('train', 'dev', 'test'):
        ids = manifest['partitions'][part]['articles']
        if not ids or any(not isinstance(i, str) or not i.isascii() or not i.isdecimal() for i in ids) or len(set(ids)) != len(ids):
            raise ValueError('REFINEMENT_ARTICLE_MANIFEST')
        sets[part] = set(ids)
        parent = parents.get('public-ranker-history-' + part)
        if parent is None or not keys_for([{'article': i} for i in ids], 'article') <= set(parent['keys'].get('article', [])):
            raise ValueError('REFINEMENT_ARTICLE_PARENT')
    return sets


def build(base, shard, read_batches):
    base = validate_ledger(base); parents = {e['id']: e for e in base['entries']}
    if any(key.startswith(PREFIX) for key in parents):
        raise ValueError('REFINEMENT_ARTICLE_ALREADY_IMPORTED')
    paths = {Path(__file__).resolve(), Path(article_segments.__file__).resolve(), Path(text_segments.__file__).resolve(),
             ROOT / 'tools/ci/historical_data_fixtures.py', ROOT / 'tools/typing_experiments/holdout_ledger.py',
             ROOT / 'tools/typing_experiments/recover_ranker_sources.py', ROOT / 'tools/model/rune-text-0.2/source-lock.json',
             ROOT / 'tools/typing_experiments/frozen_sources/manifest.json'}
    paths.update(data.DATA / name for name in ('manifest.json', 'files.tar.gz', 'articles.jsonl', 'NOTICE.md'))
    bindings = {str(p.relative_to(ROOT)): digest(p) for p in paths}
    lock = json.loads((ROOT / 'tools/model/rune-text-0.2/source-lock.json').read_text())['wikipediaContext']['files']['ru-0007.parquet']
    if shard.stat().st_size != lock['bytes'] or digest(shard) != lock['sha256']:
        raise ValueError('REFINEMENT_ARTICLE_SOURCE_IDENTITY')
    payload = data.verify(); manifest = json.loads(payload['typing-refinement/data/manifest.json'])
    if manifest['sourceSha256'] != lock['sha256']:
        raise ValueError('REFINEMENT_ARTICLE_MANIFEST_SOURCE')
    sets = partition_sets(manifest, parents)
    found = article_segments.collect(sets, read_batches(shard))
    if digest(shard) != lock['sha256'] or any(digest(ROOT / k) != v for k, v in bindings.items()):
        raise ValueError('REFINEMENT_ARTICLE_INPUT_DRIFT')
    result = copy.deepcopy(base); counts = {}
    for part, ids in sets.items():
        parent = parents['public-ranker-history-' + part]
        if not found[part]: raise ValueError('REFINEMENT_ARTICLE_EMPTY')
        result['entries'].append({'id': PREFIX + part, 'usage': 'historical-source-exclusion',
            'rowCount': len(ids), 'keys': {'article': sorted(keys_for([{'article': i} for i in ids], 'article')),
            'sentence': sorted(found[part])}, 'missingAxes': [], 'bindings': bindings,
            'sourceSha256': lock['sha256'], 'parentEntries': [parent['id']],
            'parentEntrySha256': hashlib.sha256(json.dumps(parent, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest(),
            'notes': 'Pinned source articles segmented by historical delimiters; not verified linguistic sentences.'})
        counts[part] = {'articles': len(ids), 'distinctSegments': len(found[part])}
    return validate_ledger(result), {'purpose': 'HISTORICAL_REFINEMENT_ARTICLE_SEGMENTS_NOT_QUALIFICATION',
        'counts': counts, 'sourceSha256': lock['sha256'], 'modelCalls': 0, 'globalCoverageComplete': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True); parser.add_argument('--shard', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); output = args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'): raise ValueError('FRESH_BUILD_OUTPUT_REQUIRED')
    import pyarrow.parquet as parquet
    def batches(path):
        for batch in parquet.ParquetFile(path).iter_batches(batch_size=128, columns=['id', 'text']):
            yield batch.column(0).to_pylist(), batch.column(1).to_pylist()
    raw = args.base.read_bytes(); base = json.loads(raw)
    ledger, receipt = build(copy.deepcopy(base), args.shard, batches)
    if args.base.read_bytes() != raw: raise ValueError('REFINEMENT_ARTICLE_INPUT_DRIFT')
    stored = copy.deepcopy(base); stored['entries'].extend(pack_ledger(ledger)['entries'][-3:])
    if validate_ledger(copy.deepcopy(stored)) != ledger: raise ValueError('REFINEMENT_ARTICLE_STORAGE_MISMATCH')
    output.mkdir(parents=True, mode=0o700)
    for name, value in (('ledger.json', stored), ('receipt.json', receipt)):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps(receipt['counts'], sort_keys=True))


if __name__ == '__main__': main()
