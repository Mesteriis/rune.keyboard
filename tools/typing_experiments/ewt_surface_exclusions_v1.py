"""Exact public EWT word surfaces for strict family-disjointness checks.

Hashes are unsalted and reversible. These are surfaces, not inferred lemmas;
they do not establish complete morphology or qualify a corpus.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

import control_ledger as control
import english_family_keys as english
import import_english_ewt_exposure as ewt

LOCK_SHA = '380668545aa5b37008eea1708bd9da9375fb1825d3f1b5ee76a6a469accc4709'
FIXTURE = Path(__file__).with_name('ewt-surface-exclusions-v1.json')
FIXTURE_SHA = '3a70fef09c85a7cdf08da6c43c65bfacfb859de67dd971c04a8f80b29f0ecc4e'
SCHEMA = 'rune-ewt-exact-english-surfaces-v1'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def generate(data, lock_raw):
    if sha(lock_raw) != LOCK_SHA:
        raise ValueError('EWT_SURFACE_LOCK')
    lock = json.loads(lock_raw)
    # Authenticate the whole source and the article/sentence structure first.
    ewt.rows_from_sources(data, lock['files'])
    keys = set()
    rows = 0
    for name in sorted(data):
        for line in data[name].decode('utf-8').splitlines():
            if not line or line.startswith('#'):
                continue
            columns = line.split('\t')
            if len(columns) != 10:
                raise ValueError('EWT_SURFACE_TOKEN_SCHEMA')
            if re.fullmatch(r'[1-9][0-9]*', columns[0]) is None:
                if re.fullmatch(r'[1-9][0-9]*(?:-[1-9][0-9]*|\.[1-9][0-9]*)', columns[0]) is None:
                    raise ValueError('EWT_SURFACE_TOKEN_ID')
                continue
            try:
                english.key_for(columns[1])  # Validate supported word shape, not a lemma claim.
            except ValueError:
                continue
            keys.add(control.surface_key('en', columns[1]))
            rows += 1
    return dict(schema=SCHEMA, sourceLockSha256=LOCK_SHA, tokenRows=rows,
                keys=sorted(keys), completeFamilyCoverage=False, independentQualification=False)


def load(raw=None):
    raw = FIXTURE.read_bytes() if raw is None else raw
    if sha(raw) != FIXTURE_SHA or sha(ewt.LOCK.read_bytes()) != LOCK_SHA:
        raise ValueError('EWT_SURFACE_IDENTITY')
    value = json.loads(raw)
    keys = value.get('keys')
    if (value.get('schema') != SCHEMA or value.get('sourceLockSha256') != LOCK_SHA or
            value.get('tokenRows') != 216055 or value.get('completeFamilyCoverage') is not False or
            value.get('independentQualification') is not False or not isinstance(keys, list) or
            len(keys) != 16913 or keys != sorted(set(keys)) or
            any(not isinstance(k, str) or re.fullmatch('[0-9a-f]{64}', k) is None for k in keys)):
        raise ValueError('EWT_SURFACE_SCHEMA')
    return frozenset(keys)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-directory', type=Path)
    parser.add_argument('--generate', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        if args.source_directory is not None or args.generate is not None:
            raise ValueError('EWT_SURFACE_SCOPE')
        print(json.dumps({'surfaceKeys':len(load()), 'independentQualification':False}))
        return
    if args.source_directory is None or args.generate is None:
        raise ValueError('EWT_SURFACE_SCOPE')
    lock = ewt.LOCK.read_bytes()
    files = json.loads(lock)['files']
    data = {name:(args.source_directory/name).read_bytes() for name in files}
    helpers = [Path(__file__).resolve(), Path(ewt.__file__).resolve(), Path(english.__file__).resolve(),
               Path(control.__file__).resolve(), Path(__file__).with_name('holdout_ledger.py'),
               Path(__file__).with_name('source_identities.py')]
    before = {path:sha(path.read_bytes()) for path in helpers}
    value = generate(data, lock)
    if (ewt.LOCK.read_bytes() != lock or any((args.source_directory/name).read_bytes() != raw for name,raw in data.items()) or
            any(sha(path.read_bytes()) != digest for path,digest in before.items())):
        raise ValueError('EWT_SURFACE_INPUT_DRIFT')
    with args.generate.open('xb') as stream:
        stream.write((json.dumps(value, sort_keys=True, indent=2)+'\n').encode())
    print(json.dumps({'surfaceKeys':len(value['keys']), 'tokenRows':value['tokenRows']}))


if __name__ == '__main__':
    main()
