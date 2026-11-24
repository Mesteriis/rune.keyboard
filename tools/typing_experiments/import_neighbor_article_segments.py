"""Recover full source-article segment exclusions for historical neighbor rows."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/ci'))
import register_neighbor_history as parent
from holdout_ledger import keys_for, pack_ledger, validate_ledger
from import_word_epoch_article_segments import collect

ENTRY = 'historical-neighbor-recovery-article-segments-v1'
SEGMENTS_SHA = '42e84204f5d6e690bb5c309ad5f082f4e97d3aaaa3ddca5c54e17420171a6d02'


def collect_source(ids, batches):
    if not ids:
        raise ValueError('NEIGHBOR_SEGMENT_EMPTY_SOURCE')
    found = collect({'source': ids}, batches)['source']
    if not found:
        raise ValueError('NEIGHBOR_SEGMENT_EMPTY')
    return found


def partition_articles(rows):
    article_ids = {row['article'] for row in rows}
    shard_ids = {shard: {row['article'] for row in rows if row['shard'] == shard} for shard in range(11, 18)}
    if sum(map(len, shard_ids.values())) != len(article_ids):
        raise ValueError('NEIGHBOR_SEGMENT_CROSS_SHARD_ARTICLE')
    return article_ids, shard_ids


def check():
    ledger = validate_ledger(json.loads(parent.LEXICAL.read_bytes()))
    expected_parent, _ = parent.entries()
    if [item for item in ledger['entries'] if item['id'] == parent.ENTRY] != [expected_parent]:
        raise ValueError('NEIGHBOR_SEGMENT_PARENT')
    entries = [item for item in ledger['entries'] if item['id'] == ENTRY]
    if len(entries) != 1:
        raise ValueError('NEIGHBOR_SEGMENT_MISSING')
    entry = entries[0]
    segments = entry['keys']['sentence']
    digest = hashlib.sha256(json.dumps(segments, separators=(',', ':')).encode()).hexdigest()
    if (entry.get('usage') != 'historical-source-exclusion' or entry.get('rowCount') != 2426 or
            entry.get('parentEntries') != [parent.ENTRY] or entry['keys']['article'] != expected_parent['keys']['article'] or
            len(segments) != 279056 or digest != SEGMENTS_SHA):
        raise ValueError('NEIGHBOR_SEGMENT_IDENTITY')
    for name, digest in entry['bindings'].items():
        path = ROOT / name
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(ROOT) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('NEIGHBOR_SEGMENT_DRIFT')
    return len(segments)


def run(base_path, output):
    import pyarrow.parquet as parquet
    base_path, output = Path(base_path), Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'):
        raise ValueError('NEIGHBOR_SEGMENT_OUTPUT')
    base_raw = base_path.read_bytes()
    stored = json.loads(base_raw)
    logical = validate_ledger(copy.deepcopy(stored))
    expected_parent, _ = parent.entries()
    if [item for item in logical['entries'] if item['id'] == parent.ENTRY] != [expected_parent]:
        raise ValueError('NEIGHBOR_SEGMENT_PARENT')
    if any(item['id'] == ENTRY for item in logical['entries']):
        raise ValueError('NEIGHBOR_SEGMENT_EXISTS')
    rows, parent_bindings = parent.inputs()
    manifest = json.loads((parent.FIXTURE / 'manifest.json').read_bytes())
    sources = manifest['sources']
    paths = [Path(__file__).resolve(), ROOT / 'tools/typing_experiments/import_word_epoch_article_segments.py',
             ROOT / 'tools/typing_experiments/import_word_epoch_text_segments.py',
             ROOT / 'tools/typing_experiments/independent_corpus_guard.py',
             ROOT / 'tools/typing_experiments/holdout_ledger.py']
    bindings = parent_bindings | {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    article_ids, shard_ids = partition_articles(rows)
    article_keys = sorted(keys_for([{'article': article} for article in article_ids], 'article'))
    if article_keys != expected_parent['keys']['article']:
        raise ValueError('NEIGHBOR_SEGMENT_ARTICLE_SCOPE')
    all_segments = set()
    for shard in range(11, 18):
        relative = f'build/typing-ranker-v2/ru-{shard:04d}.parquet'
        source = sources[relative]
        path = ROOT / relative
        with path.open('rb') as stream:
            before = hashlib.file_digest(stream, 'sha256').hexdigest()
        if path.stat().st_size != source['bytes'] or before != source['sha256']:
            raise ValueError('NEIGHBOR_SEGMENT_SOURCE_IDENTITY')
        ids = shard_ids[shard]
        def batches():
            for batch in parquet.ParquetFile(path).iter_batches(batch_size=128, columns=['id', 'text']):
                yield batch.column(0).to_pylist(), batch.column(1).to_pylist()
        all_segments.update(collect_source(ids, batches()))
        with path.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != before:
                raise ValueError('NEIGHBOR_SEGMENT_SOURCE_DRIFT')
    entry = dict(id=ENTRY, usage='historical-source-exclusion', rowCount=len(article_ids),
                 keys={'article': article_keys, 'sentence': sorted(all_segments)}, missingAxes=[],
                 bindings=bindings, parentEntries=[parent.ENTRY],
                 notes='All source article segments under historical delimiters; not linguistic sentence validation.')
    logical['entries'].append(entry)
    stored['entries'].append(pack_ledger(logical)['entries'][-1])
    if validate_ledger(copy.deepcopy(stored)) != logical:
        raise ValueError('NEIGHBOR_SEGMENT_STORAGE')
    if (base_path.read_bytes() != base_raw or
            any(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest for name, digest in bindings.items())):
        raise ValueError('NEIGHBOR_SEGMENT_INPUT_DRIFT')
    receipt = dict(scope='disclosed-neighbor-source-segments-not-qualification', articles=len(article_ids),
                   segmentKeys=len(all_segments), baseLedgerSha256=hashlib.sha256(base_raw).hexdigest(),
                   sourceShards={name: value['sha256'] for name, value in sorted(sources.items())},
                   modelCalls=0, globalCoverageComplete=False)
    output.mkdir(parents=True, mode=0o700)
    for name, value in (('ledger.json', stored), ('receipt.json', receipt)):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'articles': receipt['articles'], 'segmentKeys': receipt['segmentKeys']}, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check and args.base is None and args.output is None:
        print(json.dumps({'segmentKeys': check(), 'independentQualification': False}))
    elif not args.check and args.base is not None and args.output is not None:
        run(args.base, args.output)
    else:
        parser.error('choose --check or --base with --output')
