"""Recover public article identities, not v6 corpus rows or qualification.

Supply ten pinned Parquet shards, or use --download-temporary to process one at
 a time. Source text is never read or written. Existing output is never replaced.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.request

import holdout_ledger

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / 'tools/typing_experiments/available-v6-article-origin-v1/source-lock.json'
LEDGER = ROOT / 'tools/typing_experiments/holdout-ledger.json'
SELECTOR = ROOT / 'tools/typing_experiments/frozen_sources/prepare_60f079e28a18fd98.py'
REVISION = 'a634f78b1c435397c07001e175fa74cc4ad5e775'
ENTRY = 'public-right-context-available-v6-'


def sha_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def read_lock():
    raw = LOCK.read_bytes()
    lock = json.loads(raw)
    if (lock.get('schema') != 1 or lock.get('repository') != 'wikimedia/wikipedia' or
            lock.get('revision') != REVISION or lock.get('snapshot') != '20231101.ru' or
            lock.get('historicalSelectorSha256') != sha_file(SELECTOR)):
        raise ValueError('V6_ARTICLE_LOCK')
    shards = lock.get('shards')
    if not isinstance(shards, list) or len(shards) != 10:
        raise ValueError('V6_ARTICLE_LOCK')
    for index, item in enumerate(shards, 11):
        name = f'{index:04d}.parquet'
        if (set(item) != {'name', 'repositoryPath', 'bytes', 'sha256'} or
                item['name'] != name or item['repositoryPath'] != '20231101.ru/train/' + name or
                type(item['bytes']) is not int or item['bytes'] <= 0 or
                not re.fullmatch(r'[0-9a-f]{64}', item['sha256'])):
            raise ValueError('V6_ARTICLE_LOCK')
    return lock, raw


def target_index(ledger):
    entries = {e['id']: e for e in ledger['entries']}
    target = {}
    for part in ('calibration', 'holdout'):
        keys = entries[ENTRY + part]['keys']['article']
        if not keys:
            raise ValueError('V6_ARTICLE_EMPTY_TARGET')
        for key in keys:
            if key in target:
                raise ValueError('V6_ARTICLE_PARTITION_OVERLAP')
            target[key] = part
    return target


def verify_historical_source_bindings(lock, ledger):
    for shard in lock['shards']:
        name = shard['name']
        observed = set()
        for entry in ledger['entries']:
            for path, digest in entry.get('bindings', {}).items():
                if Path(path).name in (name, 'ru-' + name):
                    observed.add(digest)
        if observed != {shard['sha256']}:
            raise ValueError('V6_ARTICLE_HISTORICAL_SOURCE_BINDING:' + name)


def scan_shard(path, shard, targets, seen):
    import pyarrow.parquet as parquet

    path = Path(path)
    if path.stat().st_size != shard['bytes'] or sha_file(path) != shard['sha256']:
        raise ValueError('V6_ARTICLE_SOURCE_IDENTITY')
    matches = []
    count = 0
    for batch in parquet.ParquetFile(path).iter_batches(batch_size=256, columns=['id']):
        for value in batch.column(0).to_pylist():
            article = str(value)
            if not article.isascii() or not article.isdecimal() or not 1 <= len(article) <= 20:
                raise ValueError('V6_ARTICLE_SOURCE_ID')
            key = next(iter(holdout_ledger.keys_for([{'article': article}], 'article')))
            count += 1
            if key not in targets:
                continue
            if key in seen:
                raise ValueError('V6_ARTICLE_DUPLICATE_SOURCE')
            seen.add(key)
            matches.append(dict(partition=targets[key], article=str(int(article)),
                                articleKey=key, shard=shard['name']))
    if path.stat().st_size != shard['bytes'] or sha_file(path) != shard['sha256']:
        raise ValueError('V6_ARTICLE_SOURCE_DRIFT')
    return matches, count


def download(shard, destination):
    url = f'https://huggingface.co/datasets/wikimedia/wikipedia/resolve/{REVISION}/' + shard['repositoryPath']
    count = 0
    with urllib.request.urlopen(url, timeout=60) as response, Path(destination).open('xb') as output:
        while chunk := response.read(1024 * 1024):
            count += len(chunk)
            if count > shard['bytes']:
                raise ValueError('V6_ARTICLE_DOWNLOAD_SIZE')
            output.write(chunk)
    if count != shard['bytes']:
        raise ValueError('V6_ARTICLE_DOWNLOAD_SIZE')


def recover(source_dir=None, download_temporary=False):
    if (source_dir is None) == (not download_temporary):
        raise ValueError('V6_ARTICLE_SOURCE_MODE')
    lock, lock_bytes = read_lock()
    ledger_sha = sha_file(LEDGER)
    helpers = [Path(__file__).resolve(), Path(holdout_ledger.__file__).resolve(),
               ROOT / 'tools/typing_experiments/source_identities.py',
               ROOT / 'tools/typing_experiments/conversation_split_checks.py', SELECTOR]
    bindings = {str(p.relative_to(ROOT)): sha_file(p) for p in helpers}
    ledger = holdout_ledger.load_ledger(LEDGER)
    verify_historical_source_bindings(lock, ledger)
    targets = target_index(ledger)
    seen, rows, source_counts = set(), [], {}
    with tempfile.TemporaryDirectory(prefix='rune-v6-shards-') as directory:
        temp = Path(directory)
        for shard in lock['shards']:
            path = (temp if download_temporary else Path(source_dir)) / shard['name']
            try:
                if download_temporary:
                    download(shard, path)
                matched, count = scan_shard(path, shard, targets, seen)
                rows.extend(matched)
                source_counts[shard['name']] = dict(sourceRows=count, matches=len(matched))
                print('shard', shard['name'], 'source rows', count, 'matched articles', len(matched), flush=True)
            finally:
                if download_temporary:
                    path.unlink(missing_ok=True)
    if seen != set(targets):
        raise ValueError('V6_ARTICLE_INCOMPLETE:' + str(len(set(targets) - seen)))
    if (LOCK.read_bytes() != lock_bytes or sha_file(LEDGER) != ledger_sha or
            any(sha_file(ROOT / name) != digest for name, digest in bindings.items())):
        raise ValueError('V6_ARTICLE_INPUT_DRIFT')
    rows.sort(key=lambda r: (r['partition'], int(r['article'])))
    report = dict(schema=1, scope='public-article-identity-not-corpus-reproduction',
        sourceLockSha256=hashlib.sha256(lock_bytes).hexdigest(), ledgerSha256=ledger_sha,
        helperSha256=bindings, pyarrowVersion=importlib.metadata.version('pyarrow'),
        sourceDecoderAttested=False, sourceCounts=source_counts,
        partitionCounts={p: sum(r['partition'] == p for r in rows) for p in ('calibration', 'holdout')},
        independentQualification=False, corpusRowsRecovered=False)
    return rows, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--source-dir', type=Path)
    source.add_argument('--download-temporary', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise ValueError('V6_ARTICLE_OUTPUT_EXISTS')
    rows, report = recover(args.source_dir, args.download_temporary)
    raw = ''.join(json.dumps(row, sort_keys=True) + '\n' for row in rows).encode()
    report['articlesSha256'] = hashlib.sha256(raw).hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.v6-articles-', dir=output.parent) as d:
        stage = Path(d) / 'result'
        stage.mkdir()
        (stage / 'articles.jsonl').write_bytes(raw)
        (stage / 'receipt.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
        os.rename(stage, output)
    print(json.dumps({'partitions': report['partitionCounts'], 'articlesSha256': report['articlesSha256'],
                      'independentQualification': False}, sort_keys=True))


if __name__ == '__main__':
    main()
