"""Register exact disclosed EWT replay contexts without retaining source text."""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/typing_experiments'))
import control_ledger as control
import english_ewt_error_model as model
import ewt_product_replay as replay

LEDGER=ROOT/'tools/typing_experiments/control-ledger.json'
FIXTURE=ROOT/'tools/ci/ewt-product-contexts-v1.json'
ENTRY='public-ewt-product-replay-contexts-v1'
HASH=re.compile(r'[0-9a-f]{64}\Z')


def collect(data):
    paths=[data/'inputs.jsonl',data/'labels.jsonl',data/'manifest.json']
    raw=[p.read_bytes() for p in paths];m=json.loads(raw[2])
    if (m.get('scope')!='disclosed-ewt-replay-not-qualification' or m.get('independentQualification') is not False or
            m.get('sourceLockSha256')!=model.LOCK_SHA or m.get('inputSha256')!=model.sha(raw[0]) or
            m.get('labelSha256')!=model.sha(raw[1]) or m.get('analyzerSha256')!=model.sha(Path(replay.__file__).read_bytes())):
        raise ValueError('EWT_CONTEXT_DATA_DRIFT')
    inputs=[json.loads(x) for x in raw[0].splitlines()];labels=[json.loads(x) for x in raw[1].splitlines()]
    if len(inputs)!=len(labels) or len(inputs)!=m.get('rows'):raise ValueError('EWT_CONTEXT_COUNT')
    keys=set()
    for row,label in zip(inputs,labels,strict=True):
        if (row.get('id')!=label.get('id') or row.get('language')!='en' or not isinstance(row.get('prefix'),str) or
                not isinstance(row.get('typed'),str) or not isinstance(label.get('expected'),str)):
            raise ValueError('EWT_CONTEXT_ROW')
        for word in (row['typed'],label['expected']):
            keys.add(control.key_for({'language':'en','prefix':row['prefix'],'typed':word},'regression'))
    if any(p.read_bytes()!=value for p,value in zip(paths,raw,strict=True)):raise ValueError('EWT_CONTEXT_INPUT_DRIFT')
    return dict(schemaVersion=1,scope='disclosed-ewt-product-contexts',rows=len(inputs),keys=sorted(keys),
        sourceLockSha256=model.LOCK_SHA,inputSha256=model.sha(raw[0]),labelSha256=model.sha(raw[1]),
        extractorSha256=model.sha(Path(replay.__file__).read_bytes()),independentQualification=False)


def entry():
    value=json.loads(FIXTURE.read_bytes());keys=value.get('keys')
    if (value.get('schemaVersion')!=1 or value.get('scope')!='disclosed-ewt-product-contexts' or
        value.get('independentQualification') is not False or value.get('sourceLockSha256')!=model.LOCK_SHA or
        value.get('extractorSha256')!=model.sha(Path(replay.__file__).read_bytes()) or
        type(value.get('rows')) is not int or value['rows']<1 or not isinstance(keys,list) or not keys or
        keys!=sorted(set(keys)) or any(not isinstance(k,str) or not HASH.fullmatch(k) for k in keys) or
        any(not isinstance(value.get(name),str) or not HASH.fullmatch(value[name]) for name in ('inputSha256','labelSha256'))):
        raise ValueError('EWT_CONTEXT_FIXTURE')
    paths=(Path(__file__).resolve(),FIXTURE,Path(replay.__file__).resolve(),Path(model.__file__).resolve(),model.VOCAB,model.ewt.LOCK)
    return dict(id=ENTRY,kind='regression',language='en',rowCount=len(keys),keys=keys,
        bindings={str(p.relative_to(ROOT)):model.sha(p.read_bytes()) for p in paths},
        semantics='Previously disclosed EWT product replay inputs and annotated target contexts; not a fresh holdout.')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--collect',type=Path);p.add_argument('--output',type=Path);p.add_argument('--check',action='store_true')
    args=p.parse_args()
    if args.check:
        if args.collect or args.output:raise ValueError('EWT_CONTEXT_SCOPE')
        expected=entry();ledger=control.load(LEDGER)
        if [e for e in ledger['entries'] if e['id']==ENTRY]!=[expected]:raise ValueError('EWT_CONTEXT_LEDGER_DRIFT')
        print(json.dumps({'keys':len(expected['keys']),'independentQualification':False}));return
    if args.output is None:raise ValueError('EWT_CONTEXT_SCOPE')
    output=args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('EWT_CONTEXT_OUTPUT')
    if args.collect:
        value=collect(args.collect)
    else:
        before=LEDGER.read_bytes();value=control.validate(json.loads(before));expected=entry()
        if any(e['id']==ENTRY for e in value['entries']):raise ValueError('EWT_CONTEXT_EXISTS')
        value['entries'].append(expected);control.validate(value)
        if LEDGER.read_bytes()!=before or entry()!=expected:raise ValueError('EWT_CONTEXT_LEDGER_DRIFT')
    with output.open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps({'keys':len(value['keys']) if args.collect else len(expected['keys']),'independentQualification':False}))


if __name__=='__main__':main()
