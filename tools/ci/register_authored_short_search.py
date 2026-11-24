"""Register public author-written dialogue contexts before any product replay."""
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

FIXTURE = ROOT / 'tools/typing_experiments/authored-dialogue-v1'
CONTROL = ROOT / 'tools/typing_experiments/control-ledger.json'
LEXICAL = ROOT / 'tools/typing_experiments/holdout-ledger.json'
ENTRY = 'authored-dialogue-short-search-outputs-v1'
PINS = {'dialogues.jsonl': '2599fe92d9f976e262f89b50dc5ec02b97bd2c3f2edad965b83d74e38ecd4169',
        'README.md': '5b26ae1c2da28ff5c5d9ffd621b4ffbb75074fc4e6608efd646f7bb0a64c2d9b'}
WORD = re.compile('[а-яё]+', re.IGNORECASE)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


SEARCH = ROOT / 'tools/typing_experiments/authored-short-search-v1'
PROJECTION_SHA = '12af2012a533b764d508ccb337d21127d2fd7b04204d2856130c4557956438ec'


def inputs():
    import register_authored_typo_inputs as source
    source.check()
    cases=[x for x in source.cases() if x[1].split()[-1] in ('мето','двох','собй')]
    projection=(SEARCH/'projection.jsonl').read_bytes(); receipt=json.loads((SEARCH/'receipt.json').read_bytes())
    if (sha(projection)!=PROJECTION_SHA or receipt.get('projectionSha256')!=PROJECTION_SHA or
        receipt.get('scope')!='disclosed-short-search-screen' or receipt.get('independentQualification') is not False or
        receipt.get('rows')!=3 or receipt.get('deterministic') is not True or receipt.get('modelCalls')!=0 or len(cases)!=3):
        raise ValueError('SHORT_SEARCH_BINDING')
    observations=[json.loads(line) for line in projection.splitlines()]
    if len(observations)!=len(cases):raise ValueError('SHORT_SEARCH_ROWS')
    values=set()
    for index,((_,phrase,target),row) in enumerate(zip(cases,observations,strict=True)):
        words=phrase.split();typed=words[-1];prefix=' '.join(words[:-1])
        if (row.get('id')!=f'replay-{index:08d}' or row.get('typed')!=typed or row.get('prefix')!=prefix or
            row.get('status')!='COMPLETE' or row.get('language')!='ru'):
            raise ValueError('SHORT_SEARCH_IDENTITY')
        values.update(((prefix,typed),(prefix,target)))
        for field in ('fullTokenGeneration','actualRequestGeneration','manualSearchGeneration'):
            gen=row.get(field)
            if not isinstance(gen,dict):raise ValueError('SHORT_SEARCH_GENERATION')
            lists=[gen.get('alternatives'),gen.get('compactAlternatives')]
            for nested in ('localSearch','neighborRecovery'):
                item=gen.get(nested)
                if not isinstance(item,dict):raise ValueError('SHORT_SEARCH_GENERATION')
                lists.append(item.get('alternatives'))
            for candidates in lists:
                if not isinstance(candidates,list):raise ValueError('SHORT_SEARCH_GENERATION')
                for candidate in candidates:
                    token=candidate.get('text') if isinstance(candidate,dict) else None
                    if not isinstance(token,str) or not WORD.fullmatch(token):raise ValueError('SHORT_SEARCH_TOKEN')
                    values.add((prefix,token))
        view=row.get('candidateView',{}).get('candidates')
        if not isinstance(view,list):raise ValueError('SHORT_SEARCH_GENERATION')
        for candidate in view:
            token=candidate.get('text') if isinstance(candidate,dict) else None
            if not isinstance(token,str) or not WORD.fullmatch(token):raise ValueError('SHORT_SEARCH_TOKEN')
            values.add((prefix,token))
    rows=[dict(language='ru',prefix=prefix,typed=token,expectedSpelling=token) for prefix,token in sorted(values)]
    paths=[Path(__file__).resolve(),Path(source.__file__).resolve(),SEARCH/'projection.jsonl',SEARCH/'receipt.json',SEARCH/'NOTICE.md',
           ROOT/'tools/ci/register_authored_dialogue.py',ROOT/'tools/ci/register_authored_phrase_inputs.py',
           *[FIXTURE/name for name in PINS],FIXTURE/'NOTICE.md']
    return rows,{str(path.relative_to(ROOT)):sha(path.read_bytes()) for path in paths}


def entries():
    rows, bindings = inputs()
    controls = dict(id=ENTRY, kind='regression', language='ru', rowCount=len(rows), bindings=bindings,
        keys=sorted({control.key_for(row, 'regression') for row in rows}),
        semantics='Previously disclosed public synthetic short-word search input, target and candidate contexts; not qualification.')
    contexts = dict(id=ENTRY+'-contexts', usage='historical-context-exclusion', rowCount=len(rows), bindings=bindings,
        keys={'context': sorted(lexical.keys_for(rows, 'context'))}, missingAxes=[],
        notes='Disclosed short-word candidate contexts; no inferred article or family identity.')
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
