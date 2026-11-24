#!/usr/bin/env python3
"""Evaluate frozen joint policy on actual editor outputs; never refit or mutate qualification."""
import argparse
import json
from pathlib import Path
import joint_evaluation_receipt as binding


def evaluate(rows,baseline,product):
    ids=[r['id'] for r in rows]
    if len(set(ids))!=len(ids) or [o.get('id') for o in baseline]!=ids or [o.get('id') for o in product]!=ids:raise ValueError('IDENTITY')
    result={band:dict(rows=0,typos=0,controls=0,baselineCorrect=0,baselineWrong=0,replacements=0,correct=0,wrong=0,
        newCorrect=0,newCorrectFamilies=set(),baselineCorrectToWrong=0,baselineCorrectAbstained=0,
        wrongResolved=0,controlChanges=0,undoFailures=0,prefixChanges=0) for band in ['short','long']}
    for r,left,right in zip(rows,baseline,product,strict=True):
        for o in [left,right]:
            if o.get('status')!='COMPLETE' or o.get('typed')!=r['typed'] or o.get('prefix')!=r['prefix']:raise ValueError('INPUT_CHANGED')
        if left['beforeBoundary']!=right['beforeBoundary']:raise ValueError('BEFORE_EDITOR_CHANGED')
        before=right['beforeBoundary']['text'];original=r['typed'].casefold()
        if not before.casefold().endswith(original):raise ValueError('SOURCE_WORD_CHANGED')
        prefix=before[:-len(r['typed'])];old=left['afterBoundary']['text'];new=right['afterBoundary']['text']
        expected=r.get('expectedSpelling',r['typed']).casefold()
        a=old.rstrip().split()[-1].casefold();b=new.rstrip().split()[-1].casefold()
        band='short' if len(r['typed'])<=4 else 'long';v=result[band]
        v['rows']+=1;v['controls']+=r['noAuto'];v['typos']+=not r['noAuto']
        base_correct=a==expected and a!=original and not r['noAuto']
        base_wrong=a not in (original,expected)
        changed=b!=original;correct=changed and b==expected and not r['noAuto']
        v['baselineCorrect']+=base_correct;v['baselineWrong']+=base_wrong
        v['replacements']+=changed;v['correct']+=correct;v['wrong']+=changed and not correct
        v['newCorrect']+=correct and a==original
        if correct and a==original:v['newCorrectFamilies'].add(r['family'])
        v['baselineCorrectToWrong']+=base_correct and b not in (original,expected)
        v['baselineCorrectAbstained']+=base_correct and b==original
        v['wrongResolved']+=base_wrong and b in (original,expected)
        v['controlChanges']+=changed and r['noAuto']
        v['undoFailures']+=(new!=before+' ' and right.get('restoredBeforeBoundaryExactly') is not True)
        v['prefixChanges']+=not new.startswith(prefix)
    for band,v in result.items():
        v['newCorrectFamilies']=len(v['newCorrectFamilies'])
        v['precision']=v['correct']/v['replacements'] if v['replacements'] else None
        common=(v['precision'] is not None and v['precision']>=.99 and not v['controlChanges'] and
            not v['baselineCorrectToWrong'] and not v['undoFailures'] and not v['prefixChanges'] and
            v['correct']>=v['baselineCorrect'] and v['baselineCorrectAbstained']<=.1*max(1,v['baselineCorrect']))
        specific=v['newCorrect']>=50 and v['newCorrectFamilies']>=20 if band=='short' else v['wrongResolved']>=10
        v['passed']=bool(common and specific)
    return result


def run(rows,baseline,product,policy,output,historical_reproduction=False,short_policy=None,corpus_manifest=None):
    frozen=binding.freeze(rows,baseline,product,policy,historical_reproduction,
        short_policy_path=short_policy,corpus_manifest_path=corpus_manifest)
    output=Path(output).resolve()
    binding.require(output.is_relative_to(binding.ROOT/'build') and not output.exists() and not output.is_symlink(),'FRESH_JOINT_OUTPUT')
    metrics=evaluate(frozen['rows'],frozen['baseline'],frozen['product'])
    observed=all(v['passed'] for v in metrics.values())
    record=dict(stage='disclosed-product-regression' if historical_reproduction else 'registry-checked-product-holdout',
        policySha256=frozen['receipt']['policySha256'],rowsSha256=frozen['receipt']['rowsSha256'],metrics=metrics)
    binding.finish_report(frozen,record,observed)
    encoded=json.dumps(record,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n'
    with output.open('x',encoding='utf-8') as stream:stream.write(encoded)
    print(json.dumps(record),flush=True);return record


def arguments():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('rows','baseline','product','policy','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--short-policy',type=Path);p.add_argument('--corpus-manifest',type=Path)
    p.add_argument('--historical-reproduction',action='store_true');return p.parse_args()


def main():
    a=arguments();record=run(a.rows,a.baseline,a.product,a.policy,a.output,a.historical_reproduction,a.short_policy,a.corpus_manifest)
    if not record['passed']:raise SystemExit(1)


if __name__=='__main__':main()
