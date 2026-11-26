"""Exclude source-attested forms of disclosed Spanish control surfaces.

UniMorph Spanish revision b9655efb0e5ce0f99809badaa7f4e93017ab8430 is
Wiktionary-derived and declares CC BY-SA 3.0. This is conservative exact-form
quarantine, not intended-sense, complete-family or qualification evidence.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import unicodedata

import control_ledger as control

ROOT = Path(__file__).resolve().parents[2]
LEDGER = Path(__file__).with_name('control-ledger.json')
FIXTURE = Path(__file__).with_name('spanish-unimorph-control-surfaces-v1.json')
NOTICE = Path(__file__).with_name('spanish-unimorph-control-surfaces-v1.NOTICE.md')
ENTRY = 'public-spanish-unimorph-control-surfaces-v1'
PARENTS = ('ci-original-spelling-v2-es', 'ci-product-replay-v1-es',
           'public-named-common-confusion-regression-v1-es')
SOURCE_SHA = '7a165d4b44eb078d23964f3eee3813f5140c5df0ffab0143c806c562e67f8771'
SOURCE_BYTES = 50335761
SOURCE_LINES = 1196245
FIXTURE_SHA = 'a62e9ace940ec9beddc5c1b033c08e15064e2ce1ddf811bbab22d9b18e0c2df2'
WORD = re.compile('[a-záéíóúüñ]{1,32}\\Z')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(',', ':'), allow_nan=False).encode())


def norm(value):
    return unicodedata.normalize('NFC', value).casefold()


def baseline(base, fixture):
    entries = {e['id']: e for e in control.validate(base)['entries']}
    refs = fixture.get('baselineEntries')
    if (not isinstance(refs, dict) or len(refs) != 66 or
            any(name not in entries or digest(entries[name]) != value for name, value in refs.items())):
        raise ValueError('ES_UNIMORPH_BASELINE')
    parents = {}
    for name in PARENTS:
        item = entries.get(name)
        if (name not in refs or not item or item.get('language') != 'es' or
                item.get('kind') != 'regression' or not item.get('surfaceKeys')):
            raise ValueError('ES_UNIMORPH_PARENT')
        parents[name] = set(item['surfaceKeys'])
    return entries, parents


def project(raw, targets):
    heads = set(); rows = 0
    for line in io.BytesIO(raw):
        fields = line.decode('utf-8').rstrip('\r\n').split('\t'); rows += 1
        if len(fields) != 3:
            raise ValueError('ES_UNIMORPH_SOURCE_ROW')
        head, form = norm(fields[0]), norm(fields[1])
        if WORD.fullmatch(head) and WORD.fullmatch(form) and (
                control.surface_key('es', head) in targets or control.surface_key('es', form) in targets):
            heads.add(head)
    pairs, titles = set(), set()
    for line in io.BytesIO(raw):
        fields = line.decode('utf-8').rstrip('\r\n').split('\t')
        head, form = norm(fields[0]), norm(fields[1])
        if head in heads and WORD.fullmatch(form):
            if any(unicodedata.category(ch).startswith('C') for ch in fields[0]):
                raise ValueError('ES_UNIMORPH_TITLE')
            pairs.add((head, form)); titles.add((head, fields[0]))
    return rows, sorted(pairs), sorted(titles)


def capture(raw, base, fixture):
    if len(raw) != SOURCE_BYTES or sha(raw) != SOURCE_SHA:
        raise ValueError('ES_UNIMORPH_SOURCE_IDENTITY')
    _, parents = baseline(base, fixture)
    rows, pairs, titles = project(raw, set().union(*parents.values()))
    if rows != SOURCE_LINES:
        raise ValueError('ES_UNIMORPH_SOURCE_ROWS')
    return dict(schema=1, sourceSha256=SOURCE_SHA, sourceRows=rows,
                baselineEntries=fixture['baselineEntries'],
                pairs=[list(pair) for pair in pairs], sourceTitles=[list(title) for title in titles])


def entry(base, fixture):
    entries, parents = baseline(base, fixture)
    pairs, titles = fixture.get('pairs'), fixture.get('sourceTitles')
    if (fixture.get('schema') != 1 or fixture.get('sourceSha256') != SOURCE_SHA or
            fixture.get('sourceRows') != SOURCE_LINES or not isinstance(pairs, list) or
            len(pairs) != 46911 or pairs != sorted(pairs) or
            any(not isinstance(p, list) or len(p) != 2 or
                any(not isinstance(x, str) or not WORD.fullmatch(x) for x in p) for p in pairs) or
            len({tuple(p) for p in pairs}) != len(pairs)):
        raise ValueError('ES_UNIMORPH_FIXTURE')
    forms = {control.surface_key('es', form) for _, form in pairs}
    targets = set().union(*parents.values()); heads = {head for head, _ in pairs}
    qualifying = {head for head, form in pairs if control.surface_key('es', head) in targets or
                  control.surface_key('es', form) in targets}
    if len(heads) != 983 or len(forms) != 46294 or qualifying != heads:
        raise ValueError('ES_UNIMORPH_SCOPE')
    if (not isinstance(titles, list) or titles != sorted(titles) or
            any(not isinstance(t, list) or len(t) != 2 or not all(isinstance(x, str) for x in t) or
                norm(t[1]) != t[0] or any(unicodedata.category(ch).startswith('C') for ch in t[1]) for t in titles) or
            {t[0] for t in titles} != heads or len({tuple(t) for t in titles}) != len(titles)):
        raise ValueError('ES_UNIMORPH_TITLES')
    prior = {key for name in fixture['baselineEntries'] for key in entries[name].get('surfaceKeys', [])}
    novel = sorted(forms - prior)
    if len(novel) != 45289:
        raise ValueError('ES_UNIMORPH_NOVEL')
    anchor = entries['ci-product-replay-v1-es']
    paths = (Path(__file__).resolve(), FIXTURE, NOTICE, Path(control.__file__).resolve())
    return dict(id=ENTRY, kind='regression', language='es', rowCount=anchor['rowCount'],
                keys=list(anchor['keys']), surfaceKeys=novel, parentEntries=list(PARENTS),
                bindings={str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in paths},
                semantics='Exact UniMorph forms of disclosed Spanish control surfaces; no intended sense or complete family claim.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path)
    parser.add_argument('--check', action='store_true', required=True)
    args = parser.parse_args()
    raw = FIXTURE.read_bytes()
    if sha(raw) != FIXTURE_SHA:
        raise ValueError('ES_UNIMORPH_FIXTURE_IDENTITY')
    fixture = json.loads(raw); before = LEDGER.read_bytes(); base = json.loads(before)
    expected = entry(base, fixture)
    if [e for e in base['entries'] if e['id'] == ENTRY] != [expected]:
        raise ValueError('ES_UNIMORPH_ENTRY')
    if args.capture:
        data = args.capture.read_bytes()
        if capture(data, base, fixture) != fixture:
            raise ValueError('ES_UNIMORPH_CAPTURE')
        if args.capture.read_bytes() != data or LEDGER.read_bytes() != before or FIXTURE.read_bytes() != raw:
            raise ValueError('ES_UNIMORPH_DRIFT')
    print(json.dumps({'surfaces': len(expected['surfaceKeys']), 'independentQualification': False}))


if __name__ == '__main__':
    main()
