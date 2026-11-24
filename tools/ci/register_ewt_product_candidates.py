"""Quarantine the disclosed candidate contexts of a model-free EWT replay."""
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
import register_ewt_product_contexts as source

LEDGER=ROOT/'tools/typing_experiments/control-ledger.json'
FIXTURE=ROOT/'tools/ci/ewt-product-candidates-v1.json'
ENTRY='public-ewt-product-candidate-contexts-v1'
HASH=re.compile(r'[0-9a-f]{64}\Z')


def candidates(observation):
    result=set()
    def add(values):
        if not isinstance(values,list):raise ValueError('EWT_CANDIDATE_LIST')
        for item in values:
            if not isinstance(item,dict) or not isinstance(item.get('text'),str) or not item['text']:
                raise ValueError('EWT_CANDIDATE_ROW')
            result.add(item['text'])
    view=observation.get('candidateView')
    if not isinstance(view,dict):raise ValueError('EWT_CANDIDATE_VIEW')
    add(view.get('candidates'))
    for name in ('fullTokenGeneration','actualRequestGeneration','manualSearchGeneration'):
        generation=observation.get(name)
        if generation is None and name!='fullTokenGeneration':continue
        if not isinstance(generation,dict):raise ValueError('EWT_CANDIDATE_GENERATION')
        add(generation.get('alternatives'));add(generation.get('compactAlternatives'))
        for nested in ('localSearch','neighborRecovery'):
            value=generation.get(nested)
            if not isinstance(value,dict):raise ValueError('EWT_CANDIDATE_GENERATION')
            add(value.get('alternatives'))
    edit=observation.get('autoEdit')
    if edit is not None:
        if not isinstance(edit,dict) or not isinstance(edit.get('applied'),str) or not edit['applied']:
            raise ValueError('EWT_CANDIDATE_EDIT')
        result.add(edit['applied'])
    return result


def collect(data,run):
    summary=replay.summarize(data,run)
    ledger_raw=LEDGER.read_bytes();ledger=control.validate(json.loads(ledger_raw));original=source.entry()
    if [e for e in ledger['entries'] if e['id']==source.ENTRY]!=[original]:raise ValueError('EWT_CANDIDATE_SOURCE')
    inputs_path=data/'inputs.jsonl';projection_path=run/'projection.jsonl'
    input_raw=inputs_path.read_bytes();projection_raw=projection_path.read_bytes()
    manifest=json.loads((data/'manifest.json').read_bytes())
    if (model.sha(input_raw)!=manifest.get('inputSha256') or
            model.sha(projection_raw)!=summary['projectionSha256']):raise ValueError('EWT_CANDIDATE_INPUT_DRIFT')
    rows=[json.loads(x) for x in input_raw.splitlines()]
    obs=[json.loads(x) for x in projection_raw.splitlines()]
    keys=set();pairs=0;changed_case=0;other_changes=0
    for row,observation in zip(rows,obs,strict=True):
        values=candidates(observation);pairs+=len(values)
        keys.update(control.key_for({'language':'en','prefix':row['prefix'],'typed':word},'regression') for word in values)
        before=observation['beforeBoundary']['text']+' ';after=observation['afterBoundary']['text']
        if before!=after:
            if before.casefold()==after.casefold():changed_case+=1
            else:other_changes+=1
    if (LEDGER.read_bytes()!=ledger_raw or inputs_path.read_bytes()!=input_raw or
            projection_path.read_bytes()!=projection_raw or source.entry()!=original):
        raise ValueError('EWT_CANDIDATE_INPUT_DRIFT')
    return dict(schemaVersion=1,scope='disclosed-ewt-product-candidates',rows=len(rows),candidateOccurrences=pairs,
        keys=sorted(keys),caseOnlyChanges=changed_case,otherChanges=other_changes,
        replaySummarySha256=model.sha(json.dumps(summary,sort_keys=True,separators=(',',':')).encode()),
        sourceFixtureSha256=model.sha(source.FIXTURE.read_bytes()),projectionSha256=summary['projectionSha256'],
        extractorSha256=model.sha(Path(replay.__file__).read_bytes()),independentQualification=False)


def entry():
    value=json.loads(FIXTURE.read_bytes());keys=value.get('keys')
    if (value.get('schemaVersion')!=1 or value.get('scope')!='disclosed-ewt-product-candidates' or
        value.get('independentQualification') is not False or value.get('extractorSha256')!=model.sha(Path(replay.__file__).read_bytes()) or
        value.get('sourceFixtureSha256')!=model.sha(source.FIXTURE.read_bytes()) or
        type(value.get('rows')) is not int or value['rows']<1 or not isinstance(keys,list) or not keys or
        keys!=sorted(set(keys)) or any(not isinstance(k,str) or not HASH.fullmatch(k) for k in keys) or
        any(not isinstance(value.get(name),str) or not HASH.fullmatch(value[name]) for name in ('replaySummarySha256','projectionSha256'))):
        raise ValueError('EWT_CANDIDATE_FIXTURE')
    paths=(Path(__file__).resolve(),FIXTURE,source.FIXTURE,Path(source.__file__).resolve(),Path(replay.__file__).resolve())
    return dict(id=ENTRY,kind='regression',language='en',rowCount=len(keys),keys=keys,
        bindings={str(p.relative_to(ROOT)):model.sha(p.read_bytes()) for p in paths},
        semantics='Candidate and applied contexts disclosed during EWT product replay; not an independent holdout.')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data',type=Path);p.add_argument('--replay',type=Path);p.add_argument('--output',type=Path);p.add_argument('--check',action='store_true')
    args=p.parse_args()
    if args.check:
        if args.data or args.replay or args.output:raise ValueError('EWT_CANDIDATE_SCOPE')
        expected=entry();ledger=control.load(LEDGER)
        if [e for e in ledger['entries'] if e['id']==ENTRY]!=[expected]:raise ValueError('EWT_CANDIDATE_LEDGER_DRIFT')
        print(json.dumps({'keys':len(expected['keys']),'independentQualification':False}));return
    if args.output is None or bool(args.data)!=bool(args.replay):raise ValueError('EWT_CANDIDATE_SCOPE')
    out=args.output.resolve()
    if out.exists() or not out.is_relative_to(ROOT/'build'):raise ValueError('EWT_CANDIDATE_OUTPUT')
    if args.data:value=collect(args.data,args.replay)
    else:
        old=LEDGER.read_bytes();value=control.validate(json.loads(old));expected=entry()
        if any(e['id']==ENTRY for e in value['entries']):raise ValueError('EWT_CANDIDATE_EXISTS')
        value['entries'].append(expected);control.validate(value)
        if LEDGER.read_bytes()!=old or entry()!=expected:raise ValueError('EWT_CANDIDATE_DRIFT')
    with out.open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps({'keys':len(value['keys']) if args.data else len(expected['keys']),'independentQualification':False}))


if __name__=='__main__':main()
