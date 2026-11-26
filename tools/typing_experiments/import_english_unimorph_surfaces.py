"""Quarantine attested UniMorph forms of previously disclosed English surfaces.

Source: unimorph/eng, revision 66e0e9e8e2dcd196da081a25a48e5c1fe3d8b49b,
Wikipedia-derived, CC BY-SA 3.0. Exact forms do not assert intended senses or
complete English morphology, and this importer never qualifies a corpus.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re

import control_ledger as control
import ewt_surface_exclusions_v1 as ewt
import holdout_ledger as ledger

ROOT = Path(__file__).resolve().parents[2]
LEDGER = Path(__file__).with_name('holdout-ledger.json')
FIXTURE = Path(__file__).with_name('english-unimorph-surfaces-v1.json')
NOTICE = Path(__file__).with_name('english-unimorph-surfaces-v1.NOTICE.md')
ENTRY = 'public-english-unimorph-historical-surfaces-v1'
PARENT = 'public-tatoeba-english-a1-exact-surface-exclusions-v1'
SOURCE_SHA = '20a191cefdc7cad6fa74b00f49d6f658684f17b14541aae372e5a3d5a8c15c67'
SOURCE_BYTES = 18022905
SOURCE_LINES = 652477
FIXTURE_SHA = 'f393af784e10dca0bac2e1cb0f751d2b9a31e0062c3d8dc308b6c875546bacf2'
WORD = re.compile(r"[a-z]+(?:['’][a-z]+)*\Z")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(',', ':'), allow_nan=False).encode())


def valid(word):
    return isinstance(word, str) and 1 <= len(word) <= 32 and WORD.fullmatch(word) is not None


def project(lines, targets):
    pairs = []
    for line in lines:
        fields = line.split('\t')
        if len(fields) != 3:
            raise ValueError('EN_UNIMORPH_SOURCE_ROW')
        lemma, form = fields[0].casefold(), fields[1].casefold()
        if valid(lemma) and valid(form):
            pairs.append((lemma, form))
    heads = {lemma for lemma, form in pairs if control.surface_key('en', lemma) in targets or
             control.surface_key('en', form) in targets}
    return sorted({(lemma, form) for lemma, form in pairs if lemma in heads})


def baseline(base, fixture):
    entries = {e['id']: e for e in ledger.validate_ledger(copy.deepcopy(base))['entries']}
    refs = fixture.get('baselineEntries')
    if (not isinstance(refs, dict) or len(refs) != 222 or PARENT not in refs or
            any(name not in entries or digest(entries[name]) != value for name, value in refs.items())):
        raise ValueError('EN_UNIMORPH_BASELINE')
    parent = entries[PARENT]
    if parent.get('sourceRepository') != 'tatoeba' or len(parent.get('unsupportedSurfaceKeys', [])) != 26735:
        raise ValueError('EN_UNIMORPH_PARENT')
    return entries, set(parent['unsupportedSurfaceKeys']) | ewt.load()


def capture(raw, base, fixture):
    if len(raw) != SOURCE_BYTES or sha(raw) != SOURCE_SHA:
        raise ValueError('EN_UNIMORPH_SOURCE_IDENTITY')
    _, targets = baseline(base, fixture)
    lines = raw.decode('utf-8').splitlines()
    if len(lines) != SOURCE_LINES:
        raise ValueError('EN_UNIMORPH_SOURCE_ROWS')
    return dict(schema=1, sourceSha256=SOURCE_SHA, sourceRows=SOURCE_LINES,
                baselineEntries=fixture['baselineEntries'],
                pairs=[list(pair) for pair in project(lines, targets)])


def entry(base, fixture):
    entries, targets = baseline(base, fixture)
    pairs = fixture.get('pairs')
    if (fixture.get('schema') != 1 or fixture.get('sourceSha256') != SOURCE_SHA or
            fixture.get('sourceRows') != SOURCE_LINES or not isinstance(pairs, list) or
            len(pairs) != 60216 or pairs != sorted(pairs) or
            any(not isinstance(pair, list) or len(pair) != 2 or not all(valid(s) for s in pair) for pair in pairs) or
            len({tuple(pair) for pair in pairs}) != len(pairs)):
        raise ValueError('EN_UNIMORPH_FIXTURE')
    forms = {control.surface_key('en', form) for _, form in pairs}
    heads = {head for head, _ in pairs}
    qualifying = {head for head, form in pairs if control.surface_key('en', head) in targets or
                  control.surface_key('en', form) in targets}
    if len(heads) != 27382 or len(forms) != 54631 or qualifying != heads:
        raise ValueError('EN_UNIMORPH_SCOPE')
    old = {key for name in fixture['baselineEntries'] for key in entries[name].get('unsupportedSurfaceKeys', [])}
    novel = sorted(forms - old - ewt.load())
    if len(novel) != 22647:
        raise ValueError('EN_UNIMORPH_NOVEL')
    anchor = entries[PARENT]
    paths = (Path(__file__).resolve(), FIXTURE, NOTICE, Path(ewt.__file__).resolve(), ewt.FIXTURE, ewt.ewt.LOCK)
    return dict(id=ENTRY, usage='historical-context-exclusion', rowCount=anchor['rowCount'],
                keys=copy.deepcopy(anchor['keys']), unsupportedSurfaceKeys=novel, missingAxes=[],
                parentEntries=[PARENT], bindings={str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in paths},
                notes='Exact UniMorph English forms of previously disclosed surfaces; no intended sense or complete family claim.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path)
    parser.add_argument('--check', action='store_true', required=True)
    args = parser.parse_args()
    raw = FIXTURE.read_bytes()
    if sha(raw) != FIXTURE_SHA:
        raise ValueError('EN_UNIMORPH_FIXTURE_IDENTITY')
    fixture = json.loads(raw); before = LEDGER.read_bytes(); base = json.loads(before)
    expected = entry(base, fixture)
    if [e for e in base['entries'] if e['id'] == ENTRY] != [expected]:
        raise ValueError('EN_UNIMORPH_ENTRY')
    if args.capture:
        data = args.capture.read_bytes()
        if capture(data, base, fixture) != fixture:
            raise ValueError('EN_UNIMORPH_CAPTURE')
        if args.capture.read_bytes() != data or LEDGER.read_bytes() != before or FIXTURE.read_bytes() != raw:
            raise ValueError('EN_UNIMORPH_DRIFT')
    print(json.dumps({'surfaces': len(expected['unsupportedSurfaceKeys']), 'independentQualification': False}))


if __name__ == '__main__':
    main()
