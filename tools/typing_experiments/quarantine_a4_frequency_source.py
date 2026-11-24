#!/usr/bin/env python3
"""Quarantine all article identities from the disclosed A4 frequency shard."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform

import a4_abbreviation_frequency as source
import control_ledger as control
import holdout_ledger as lexical

ROOT = Path(__file__).resolve().parents[2]
ENTRY = 'public-a4-frequency-source-wikipedia-0011-v1'


def digest(keys):
    return hashlib.sha256(''.join(key + '\n' for key in keys).encode('ascii')).hexdigest()


def article_keys(values):
    seen = set()
    for value in values:
        article = str(value)
        if not article.isascii() or not article.isdecimal() or int(article) <= 0:
            raise ValueError('A4_SOURCE_ARTICLE_ID')
        article = str(int(article))
        if article in seen: raise ValueError('A4_SOURCE_DUPLICATE_ARTICLE')
        seen.add(article)
    if not seen: raise ValueError('A4_SOURCE_EMPTY')
    rows = [{'article': article, 'language': 'ru'} for article in seen]
    left = sorted(lexical.keys_for(rows, 'article'))
    right = sorted({control.article_key(row) for row in rows})
    if len(left) != len(seen) or len(right) != len(seen): raise ValueError('A4_SOURCE_KEY_COLLISION')
    return left, right


def run(path):
    import pyarrow.parquet as parquet
    path = Path(path).resolve(strict=True)
    lock_hash, helper_hash = source.sha(source.LOCK), source.sha(__file__)
    source_helper_hash = source.sha(source.__file__)
    dependencies = (Path(control.__file__).resolve(), Path(lexical.__file__).resolve(),
                    ROOT / 'tools/typing_experiments/source_identities.py',
                    ROOT / 'tools/typing_experiments/conversation_split_checks.py')
    dependency_hashes = {str(p.relative_to(ROOT)): source.sha(p) for p in dependencies}
    lock = json.loads(source.LOCK.read_text()); shard = next(x for x in lock['shards'] if x['name'] == source.SHARD)
    if path.stat().st_size != shard['bytes'] or source.sha(path) != shard['sha256']:
        raise ValueError('A4_SOURCE_IDENTITY')
    def ids():
        for batch in parquet.ParquetFile(path).iter_batches(batch_size=1024, columns=['id']):
            yield from batch.column(0).to_pylist()
    left, right = article_keys(ids())
    if len(left) != 92622: raise ValueError('A4_SOURCE_COUNT')
    if (path.stat().st_size != shard['bytes'] or source.sha(path) != shard['sha256'] or
            source.sha(source.LOCK) != lock_hash or source.sha(__file__) != helper_hash or
            source.sha(source.__file__) != source_helper_hash or
            any(source.sha(ROOT / name) != digest for name, digest in dependency_hashes.items())):
        raise ValueError('A4_SOURCE_DRIFT')
    meta = {'schema':1,'sourceSha256':shard['sha256'],'sourceLockSha256':lock_hash,
        'helperSha256':helper_hash,'frequencyHelperSha256':source_helper_hash,'articles':len(left),
        'dependencySha256':dependency_hashes,
        'lexicalKeysSha256':digest(left),'controlKeysSha256':digest(right),
        'pythonVersion':platform.python_version(),'pyarrowVersion':importlib.metadata.version('pyarrow'),
        'sourceDecoderAttested':False,'independentlyQualified':False}
    return meta, left, right


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args();output=args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('A4_SOURCE_OUTPUT')
    meta,left,right=run(args.source);output.mkdir(parents=True,mode=0o700)
    for name,value in (('manifest.json',meta),('lexical-keys.json',left),('control-keys.json',right)):
        (output/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'articles':len(left),'independentlyQualified':False}))


if __name__ == '__main__':main()
