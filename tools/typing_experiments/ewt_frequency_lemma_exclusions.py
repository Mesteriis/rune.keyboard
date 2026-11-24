"""Quarantine exact public EWT lemmas in the pinned full frequency list.

These unsalted public-word hashes are reversible, not anonymization. Exact
annotated lemmas are not complete English families or qualification evidence.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re

import english_family_keys as family
import ewt_lemma_exclusions as prior
import ewt_packaged_lemma_exclusions as packaged
import ewt_scowl_lemma_exclusions as scowl
import holdout_ledger as lexical

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).with_name('ewt-frequency-lemma-exclusions-v1.json')
URL = ('https://raw.githubusercontent.com/hermitdave/FrequencyWords/'
       '525f9b560de45753a5ea01069454e72e9aa541c6/content/2018/en/en_full.txt')
FREQUENCY_SHA = '7fea67ab954e2c01df6c608c9826e594cf36f8823b3243554f88245fb75dc506'
FREQUENCY_BYTES = 19977552
MIN_FREQUENCY = 5
ENTRY = 'public-ud-english-ewt-2.18-full-frequency-lemma-exclusion-v1'
FIXTURE_SHA = 'b7d11b0d6f56f3c04f4f5583131577ae1f02507f011c19a05fdef86f6e2f6263'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def frequency_keys(raw):
    if len(raw) != FREQUENCY_BYTES or sha(raw) != FREQUENCY_SHA:
        raise ValueError('EWT_FREQUENCY_SOURCE_IDENTITY')
    keys = set()
    for line in raw.decode('utf-8').splitlines():
        try:
            word, count = line.rsplit(' ', 1)
            if not count.isascii() or not count.isdecimal() or int(count) < 1:
                raise ValueError
        except ValueError as error:
            raise ValueError('EWT_FREQUENCY_SOURCE_FORMAT') from error
        if int(count) >= MIN_FREQUENCY:
            try:
                keys.add(family.key_for(word))
            except ValueError:
                continue
    return keys


def generate(data, frequency, ledger):
    old_raw = prior.FIXTURE.read_bytes(); packaged_raw = packaged.FIXTURE.read_bytes(); scowl_raw = scowl.FIXTURE.read_bytes()
    if (sha(old_raw) != packaged.PRIOR_SHA or sha(packaged_raw) != packaged.FIXTURE_SHA or
            sha(scowl_raw) != scowl.FIXTURE_SHA):
        raise ValueError('EWT_FREQUENCY_PRIOR_IDENTITY')
    lock = prior.ewt.LOCK.read_bytes(); vocab = prior.VOCAB.read_bytes()
    old = prior.extract(data, lock, vocab, ledger)
    if old != prior.fixture(old_raw):
        raise ValueError('EWT_FREQUENCY_PRIOR_REPRODUCTION')
    extra = packaged.generate(data, lock, vocab, ledger, old_raw,
                              packaged.TRIE.read_bytes(), packaged.MANIFEST.read_bytes())
    if extra != json.loads(packaged_raw):
        raise ValueError('EWT_FREQUENCY_PACKAGED_REPRODUCTION')
    expected = scowl.entry(ledger, scowl_raw)
    if [e for e in lexical.validate_ledger(copy.deepcopy(ledger))['entries'] if e['id'] == scowl.ENTRY] != [expected]:
        raise ValueError('EWT_FREQUENCY_SCOWL_PARENT')
    previous = set(old['keys']) | set(extra['keys']) | set(json.loads(scowl_raw)['keys'])
    keys, counts = scowl.scan(data, frequency_keys(frequency), previous)
    return dict(schema='ewt-public-full-frequency-lemmas-v1', sourceLockSha256=prior.LOCK_SHA,
                frequencyUrl=URL, frequencySha256=FREQUENCY_SHA, minimumFrequency=MIN_FREQUENCY,
                priorFixtureSha256=packaged.PRIOR_SHA, packagedFixtureSha256=packaged.FIXTURE_SHA,
                scowlFixtureSha256=scowl.FIXTURE_SHA, counts=counts, keys=keys,
                independentQualification=False, familyCoverageComplete=False)


def entry(ledger, raw):
    if sha(raw) != FIXTURE_SHA:
        raise ValueError('EWT_FREQUENCY_FIXTURE_IDENTITY')
    scowl_raw = scowl.FIXTURE.read_bytes(); expected = scowl.entry(ledger, scowl_raw)
    checked = lexical.validate_ledger(copy.deepcopy(ledger))
    if [e for e in checked['entries'] if e['id'] == scowl.ENTRY] != [expected]:
        raise ValueError('EWT_FREQUENCY_PARENT')
    value = json.loads(raw)
    old = (set(prior.fixture(prior.FIXTURE.read_bytes())['keys']) |
           set(json.loads(packaged.FIXTURE.read_bytes())['keys']) | set(json.loads(scowl_raw)['keys']))
    if (value.get('schema') != 'ewt-public-full-frequency-lemmas-v1' or
            value.get('sourceLockSha256') != prior.LOCK_SHA or value.get('frequencyUrl') != URL or
            value.get('frequencySha256') != FREQUENCY_SHA or value.get('minimumFrequency') != MIN_FREQUENCY or
            value.get('priorFixtureSha256') != packaged.PRIOR_SHA or value.get('packagedFixtureSha256') != packaged.FIXTURE_SHA or
            value.get('scowlFixtureSha256') != scowl.FIXTURE_SHA or
            value.get('independentQualification') is not False or value.get('familyCoverageComplete') is not False or
            value.get('counts') != {'ADJ':20, 'ADV':8, 'INTJ':14, 'NOUN':333, 'PRON':1, 'PROPN':1214, 'VERB':15, 'X':18} or
            not isinstance(value.get('keys'), list) or len(value['keys']) != 845 or
            value['keys'] != sorted(set(value['keys'])) or
            any(not isinstance(k, str) or re.fullmatch(r'[0-9a-f]{64}', k) is None for k in value['keys']) or
            old.intersection(value['keys'])):
        raise ValueError('EWT_FREQUENCY_FIXTURE')
    paths = (Path(__file__).resolve(), Path(prior.__file__).resolve(), Path(packaged.__file__).resolve(),
             Path(scowl.__file__).resolve(), Path(family.__file__).resolve(), Path(lexical.__file__).resolve(),
             Path(prior.ewt.__file__).resolve(), prior.ewt.LOCK, prior.FIXTURE, packaged.FIXTURE, scowl.FIXTURE,
             ROOT/'tools/typing_experiments/source_identities.py', FIXTURE,
             ROOT/'tools/lexicon/smart-typing-0.3/notices/FrequencyWords-README.md')
    bindings = {str(path.relative_to(ROOT)):sha(path.read_bytes()) for path in paths}
    return dict(id=ENTRY, usage='historical-family-exclusion', keys={'family':value['keys']}, missingAxes=[],
                bindings=bindings, rowCount=sum(value['counts'].values()), parentEntries=[scowl.ENTRY],
                notes='Exact public EWT lemmas in pinned FrequencyWords en_full with frequency at least five; not full families or independent qualification.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-directory', type=Path); parser.add_argument('--frequency', type=Path)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--generate', type=Path); modes.add_argument('--register', type=Path); modes.add_argument('--check', action='store_true')
    args = parser.parse_args(); ledger_raw = prior.LEDGER.read_bytes(); ledger = json.loads(ledger_raw)
    if args.generate:
        if args.source_directory is None or args.frequency is None:
            raise ValueError('EWT_FREQUENCY_SCOPE')
        hashes = json.loads(prior.ewt.LOCK.read_bytes())['files']
        paths = {name:args.source_directory/name for name in hashes}
        data = {name:path.read_bytes() for name,path in paths.items()}; frequency = args.frequency.read_bytes()
        bound = (Path(__file__).resolve(), Path(prior.__file__).resolve(), Path(packaged.__file__).resolve(),
                 Path(scowl.__file__).resolve(), Path(family.__file__).resolve(), Path(lexical.__file__).resolve(),
                 Path(prior.ewt.__file__).resolve(), ROOT/'tools/typing_experiments/source_identities.py',
                 prior.ewt.LOCK, prior.VOCAB, prior.FIXTURE, packaged.FIXTURE, scowl.FIXTURE, packaged.TRIE, packaged.MANIFEST)
        before = {path:sha(path.read_bytes()) for path in bound}
        value = generate(data, frequency, ledger)
        if (prior.LEDGER.read_bytes() != ledger_raw or args.frequency.read_bytes() != frequency or
                any(paths[name].read_bytes() != raw for name,raw in data.items()) or
                any(sha(path.read_bytes()) != digest for path,digest in before.items())):
            raise ValueError('EWT_FREQUENCY_INPUT_DRIFT')
        with args.generate.open('xb') as stream:
            stream.write((json.dumps(value, sort_keys=True, indent=2)+'\n').encode())
        print(json.dumps({'keys':len(value['keys']), 'counts':value['counts']}, sort_keys=True)); return
    if args.source_directory is not None or args.frequency is not None:
        raise ValueError('EWT_FREQUENCY_SCOPE')
    expected = entry(ledger, FIXTURE.read_bytes())
    if args.check:
        if [e for e in lexical.validate_ledger(ledger)['entries'] if e['id'] == ENTRY] != [expected]:
            raise ValueError('EWT_FREQUENCY_LEDGER_DRIFT')
        print(json.dumps({'keys':len(expected['keys']['family']), 'independentQualification':False})); return
    output = args.register.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):
        raise ValueError('EWT_FREQUENCY_OUTPUT')
    if any(e['id'] == ENTRY for e in ledger['entries']):
        raise ValueError('EWT_FREQUENCY_EXISTS')
    ledger['entries'].append(expected); lexical.validate_ledger(copy.deepcopy(ledger))
    if prior.LEDGER.read_bytes() != ledger_raw or entry(json.loads(ledger_raw), FIXTURE.read_bytes()) != expected:
        raise ValueError('EWT_FREQUENCY_INPUT_DRIFT')
    with output.open('x', encoding='utf-8') as stream:
        json.dump(ledger, stream, ensure_ascii=False, sort_keys=True, indent=2); stream.write('\n')
    print(json.dumps({'keys':len(expected['keys']['family']), 'independentQualification':False}))


if __name__ == '__main__':
    main()
