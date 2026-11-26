"""Quarantine dictionary analyses and exact annotated lemmas from exposed Taiga dev."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

import holdout_ledger as ledger
import import_taiga_dev_exposure as taiga
from source_identities import unsupported_surface_key

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).with_name('public_sources') / 'ud-taiga-2.18-dev' / 'lemma-exclusions-v1.json'
LEDGER = Path(__file__).with_name('holdout-ledger.json')
ENTRY = 'public-taiga-dev-annotated-lemmas-v1'
FIXTURE_SHA = '913296ef5c1834acdda886437d836a2ab62aa9fd54d5457b6e62f7115f48c14c'
WORD = re.compile(r'[а-яё]{1,32}\Z')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def dictionary_identity(receipt):
    """Exclude generated RECORD metadata while binding the other receipt files."""
    stable = copy.deepcopy(receipt)
    for package in stable['packages'].values():
        package['files'] = {name: digest for name, digest in package['files'].items()
                            if not name.endswith('.dist-info/RECORD')}
    return sha(json.dumps(stable, sort_keys=True, separators=(',', ':')).encode())


def capture(data, lexicon):
    lock = json.loads(taiga.LOCK.read_text())
    sentences, count = taiga.sentence_keys(data, lock['sha256'])
    base = ledger.load_ledger(LEDGER)
    parents = [item for item in base['entries'] if item['id'] == taiga.ENTRY]
    if len(parents) != 1 or parents[0]['rowCount'] != count or parents[0]['keys']['sentence'] != sentences:
        raise ValueError('TAIGA_LEMMA_PARENT')
    receipt = lexicon.receipt()
    surfaces = set()
    token_rows = eligible_rows = 0
    for line in data.decode('utf-8').splitlines():
        if not line or line.startswith('#'):
            continue
        fields = line.split('\t')
        if len(fields) != 10:
            raise ValueError('TAIGA_LEMMA_ROW')
        token_id = fields[0]
        if not token_id.isascii() or not token_id.isdecimal():
            continue
        token_rows += 1
        lemma = unicodedata.normalize('NFC', fields[2]).casefold()
        if WORD.fullmatch(lemma):
            eligible_rows += 1
            surfaces.add(lemma)
    eligible = surfaces
    families, unknown = set(), set()
    for word in eligible:
        analyses = lexicon.analyses(word)
        if not analyses:
            unknown.add(word)
        for analysis in analyses:
            families.update(ledger.keys_for([{'families': [analysis.lemma]}], 'family'))
    exact = {unsupported_surface_key(word) for word in eligible}
    if None in exact or not families or not exact:
        raise ValueError('TAIGA_LEMMA_EMPTY')
    if lexicon.receipt() != receipt:
        raise ValueError('TAIGA_LEMMA_DICTIONARY_DRIFT')
    return dict(schema=1, sourceSha256=lock['sha256'], sentenceCount=count,
                tokenRows=token_rows, eligibleRows=eligible_rows, eligibleSurfaces=len(eligible),
                unsupportedRows=token_rows - eligible_rows, unknownSurfaces=len(unknown),
                familyKeys=sorted(families), exactSurfaceKeys=sorted(exact),
                dictionaryIdentitySha256=dictionary_identity(receipt))


def fixture():
    raw = FIXTURE.read_bytes()
    if sha(raw) != FIXTURE_SHA:
        raise ValueError('TAIGA_LEMMA_FIXTURE')
    value = json.loads(raw)
    if (value.get('schema') != 1 or value.get('sourceSha256') != json.loads(taiga.LOCK.read_text())['sha256'] or
            value.get('sentenceCount') != 1260 or type(value.get('eligibleSurfaces')) is not int or value['eligibleSurfaces'] < 1 or
            not isinstance(value.get('dictionaryIdentitySha256'), str) or
            not re.fullmatch('[0-9a-f]{64}', value['dictionaryIdentitySha256'])):
        raise ValueError('TAIGA_LEMMA_FIXTURE')
    for field in ('familyKeys', 'exactSurfaceKeys'):
        keys = value.get(field)
        if (not isinstance(keys, list) or not keys or keys != sorted(set(keys)) or
                any(not isinstance(key, str) or not re.fullmatch('[0-9a-f]{64}', key) for key in keys)):
            raise ValueError('TAIGA_LEMMA_KEYS')
    if len(value['exactSurfaceKeys']) != value['eligibleSurfaces']:
        raise ValueError('TAIGA_LEMMA_SURFACE_COUNT')
    return value


def entry(base):
    value = fixture()
    parents = [item for item in ledger.validate_ledger(copy.deepcopy(base))['entries'] if item['id'] == taiga.ENTRY]
    if len(parents) != 1 or parents[0]['rowCount'] != value['sentenceCount']:
        raise ValueError('TAIGA_LEMMA_PARENT')
    paths = (Path(__file__).resolve(), FIXTURE, taiga.LOCK, Path(taiga.__file__).resolve(),
             Path(ledger.__file__).resolve(), ROOT / 'tools/typing_experiments/source_identities.py',
             ROOT / 'tools/morphology/ranker.py', ROOT / 'tools/morphology/requirements.lock')
    bindings = {str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in paths}
    return dict(id=ENTRY, usage='historical-family-exclusion', rowCount=value['eligibleSurfaces'],
                keys={'family': value['familyKeys']}, unsupportedSurfaceKeys=value['exactSurfaceKeys'],
                missingAxes=[], bindings=bindings, dictionaryIdentitySha256=value['dictionaryIdentitySha256'],
                parentEntries=[taiga.ENTRY],
                notes='Dictionary-only analyses and exact annotated Cyrillic lemmas from inspected public Taiga dev; not independent qualification.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture', type=Path); p.add_argument('--check', action='store_true'); p.add_argument('--output', type=Path)
    args = p.parse_args()
    if args.check:
        if args.capture or args.output: raise ValueError('TAIGA_LEMMA_SCOPE')
        raw = json.loads(LEDGER.read_bytes()); expected = entry(raw)
        if [item for item in raw['entries'] if item['id'] == ENTRY] != [expected]: raise ValueError('TAIGA_LEMMA_DRIFT')
        print(json.dumps({'surfaces': expected['rowCount'], 'independentQualification': False})); return
    if args.output is None: raise ValueError('TAIGA_LEMMA_SCOPE')
    output = args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'): raise ValueError('TAIGA_LEMMA_OUTPUT')
    if args.capture:
        sys.path.insert(0, str(ROOT / 'tools/morphology'))
        from ranker import PymorphyLexicon
        source = args.capture.read_bytes(); lock = taiga.LOCK.read_bytes(); base = LEDGER.read_bytes()
        helpers = (Path(__file__).resolve(), Path(taiga.__file__).resolve(), Path(ledger.__file__).resolve(),
                   ROOT / 'tools/typing_experiments/source_identities.py', ROOT / 'tools/morphology/ranker.py',
                   ROOT / 'tools/morphology/requirements.lock')
        helper_hashes = {path: sha(path.read_bytes()) for path in helpers}
        result = capture(source, PymorphyLexicon(cache_size=16384))
        if (args.capture.read_bytes() != source or taiga.LOCK.read_bytes() != lock or LEDGER.read_bytes() != base or
                any(sha(path.read_bytes()) != digest for path, digest in helper_hashes.items())):
            raise ValueError('TAIGA_LEMMA_INPUT_DRIFT')
        output.write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
        print(json.dumps({key: result[key] for key in ('sentenceCount', 'tokenRows', 'eligibleRows', 'eligibleSurfaces', 'unsupportedRows', 'unknownSurfaces')})); return
    raw = LEDGER.read_bytes(); stored = json.loads(raw); current = entry(stored)
    if any(item['id'] == ENTRY for item in stored['entries']): raise ValueError('TAIGA_LEMMA_EXISTS')
    stored['entries'].append(current); ledger.validate_ledger(copy.deepcopy(stored))
    if LEDGER.read_bytes() != raw or entry(json.loads(raw)) != current: raise ValueError('TAIGA_LEMMA_INPUT_DRIFT')
    output.write_text(json.dumps(stored, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'surfaces': current['rowCount'], 'independentQualification': False}))


if __name__ == '__main__': main()
