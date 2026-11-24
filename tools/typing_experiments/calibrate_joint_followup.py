#!/usr/bin/env python3
"""Calibrate acquisition separately from retention on fresh public word families."""
import argparse
import json
from pathlib import Path
import joint_calibration_receipt as binding
import calibrate_joint_source as source


def final_word(r, score, margin):
    if r['topScore'] < score or r['margin'] < margin: return r['original']
    candidate=r['candidate']
    # A baseline decision may only be retained or vetoed; never replaced by a third word.
    if r['baseline'] != r['original'] and candidate != r['baseline']: return r['original']
    return candidate


def metric(records, score, margin):
    rewritten=[dict(r,candidate=final_word(r,score,margin),topScore=1.,margin=1.) for r in records]
    return source.full_metrics(rewritten,0.,0.)


def calibrate(records, retention):
    import numpy as np
    values=[r for r in records if (r['baseline']!=r['original']) == retention and r['band']=='long']
    if not values: raise ValueError('NO_CALIBRATION')
    scores=np.unique(np.quantile([r['topScore'] for r in values],np.linspace(0,1,65)))
    margins=np.unique(np.quantile([r['margin'] for r in values],np.linspace(0,1,65)))
    best=None
    for s in scores:
        for m in margins:
            if m<=0:continue
            result=metric(values,s,m)
            if result['controlChanges'] or result['baselineCorrectToWrong']:continue
            if retention:
                if result['baselineCorrectAbstained']>.1*max(1,result['baselineCorrect']) or result['wrongResolved']<10:continue
                key=(result['wrongResolved'],-result['baselineCorrectAbstained'],s,m)
            else:
                if result['newCorrect']<100 or result['precision'] is None or result['precision']<.995:continue
                key=(result['newCorrect'],-result['wrong'],s,m)
            if best is None or key>best[0]:best=(key,float(s),float(m),result)
    if best is None:return dict(calibrationPassed=False,minimumScore=2.,minimumMargin=2.,metrics=metric(values,2.,2.))
    return dict(calibrationPassed=True,minimumScore=best[1],minimumMargin=best[2],metrics=best[3])


def run(root,export,output,historical_reproduction=False,corpus=None):
    root=Path(root).resolve()
    frozen=binding.freeze('followup',root/'ranker',Path(corpus).resolve() if corpus else root/'followup-corpus',export,
                          root/'arbitration-v3/frozen-policy.json',historical_reproduction)
    output=Path(output).resolve()
    binding.require(output.is_relative_to(binding.ROOT/'build') and not output.exists() and not output.is_symlink(),'FRESH_CALIBRATION_OUTPUT')
    records=source.score_bound(frozen);by_id={o['id']:o for o in frozen['observations']}
    for record in records:
        winner=max(range(len(record['scores'])),key=lambda i:(record['scores'][i],-i))
        raw=by_id[record['id']]['jointSearch']['alternatives'][winner-1]['text'].casefold() if winner else record['original']
        if record['baseline']!=record['original'] and raw!=record['baseline']:record['candidate']=record['original']
    result={name:calibrate(records,retention) for name,retention in [('acquisition',False),('retention',True)]}
    parent=frozen['parent'];policy=dict(schema=1,modelSha256=parent['modelSha256'],contextSha256=parent['contextSha256'],
        shortPolicySha256=frozen['receipt']['parentPolicySha256'],holdoutSha256=frozen['receipt']['holdoutSha256'],
        corpusSha256=frozen['receipt']['corpusManifestSha256'],thresholds=result,calibratorSha256=binding.file_hash(Path(__file__)),
        calibrationSummary=frozen['scoreSummary'],hostScoringVersions=frozen['hostScoringVersions'],
        protocol='Acquisition calibration >=99.5%, independent >=99%; retention never introduces a third word, resolves >=10 old errors and abstains <=10% of old correct.')
    observed=all(v['calibrationPassed'] for v in result.values());binding.seal_policy(frozen,policy,observed)
    short=parent['thresholds']['short'];acq=result['acquisition'];ret=result['retention']
    config='\t'.join(map(str,[frozen['model'],parent['modelSha256'],short['minimumScore'],short['minimumMargin'],
        acq['minimumScore'],acq['minimumMargin'],ret['minimumScore'],ret['minimumMargin']]))+'\n'
    binding.publish(frozen,output,policy,records,config);print(json.dumps(result),flush=True);return policy


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('root','export','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--historical-reproduction',action='store_true');p.add_argument('--corpus',type=Path);a=p.parse_args()
    policy=run(a.root,a.export,a.output,a.historical_reproduction,a.corpus)
    if not policy['observedCalibrationPassed']:raise SystemExit(1)


if __name__=='__main__':main()
