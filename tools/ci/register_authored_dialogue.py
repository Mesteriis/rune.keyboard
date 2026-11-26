"""Register public author-written dialogue contexts before any product replay."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/typing_experiments'))
import control_ledger as control
import holdout_ledger as lexical

FIXTURE = ROOT / 'tools/typing_experiments/authored-dialogue-v1'
CONTROL = ROOT / 'tools/typing_experiments/control-ledger.json'
LEXICAL = ROOT / 'tools/typing_experiments/holdout-ledger.json'
ENTRY = 'authored-everyday-dialogue-public-v1'
PINS = {'dialogues.jsonl': '2599fe92d9f976e262f89b50dc5ec02b97bd2c3f2edad965b83d74e38ecd4169',
        'README.md': '5b26ae1c2da28ff5c5d9ffd621b4ffbb75074fc4e6608efd646f7bb0a64c2d9b'}
WORD = re.compile('[а-яё]+', re.IGNORECASE)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def inputs():
    blobs = {name: (FIXTURE / name).read_bytes() for name in PINS}
    if any(sha(blobs[name]) != digest for name, digest in PINS.items()):
        raise ValueError('DIALOGUE_SOURCE_IDENTITY')
    dialogues = [json.loads(line) for line in blobs['dialogues.jsonl'].splitlines()]
    if len(dialogues) != 20 or len({row.get('id') for row in dialogues}) != 20:
        raise ValueError('DIALOGUE_SOURCE_ROWS')
    result = []
    for row in dialogues:
        for side in ('user', 'assistant'):
            value = row.get(side)
            if not isinstance(value, str) or not value.strip():
                raise ValueError('DIALOGUE_SOURCE_TEXT')
            for match in WORD.finditer(value):
                prefix = value[max(0, match.start() - 128):match.start()].lstrip()
                token = match.group()
                result.append(dict(language='ru', prefix=prefix, typed=token, expectedSpelling=token))
    if len(result) != 262:
        raise ValueError('DIALOGUE_SOURCE_SCOPE')
    paths = [Path(__file__).resolve(), *[FIXTURE / name for name in PINS], FIXTURE / 'NOTICE.md']
    return result, {str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in paths}


def entries():
    rows, bindings = inputs()
    controls = dict(id=ENTRY, kind='regression', language='ru', rowCount=len(rows), bindings=bindings,
        keys=sorted({control.key_for(row, 'regression') for row in rows}),
        semantics='Public author-written dialogue contexts; disclosed regression only, no natural-data or label qualification.')
    contexts = dict(id=ENTRY+'-contexts', usage='historical-context-exclusion', rowCount=len(rows), bindings=bindings,
        keys={'context': sorted(lexical.keys_for(rows, 'context'))}, missingAxes=[],
        notes='Public author-written dialogue token contexts; no inferred article or family identity.')
    return controls, contexts


def check():
    first, second = entries()
    a = control.load(CONTROL); b = lexical.load_ledger(LEXICAL)
    if [e for e in a['entries'] if e['id'] == ENTRY] != [first] or [e for e in b['entries'] if e['id'] == second['id']] != [second]:
        raise ValueError('DIALOGUE_REGISTRY_DRIFT')
    return len(inputs()[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true'); parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.check:
        if args.output: raise ValueError('DIALOGUE_SCOPE')
        print(json.dumps({'tokens': check(), 'independentQualification': False})); return
    if args.output is None: raise ValueError('DIALOGUE_SCOPE')
    output = args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'): raise ValueError('DIALOGUE_OUTPUT')
    old_a = CONTROL.read_bytes(); old_b = LEXICAL.read_bytes()
    first, second = entries(); bindings = first['bindings']
    a = json.loads(old_a); b = json.loads(old_b)
    control.validate(a); current = lexical.validate_ledger(copy.deepcopy(b))
    if any(e['id'] == ENTRY for e in a['entries']) or any(e['id'] == second['id'] for e in current['entries']):
        raise ValueError('DIALOGUE_EXISTS')
    a['entries'].append(first); b['entries'].append(second)
    control.validate(a); lexical.validate_ledger(copy.deepcopy(b))
    if CONTROL.read_bytes() != old_a or LEXICAL.read_bytes() != old_b or inputs()[1] != bindings:
        raise ValueError('DIALOGUE_DRIFT')
    output.mkdir(parents=True, mode=0o700)
    for name, value in (('control-ledger.json', a), ('holdout-ledger.json', b)):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'tokens': 262, 'independentQualification': False}))


if __name__ == '__main__': main()
