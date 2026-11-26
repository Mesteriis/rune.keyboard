#!/usr/bin/env python3
"""Freeze complete-pool arbitration on calibration; abstentions are explicit and separately costed."""
import argparse
import json
from pathlib import Path
import numpy as np
import train_joint_correction as training


def normalized(records,observations):
    by_id={o['id']:o for o in observations}
    output=[]
    for r in records:
        o=by_id[r['id']];pool=o['jointSearch']['alternatives'];scores=r['scores']
        if len(scores)!=len(pool)+1:raise ValueError('SCORE_POOL_IDENTITY')
        winner=max(range(len(scores)),key=lambda i:(scores[i],-i))
        candidate=pool[winner-1]['text'] if winner else r['original']
        allowed=not winner or o['jointAdmission'].get(candidate) is True
        output.append(dict(r,candidate=candidate.casefold() if allowed else r['baseline']))
    return output


def full_metrics(records,minimum_score,minimum_margin):
    final=[r['candidate'] if r['topScore']>=minimum_score and r['margin']>=minimum_margin else r['original'] for r in records]
    lexical=[(r,c) for r,c in zip(records,final) if c!=r['original']]
    base_correct=[(r,c) for r,c in zip(records,final) if r['baseline']==r['expected'] and r['baseline']!=r['original']]
    base_wrong=[(r,c) for r,c in zip(records,final) if r['baseline'] not in (r['expected'],r['original'])]
    correct=sum(c==r['expected'] and not r['control'] for r,c in lexical)
    wrong=len(lexical)-correct
    return dict(replacements=len(lexical),correct=correct,wrong=wrong,precision=correct/len(lexical) if lexical else None,
        baselineCorrect=len(base_correct),baselineWrong=len(base_wrong),
        baselineCorrectToWrong=sum(c not in (r['expected'],r['original']) for r,c in base_correct),
        baselineCorrectAbstained=sum(c==r['original'] for r,c in base_correct),
        wrongResolved=sum(c in (r['expected'],r['original']) for r,c in base_wrong),
        controlChanges=sum(r['control'] for r,c in lexical),
        newCorrect=sum(r['baseline']==r['original'] and c==r['expected'] and not r['control'] for r,c in lexical),
        newCorrectFamilies=len({r['family'] for r,c in lexical if r['baseline']==r['original'] and c==r['expected'] and not r['control']}))


def calibrate(records,band):
    r=[x for x in records if x['band']==band]
    scores=np.unique(np.quantile([x['topScore'] for x in r],np.linspace(0,1,65)))
    margins=np.unique(np.quantile([x['margin'] for x in r],np.linspace(0,1,65)))
    best=None
    for s in scores:
        for m in margins:
            if m<=0:continue
            metric=full_metrics(r,s,m)
            if (metric['precision'] is None or metric['precision']<.99 or metric['controlChanges'] or
                metric['baselineCorrectToWrong'] or metric['correct']<metric['baselineCorrect'] or
                metric['baselineCorrectAbstained']>.1*max(1,metric['baselineCorrect'])):continue
            if band=='short' and (metric['newCorrect']<50 or metric['newCorrectFamilies']<20):continue
            if band=='long' and metric['wrongResolved']<10:continue
            key=(metric['correct'],-metric['wrong'],metric['wrongResolved'],s,m)
            if best is None or key>best[0]:best=(key,float(s),float(m),metric)
    if best is None:return dict(calibrationPassed=False,minimumScore=2.,minimumMargin=2.,metrics=full_metrics(r,2.,2.))
    return dict(calibrationPassed=True,minimumScore=best[1],minimumMargin=best[2],metrics=best[3])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('ranker',type=Path);p.add_argument('calibration_export',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args()
    if a.output.exists():raise ValueError('FRESH_OUTPUT')
    old=json.loads((a.ranker/'frozen-policy.json').read_text())
    if training.sha(a.ranker/'joint-ranker.bin')!=old['modelSha256']:raise ValueError('MODEL_DRIFT')
    records=normalized(json.loads((a.ranker/'calibration-scores.json').read_text()),training.read(a.calibration_export/'observations.jsonl'))
    a.output.mkdir();result={b:calibrate(records,b) for b in ['short','long']}
    policy=dict(old,stage='frozen-before-independent-holdout',arbitration='complete joint pool; below threshold retains original; inadmissible selected proposal leaves the qualified baseline untouched',
        thresholds=result,calibratorSha256=training.sha(Path(__file__)),
        protocolAmendment='Before opening holdout: replace legacy fallback with explicit abstention; count correct-to-original separately, capped at 10%, while correct-to-wrong must remain zero and total correct cannot fall.')
    training.write(a.output/'frozen-policy.json',policy)
    training.write(a.output/'calibration-scores.json',records)
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
