"""Protect disclosed synthetic empty-prefix controller candidate contexts."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/typing_experiments'), str(ROOT / 'tools/ci')]
import control_ledger as control
import holdout_ledger as lexical

CONTROL = ROOT / 'tools/typing_experiments/control-ledger.json'
LEXICAL = ROOT / 'tools/typing_experiments/holdout-ledger.json'
ENTRY = 'a2-empty-controller-candidate-contexts-v1'
WORD = re.compile('[а-яё]+', re.IGNORECASE)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


SEARCH = ROOT / 'tools/typing_experiments/a2-empty-controller-v1'
PROJECTION_SHA = '4b367eefa761e569cb7c8738ddd8eeac36cbdd4318cec2b5f8a935b157ea304f'


def inputs():
    import register_a2_empty_prefix as source
    source.check()
    projection=(SEARCH/'projection.jsonl').read_bytes(); receipt=json.loads((SEARCH/'receipt.json').read_bytes())
    if (sha(projection)!=PROJECTION_SHA or receipt.get('projectionSha256')!=PROJECTION_SHA or
        receipt.get('scope')!='disclosed-empty-prefix-controller-probe' or receipt.get('independentQualification') is not False or
        receipt.get('rows')!=1 or receipt.get('deterministic') is not True or receipt.get('modelCalls')!=0):
        raise ValueError('EMPTY_CONTROLLER_BINDING')
    rows=[json.loads(line) for line in projection.splitlines()]
    if len(rows)!=1:raise ValueError('EMPTY_CONTROLLER_ROWS')
    row=rows[0]
    if (row.get('id')!='replay-00000000' or row.get('typed')!='молоо' or row.get('prefix')!='' or
        row.get('status')!='COMPLETE' or row.get('language')!='ru' or row.get('actualModelRequest') is not None):
        raise ValueError('EMPTY_CONTROLLER_IDENTITY')
    values={'молоо','молоко'}
    for field in ('fullTokenGeneration','actualRequestGeneration','manualSearchGeneration'):
        gen=row.get(field)
        if not isinstance(gen,dict):raise ValueError('EMPTY_CONTROLLER_GENERATION')
        lists=[gen.get('alternatives'),gen.get('compactAlternatives')]
        for nested in ('localSearch','neighborRecovery'):
            item=gen.get(nested)
            if not isinstance(item,dict):raise ValueError('EMPTY_CONTROLLER_GENERATION')
            lists.append(item.get('alternatives'))
        for candidates in lists:
            if not isinstance(candidates,list):raise ValueError('EMPTY_CONTROLLER_GENERATION')
            for candidate in candidates:
                token=candidate.get('text') if isinstance(candidate,dict) else None
                if not isinstance(token,str) or not WORD.fullmatch(token):raise ValueError('EMPTY_CONTROLLER_TOKEN')
                values.add(token)
    view=row.get('candidateView',{}).get('candidates')
    if not isinstance(view,list):raise ValueError('EMPTY_CONTROLLER_GENERATION')
    for candidate in view:
        token=candidate.get('text') if isinstance(candidate,dict) else None
        if not isinstance(token,str) or not WORD.fullmatch(token):raise ValueError('EMPTY_CONTROLLER_TOKEN')
        values.add(token)
    records=[dict(language='ru',prefix='',typed=token,expectedSpelling=token) for token in sorted(values)]
    paths=[Path(__file__).resolve(),Path(source.__file__).resolve(),SEARCH/'projection.jsonl',SEARCH/'receipt.json',SEARCH/'NOTICE.md',
           source.DATA/'cases.json',source.DATA/'NOTICE.md']
    return records,{str(path.relative_to(ROOT)):sha(path.read_bytes()) for path in paths}


def entries():
    rows, bindings = inputs()
    controls = dict(id=ENTRY, kind='regression', language='ru', rowCount=len(rows), bindings=bindings,
        keys=sorted({control.key_for(row, 'regression') for row in rows}),
        semantics='Disclosed synthetic empty-prefix controller candidates; not qualification.')
    contexts = dict(id=ENTRY+'-contexts', usage='historical-context-exclusion', rowCount=len(rows), bindings=bindings,
        keys={'context': sorted(lexical.keys_for(rows, 'context'))}, missingAxes=[],
        notes='Disclosed empty-prefix candidate contexts; no inferred article or family identity.')
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
    print(json.dumps({'tokens': len(inputs()[0]), 'independentQualification': False}))


if __name__ == '__main__': main()
