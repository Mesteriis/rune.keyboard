#!/usr/bin/env python3
"""Calibrate acquisition separately from retention on fresh public word families."""
import argparse
import json
from pathlib import Path
import numpy as np
import train_joint_correction as training
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


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['root','export','output']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();root=a.root.resolve();out=a.output.resolve()
    if out.exists():raise ValueError('FRESH_OUTPUT')
    rows=training.read(root/'followup-corpus/calibration.jsonl');obs=training.read(a.export/'observations.jsonl')
    records=source.normalized(training.score(root/'ranker/joint-ranker.bin',training.groups(rows,obs)),obs)
    by_id={o['id']:o for o in obs}
    for r in records:
        winner=max(range(len(r['scores'])),key=lambda i:(r['scores'][i],-i))
        raw=by_id[r['id']]['jointSearch']['alternatives'][winner-1]['text'].casefold() if winner else r['original']
        if r['baseline']!=r['original'] and raw!=r['baseline']:r['candidate']=r['original']
    result={name:calibrate(records,retention) for name,retention in [('acquisition',False),('retention',True)]}
    out.mkdir(parents=True);old=json.loads((root/'arbitration-v3/frozen-policy.json').read_text())
    policy=dict(schema=1,stage='frozen-before-independent-holdout',modelSha256=old['modelSha256'],
        contextSha256=old['contextSha256'],shortPolicySha256=training.sha(root/'arbitration-v3/frozen-policy.json'),
        holdoutSha256=training.sha(root/'followup-corpus/holdout.jsonl'),
        corpusSha256=training.sha(root/'followup-corpus/manifest.json'),calibrationExportSha256=training.sha(a.export/'observations.jsonl'),
        thresholds=result,calibratorSha256=training.sha(Path(__file__)),
        protocol='Fresh article and lemma disjoint splits. Acquisition calibration precision >=99.5%, independent >=99%; retention cannot introduce a third word, resolves >=10 old errors, abstains <=10% of old correct. Full product precision >=99%, net correct cannot fall; controls, correct-to-wrong, prefix and Undo failures must be zero.')
    training.write(out/'frozen-policy.json',policy);training.write(out/'calibration-scores.json',records)
    short=old['thresholds']['short'];acq=result['acquisition'];retain=result['retention']
    (out/'config.tsv').write_text('\t'.join(map(str,[root/'ranker/joint-ranker.bin',old['modelSha256'],short['minimumScore'],short['minimumMargin'],acq['minimumScore'],acq['minimumMargin'],retain['minimumScore'],retain['minimumMargin']]))+'\n')
    print(json.dumps(result),flush=True)
    if not all(v['calibrationPassed'] for v in result.values()):raise SystemExit(1)

if __name__=='__main__':main()
