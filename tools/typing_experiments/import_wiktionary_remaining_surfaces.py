"""Conservatively exclude attested forms of additional public historical surfaces.

The retained source is Russian Wiktionary via SergeyShk/rumorph-wiktionary,
revision 768e78b0f415f51c60d73c15362218452e30dbcc, CC BY-SA 4.0.
Exact forms are not claims about intended senses or canonical Pymorph families.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

import holdout_ledger as ledger
import import_wiktionary_historical_exclusions as source
from source_identities import unsupported_surface_key

ROOT = Path(__file__).resolve().parents[2]
LEDGER = source.LEDGER
FIXTURE = Path(__file__).with_name('wiktionary-remaining-surfaces-v1.json')
ENTRY = 'public-historical-wiktionary-remaining-surfaces-v1'
FIXTURE_SHA = '21b99606e41c564f325cf534753ff5e35b9e6c8613749219b7f26ef9cdd78a6a'


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def baseline(base, fixture):
    checked = ledger.validate_ledger(copy.deepcopy(base))
    entries = {item['id']: item for item in checked['entries']}
    bound = fixture['baselineEntries']
    if not isinstance(bound, dict) or len(bound) != 221:
        raise ValueError('WIKTIONARY_REMAINING_BASELINE')
    if any(name not in entries or digest(entries[name]) != expected for name, expected in bound.items()):
        raise ValueError('WIKTIONARY_REMAINING_BASELINE')
    names = fixture['parentIds']
    if not isinstance(names, list) or len(names) != 28 or names != sorted(set(names)):
        raise ValueError('WIKTIONARY_REMAINING_PARENTS')
    if any(name not in bound or not entries[name].get('unsupportedSurfaceKeys') for name in names):
        raise ValueError('WIKTIONARY_REMAINING_PARENTS')
    return entries, {name: set(entries[name]['unsupportedSurfaceKeys']) for name in names}


def capture(raw, base, fixture):
    entries, parents = baseline(base, fixture)
    result = source.capture(raw, parents)
    result['baselineEntries'] = fixture['baselineEntries']
    result['parentIds'] = fixture['parentIds']
    return result


def entry(base, fixture):
    entries, parents = baseline(base, fixture)
    pairs = fixture.get('pairs')
    titles = fixture.get('sourceTitles')
    if (fixture.get('schema') != 1 or fixture.get('sourceSha256') != source.SOURCE_SHA or
            fixture.get('entries') != source.SOURCE_ENTRIES or not isinstance(pairs, list) or
            len(pairs) != 83763 or pairs != sorted(pairs) or
            any(not isinstance(p, list) or len(p) != 2 or
                any(not isinstance(s, str) or not source.WORD.fullmatch(s) for s in p) for p in pairs) or
            len({tuple(p) for p in pairs}) != len(pairs)):
        raise ValueError('WIKTIONARY_REMAINING_FIXTURE')
    forms = {unsupported_surface_key(form) for _, form in pairs}
    targets = set().union(*parents.values())
    matches = {name: sorted(values & forms) for name, values in parents.items()}
    if (fixture.get('matchesByParent') != matches or len(forms) != 79503 or
            len(set().union(*(set(v) for v in matches.values()))) != 11091 or
            {head for head, form in pairs if unsupported_surface_key(form) in targets} != {p[0] for p in pairs}):
        raise ValueError('WIKTIONARY_REMAINING_SCOPE')
    if (not isinstance(titles, list) or titles != sorted(titles) or
            any(not isinstance(t, list) or len(t) != 2 or not all(isinstance(v, str) for v in t)
                or source.norm(t[1]) != t[0] for t in titles) or
            {t[0] for t in titles} != {p[0] for p in pairs}):
        raise ValueError('WIKTIONARY_REMAINING_TITLES')
    old = {key for name in fixture['baselineEntries'] for key in entries[name].get('unsupportedSurfaceKeys', [])}
    novel = sorted(forms - old)
    if len(novel) != 54808:
        raise ValueError('WIKTIONARY_REMAINING_NOVEL')
    anchor = entries[source.ENTRY]
    files = (Path(__file__).resolve(), FIXTURE, Path(source.__file__).resolve())
    return dict(id=ENTRY, usage='historical-context-exclusion', rowCount=anchor['rowCount'],
                keys=copy.deepcopy(anchor['keys']), unsupportedSurfaceKeys=novel, missingAxes=[],
                parentEntries=fixture['parentIds'],
                bindings={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
                notes='Exact Wiktionary forms of additional disclosed public surfaces; no canonical family or intended sense inferred.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path)
    parser.add_argument('--check', action='store_true', required=True)
    args = parser.parse_args()
    raw = FIXTURE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != FIXTURE_SHA:
        raise ValueError('WIKTIONARY_REMAINING_FIXTURE_IDENTITY')
    fixture = json.loads(raw)
    base_raw = LEDGER.read_bytes()
    base = json.loads(base_raw)
    expected = entry(base, fixture)
    if [e for e in base['entries'] if e['id'] == ENTRY] != [expected]:
        raise ValueError('WIKTIONARY_REMAINING_ENTRY')
    if args.capture:
        data = args.capture.read_bytes()
        if capture(data, base, fixture) != fixture:
            raise ValueError('WIKTIONARY_REMAINING_CAPTURE')
        if args.capture.read_bytes() != data or LEDGER.read_bytes() != base_raw or FIXTURE.read_bytes() != raw:
            raise ValueError('WIKTIONARY_REMAINING_DRIFT')
    print(json.dumps({'surfaces': len(expected['unsupportedSurfaceKeys']), 'independentQualification': False}))


if __name__ == '__main__':
    main()
