"""Exclude observed public neighbor replay outputs; never qualify the corpus."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/typing_experiments'))
import control_ledger as control
import holdout_ledger as lexical

DATA = ROOT / 'tools/typing_experiments/neighbor-history-v1'
FIXTURE = DATA / 'current-observed-v1.jsonl'
CONTROL = ROOT / 'tools/typing_experiments/control-ledger.json'
LEXICAL = ROOT / 'tools/typing_experiments/holdout-ledger.json'
ENTRY = 'neighbor-current-observed-v1'
PINS = {'current-observed-v1.jsonl': 'e86ca9e774008dd43f8238278db14b46f081d90f9ff558ba5d54aa3fb70a68e8',
        'holdout.jsonl': 'e0a97cd39220a3887dfe2129f45c07db512e83e72a8c6f4b74ca3657d5928437',
        'manifest.json': '2aeaf745c132c869d2560c89f3831f9710d82d34f559083a352eeb99b604060e'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def inputs():
    paths = [FIXTURE, DATA / 'holdout.jsonl', DATA / 'manifest.json', Path(__file__).resolve(),
             ROOT / 'tools/typing_experiments/control_ledger.py', ROOT / 'tools/typing_experiments/holdout_ledger.py']
    raw = {str(path.relative_to(ROOT)): path.read_bytes() for path in paths}
    for name, digest in PINS.items():
        if sha(raw[str((DATA / name).relative_to(ROOT))]) != digest:
            raise ValueError('NEIGHBOR_OBSERVED_IDENTITY')
    rows = [json.loads(line) for line in raw[str(FIXTURE.relative_to(ROOT))].splitlines()]
    original = [json.loads(line) for line in raw[str((DATA / 'holdout.jsonl').relative_to(ROOT))].splitlines()]
    canonical = ''.join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n' for row in rows).encode()
    by_id = {row['id']: row for row in original}
    if (len(original) != 6000 or len(by_id) != 6000 or len(rows) != 3472 or raw[str(FIXTURE.relative_to(ROOT))] != canonical or
            len({row.get('sourceId') for row in rows}) != len(rows)):
        raise ValueError('NEIGHBOR_OBSERVED_ROWS')
    for row in rows:
        if (set(row) != {'sourceId', 'article', 'language', 'prefix', 'typed', 'expectedSpelling'} or
                row['sourceId'] not in by_id or row['article'] != by_id[row['sourceId']]['article'] or
                row['language'] != 'ru' or not isinstance(row['prefix'], str) or not row['prefix'] or
                not isinstance(row['typed'], str) or not row['typed'] or row['typed'] != row['expectedSpelling']):
            raise ValueError('NEIGHBOR_OBSERVED_ROW')
    return rows, {name: sha(value) for name, value in raw.items()}


def entries():
    rows, bindings = inputs()
    first = dict(id=ENTRY, kind='regression', language='ru', rowCount=len(rows), bindings=bindings,
                 keys=sorted({control.key_for(row, 'regression') for row in rows}),
                 surfaceKeys=sorted({control.surface_key('ru', row['typed']) for row in rows}),
                 articleKeys=sorted({control.article_key(row) for row in rows}),
                 semantics='Observed outputs of disclosed historical neighbor replay; not independent quality data.')
    second = dict(id=ENTRY + '-contexts', usage='historical-context-exclusion', rowCount=len(rows),
                  bindings=bindings, keys={'context': sorted(lexical.keys_for(rows, 'context'))}, missingAxes=[],
                  notes='Observed public neighbor replay contexts; no canonical family claim.')
    return first, second


def check():
    controls = control.load(CONTROL)
    ledger = lexical.load_ledger(LEXICAL)
    first, second = entries()
    if ([e for e in controls['entries'] if e['id'] == ENTRY] != [first] or
            [e for e in ledger['entries'] if e['id'] == ENTRY + '-contexts'] != [second]):
        raise ValueError('NEIGHBOR_OBSERVED_DRIFT')
    return first['rowCount']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.check:
        if args.output:
            raise ValueError('NEIGHBOR_OBSERVED_SCOPE')
        print(json.dumps({'contexts': check(), 'independentQualification': False}))
        return
    if args.output is None:
        raise ValueError('NEIGHBOR_OBSERVED_SCOPE')
    output = args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'):
        raise ValueError('NEIGHBOR_OBSERVED_OUTPUT')
    before_c, before_l = CONTROL.read_bytes(), LEXICAL.read_bytes()
    first, second = entries()
    controls, stored = json.loads(before_c), json.loads(before_l)
    control.validate(controls)
    logical = lexical.validate_ledger(copy.deepcopy(stored))
    if any(e['id'] == ENTRY for e in controls['entries']) or any(e['id'] == ENTRY + '-contexts' for e in logical['entries']):
        raise ValueError('NEIGHBOR_OBSERVED_EXISTS')
    controls['entries'].append(first)
    stored['entries'].append(second)
    control.validate(controls)
    lexical.validate_ledger(copy.deepcopy(stored))
    if CONTROL.read_bytes() != before_c or LEXICAL.read_bytes() != before_l or inputs()[1] != first['bindings']:
        raise ValueError('NEIGHBOR_OBSERVED_INPUT_DRIFT')
    output.mkdir(parents=True, mode=0o700)
    for name, value in (('control-ledger.json', controls), ('holdout-ledger.json', stored)):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'contexts': len(inputs()[0]), 'independentQualification': False}))


if __name__ == '__main__':
    main()
