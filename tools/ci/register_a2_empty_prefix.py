"""Protect disclosed synthetic empty-prefix scorer controls."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/typing_experiments'))
import control_ledger as control
import holdout_ledger as lexical

DATA=ROOT/'tools/typing_experiments/a2-empty-prefix-controls-v1'
CONTROL=ROOT/'tools/typing_experiments/control-ledger.json'
LEXICAL=ROOT/'tools/typing_experiments/holdout-ledger.json'
ENTRY='a2-empty-prefix-synthetic-v1'


def sha(raw): return hashlib.sha256(raw).hexdigest()


def inputs():
    raw=(DATA/'cases.json').read_bytes();cases=json.loads(raw)
    if len(cases)!=5 or len({case.get('id') for case in cases})!=5:raise ValueError('A2_EMPTY_SCOPE')
    rows=[]
    for case in cases:
        if (set(case)!={'id','language','prefix','candidates'} or case['language'] not in ('en','ru') or
            case['prefix'] not in ('',' ') or not isinstance(case['candidates'],list) or len(case['candidates'])!=2 or
            any(not isinstance(x,str) or not x or not x.isalpha() for x in case['candidates'])):
            raise ValueError('A2_EMPTY_CASE')
        for word in case['candidates']:
            rows.append(dict(language=case['language'],prefix=case['prefix'],typed=word,expectedSpelling=word))
    paths=(Path(__file__).resolve(),DATA/'cases.json',DATA/'NOTICE.md')
    return rows,{str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in paths}


def entries():
    rows,bindings=inputs();result=[]
    for language in ('en','ru'):
        selected=[row for row in rows if row['language']==language]
        result.append(dict(id=ENTRY+'-'+language,kind='regression',language=language,rowCount=len(selected),bindings=bindings,
            keys=sorted({control.key_for(row,'regression') for row in selected}),
            semantics='Disclosed synthetic scorer candidate contexts; no independent qualification.'))
    ru=[row for row in rows if row['language']=='ru']
    result.append(dict(id=ENTRY+'-ru-contexts',usage='historical-context-exclusion',rowCount=len(ru),bindings=bindings,
        keys={'context':sorted(lexical.keys_for(ru,'context'))},missingAxes=[],
        notes='Previously scored synthetic Russian candidate contexts; no family or source-article identity.'))
    return result


def check():
    expected=entries();a=control.load(CONTROL);b=lexical.load_ledger(LEXICAL)
    for entry in expected:
        ledger=b if entry['id'].endswith('-contexts') else a
        if [v for v in ledger['entries'] if v['id']==entry['id']]!=[entry]:raise ValueError('A2_EMPTY_REGISTRY_DRIFT')
    return len(inputs()[0])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');p.add_argument('--output',type=Path);args=p.parse_args()
    if args.check:
        if args.output:raise ValueError('A2_EMPTY_ARGS')
        print(json.dumps({'contexts':check(),'independentQualification':False}));return
    if args.output is None:raise ValueError('A2_EMPTY_ARGS')
    out=args.output.resolve()
    if out.exists() or not out.is_relative_to(ROOT/'build'):raise ValueError('A2_EMPTY_OUTPUT')
    old_a=CONTROL.read_bytes();old_b=LEXICAL.read_bytes();a=json.loads(old_a);b=json.loads(old_b)
    control.validate(a);logical=lexical.validate_ledger(copy.deepcopy(b));added=entries();ids={x['id'] for x in added}
    if any(e['id'] in ids for e in a['entries']+logical['entries']):raise ValueError('A2_EMPTY_EXISTS')
    a['entries'].extend(added[:2]);b['entries'].append(added[2]);control.validate(a);lexical.validate_ledger(copy.deepcopy(b))
    if CONTROL.read_bytes()!=old_a or LEXICAL.read_bytes()!=old_b or entries()!=added:raise ValueError('A2_EMPTY_DRIFT')
    out.mkdir(parents=True,mode=0o700)
    for name,value in (('control-ledger.json',a),('holdout-ledger.json',b)):
        (out/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'contexts':len(inputs()[0]),'independentQualification':False}))


if __name__=='__main__':main()
