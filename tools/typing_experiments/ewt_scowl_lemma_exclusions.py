"""Quarantine exact public EWT lemmas also present in the pinned SCOWL 5desk list.

The unsalted keys are reversible; they are not anonymization. This is neither
complete English family coverage nor independent qualification.
"""
import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import re
import tarfile

import english_family_keys as family
import ewt_lemma_exclusions as prior
import ewt_packaged_lemma_exclusions as packaged
import holdout_ledger as lexical

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).with_name('ewt-scowl-lemma-exclusions-v1.json')
ARCHIVE_SHA = '933cd8edab9297fc8cb6358d7cb3d05a50371107d1431af61de09eaa875043ac'
MEMBER_SHA = 'bf400f974c3716bb9f427b583d6e1cade92c283c9a7bfd1b2e10c3ca2bd95464'
MEMBER = 'wordlist-5ef55f9c42730ebe4394a78b77855468a6f15dd2/alt12dicts/5desk.txt'
ENTRY = 'public-ud-english-ewt-2.18-scowl-5desk-lemma-exclusion-v1'
FIXTURE_SHA = 'a5b984e703bd6ab49c72906da4bbea2c5269d3e80454292c82c0ac2d64c1bfd1'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def dictionary(archive):
    if sha(archive) != ARCHIVE_SHA:
        raise ValueError('EWT_SCOWL_ARCHIVE_IDENTITY')
    import io
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as package:
        matches = [item for item in package.getmembers() if item.name == MEMBER]
        if len(matches) != 1 or not matches[0].isfile() or matches[0].size != 580271:
            raise ValueError('EWT_SCOWL_MEMBER')
        raw = package.extractfile(matches[0]).read()
    if sha(raw) != MEMBER_SHA:
        raise ValueError('EWT_SCOWL_MEMBER_IDENTITY')
    keys = set()
    for line in raw.decode('latin-1').splitlines():
        try:
            keys.add(family.key_for(line))
        except ValueError:
            continue
    return keys


def scan(data, words, old):
    counts = Counter(); keys = set()
    for name in sorted(data):
        for line in data[name].decode('utf-8').splitlines():
            if not line or line.startswith('#'):
                continue
            fields = line.split('\t')
            if len(fields) != 10:
                raise ValueError('EWT_SCOWL_TOKEN_SCHEMA')
            if re.fullmatch(r'[1-9][0-9]*', fields[0]) is None:
                if re.fullmatch(r'[1-9][0-9]*(?:-[1-9][0-9]*|\.[1-9][0-9]*)', fields[0]) is None:
                    raise ValueError('EWT_SCOWL_TOKEN_ID')
                continue
            if fields[3] not in prior.POS:
                raise ValueError('EWT_SCOWL_TOKEN_SCHEMA')
            try:
                key = family.key_for(fields[2])
            except ValueError:
                continue
            if key in words and key not in old:
                counts[fields[3]] += 1
                keys.add(key)
    return sorted(keys), dict(sorted(counts.items()))


def generate(data, archive, ledger):
    old_raw = prior.FIXTURE.read_bytes(); extra_raw = packaged.FIXTURE.read_bytes()
    if prior.sha(old_raw) != packaged.PRIOR_SHA or sha(extra_raw) != packaged.FIXTURE_SHA:
        raise ValueError('EWT_SCOWL_PRIOR_IDENTITY')
    lock = prior.ewt.LOCK.read_bytes()
    old = prior.extract(data, lock, prior.VOCAB.read_bytes(), ledger)
    if old != prior.fixture(old_raw):
        raise ValueError('EWT_SCOWL_PRIOR_REPRODUCTION')
    extra = packaged.generate(data, lock, prior.VOCAB.read_bytes(), ledger, old_raw,
                              packaged.TRIE.read_bytes(), packaged.MANIFEST.read_bytes())
    if extra != json.loads(extra_raw):
        raise ValueError('EWT_SCOWL_PACKAGED_REPRODUCTION')
    old_keys = set(old['keys']) | set(extra['keys'])
    keys, counts = scan(data, dictionary(archive), old_keys)
    return dict(schema='ewt-public-scowl-5desk-lemmas-v1', sourceLockSha256=prior.LOCK_SHA,
                archiveSha256=ARCHIVE_SHA, memberSha256=MEMBER_SHA,
                priorFixtureSha256=packaged.PRIOR_SHA, packagedFixtureSha256=packaged.FIXTURE_SHA,
                counts=counts, keys=keys, independentQualification=False, familyCoverageComplete=False)


def entry(ledger, raw):
    if sha(raw) != FIXTURE_SHA:
        raise ValueError('EWT_SCOWL_FIXTURE_IDENTITY')
    expected = packaged.entry(ledger, packaged.FIXTURE.read_bytes())
    checked = lexical.validate_ledger(copy.deepcopy(ledger))
    if [e for e in checked['entries'] if e['id'] == packaged.ENTRY] != [expected]:
        raise ValueError('EWT_SCOWL_PARENT')
    value = json.loads(raw)
    old = set(prior.fixture(prior.FIXTURE.read_bytes())['keys']) | set(json.loads(packaged.FIXTURE.read_bytes())['keys'])
    if (value.get('schema') != 'ewt-public-scowl-5desk-lemmas-v1' or
            value.get('sourceLockSha256') != prior.LOCK_SHA or value.get('archiveSha256') != ARCHIVE_SHA or
            value.get('memberSha256') != MEMBER_SHA or value.get('priorFixtureSha256') != packaged.PRIOR_SHA or
            value.get('packagedFixtureSha256') != packaged.FIXTURE_SHA or
            value.get('independentQualification') is not False or value.get('familyCoverageComplete') is not False or
            value.get('counts') != {'ADJ':21, 'NOUN':56, 'PROPN':76, 'VERB':9} or
            not isinstance(value.get('keys'), list) or len(value['keys']) != 84 or
            value['keys'] != sorted(set(value['keys'])) or
            any(not isinstance(k, str) or re.fullmatch(r'[0-9a-f]{64}', k) is None for k in value['keys']) or
            old.intersection(value['keys'])):
        raise ValueError('EWT_SCOWL_FIXTURE')
    paths = (Path(__file__).resolve(), Path(prior.__file__).resolve(), Path(packaged.__file__).resolve(),
             Path(family.__file__).resolve(), Path(lexical.__file__).resolve(), prior.ewt.LOCK,
             prior.FIXTURE, packaged.FIXTURE, FIXTURE,
             ROOT/'tools/typing_experiments/source_identities.py',
             ROOT/'tools/lexicon/smart-typing-0.3/source-lock.json')
    bindings = {str(path.relative_to(ROOT)):sha(path.read_bytes()) for path in paths}
    return dict(id=ENTRY, usage='historical-family-exclusion', keys={'family':value['keys']},
                missingAxes=[], bindings=bindings, rowCount=sum(value['counts'].values()),
                parentEntries=[prior.ENTRY, packaged.ENTRY],
                notes='Exact public EWT lemmas also in pinned SCOWL 5desk; not full families or independent qualification.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-directory', type=Path); parser.add_argument('--archive', type=Path)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--generate', type=Path); modes.add_argument('--register', type=Path); modes.add_argument('--check', action='store_true')
    args = parser.parse_args(); ledger_raw = prior.LEDGER.read_bytes(); ledger = json.loads(ledger_raw)
    if args.generate:
        if args.source_directory is None or args.archive is None:
            raise ValueError('EWT_SCOWL_SCOPE')
        hashes = json.loads(prior.ewt.LOCK.read_bytes())['files']
        paths = {name:args.source_directory/name for name in hashes}
        data = {name:path.read_bytes() for name,path in paths.items()}
        archive = args.archive.read_bytes()
        bound = (Path(__file__).resolve(), Path(prior.__file__).resolve(), Path(packaged.__file__).resolve(),
                 Path(family.__file__).resolve(), Path(lexical.__file__).resolve(), Path(prior.ewt.__file__).resolve(),
                 ROOT/'tools/typing_experiments/source_identities.py', prior.ewt.LOCK, prior.VOCAB,
                 prior.FIXTURE, packaged.FIXTURE, packaged.TRIE, packaged.MANIFEST)
        before = {path:sha(path.read_bytes()) for path in bound}
        value = generate(data, archive, ledger)
        if (prior.LEDGER.read_bytes() != ledger_raw or args.archive.read_bytes() != archive or
                any(paths[name].read_bytes() != raw for name,raw in data.items()) or
                any(sha(path.read_bytes()) != digest for path,digest in before.items())):
            raise ValueError('EWT_SCOWL_INPUT_DRIFT')
        with args.generate.open('xb') as stream:
            stream.write((json.dumps(value, sort_keys=True, indent=2)+'\n').encode())
        print(json.dumps({'keys':len(value['keys']), 'counts':value['counts']}, sort_keys=True)); return
    if args.source_directory is not None or args.archive is not None:
        raise ValueError('EWT_SCOWL_SCOPE')
    expected = entry(ledger, FIXTURE.read_bytes())
    if args.check:
        if [e for e in lexical.validate_ledger(ledger)['entries'] if e['id'] == ENTRY] != [expected]:
            raise ValueError('EWT_SCOWL_LEDGER_DRIFT')
        print(json.dumps({'keys':len(expected['keys']['family']), 'independentQualification':False})); return
    output = args.register.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):
        raise ValueError('EWT_SCOWL_OUTPUT')
    if any(e['id'] == ENTRY for e in ledger['entries']):
        raise ValueError('EWT_SCOWL_EXISTS')
    ledger['entries'].append(expected); lexical.validate_ledger(copy.deepcopy(ledger))
    if prior.LEDGER.read_bytes() != ledger_raw or entry(json.loads(ledger_raw), FIXTURE.read_bytes()) != expected:
        raise ValueError('EWT_SCOWL_INPUT_DRIFT')
    with output.open('x', encoding='utf-8') as stream:
        json.dump(ledger, stream, ensure_ascii=False, sort_keys=True, indent=2); stream.write('\n')
    print(json.dumps({'keys':len(expected['keys']['family']), 'independentQualification':False}))


if __name__ == '__main__':
    main()
