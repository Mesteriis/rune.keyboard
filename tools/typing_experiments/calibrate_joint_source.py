#!/usr/bin/env python3
"""Freeze complete-pool arbitration on calibration; abstentions are explicit and separately costed."""
import argparse
import json
from pathlib import Path
import joint_calibration_receipt as binding


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
    import numpy as np
    r=[x for x in records if x['band']==band]
    if not r:raise ValueError('NO_CALIBRATION')
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


def score_bound(frozen):
    import numpy as np
    import catboost
    import train_joint_correction as training
    import promote_refinement as promotion
    binding.require(np.__version__=='2.2.6' and catboost.__version__=='1.2.8','CALIBRATION_NUMERICAL_DEPENDENCIES')
    promotion.validate_tree(frozen['model'].read_bytes(),training.rank.FEATURES)
    context=training.neural.load_model(frozen['context'])
    binding.require((context.window,context.hidden)==(48,48) and training.base.CONTEXT_MODEL.resolve()==frozen['context'],
                    'CALIBRATION_CONTEXT_SHAPE')
    groups=training.groups(frozen['rows'],frozen['observations'])
    records=training.score(frozen['model'],groups)
    binding.validate_scores(records,frozen['rows'],frozen['observations'])
    frozen['scoreSummary']=dict(eligibleGroups=len(groups),totalCalibrationRows=len(frozen['rows']))
    frozen['hostScoringVersions']=dict(numpy=np.__version__,catboost=catboost.__version__)
    return normalized(records,frozen['observations'])


def run(ranker,calibration_export,output,historical_reproduction=False,corpus=None):
    ranker=Path(ranker).resolve();corpus=Path(corpus).resolve() if corpus else ranker.parent/'corpus'
    frozen=binding.freeze('source',ranker,corpus,calibration_export,ranker/'frozen-policy.json',historical_reproduction)
    output=Path(output).resolve()
    binding.require(output.is_relative_to(binding.ROOT/'build') and not output.exists() and not output.is_symlink(),'FRESH_CALIBRATION_OUTPUT')
    records=score_bound(frozen);result={band:calibrate(records,band) for band in ('short','long')}
    policy=dict(frozen['parent'],arbitration='complete joint pool; below threshold retains original; inadmissible proposal retains qualified baseline',
        thresholds=result,calibratorSha256=binding.file_hash(Path(__file__)),
        calibrationSummary=frozen['scoreSummary'],hostScoringVersions=frozen['hostScoringVersions'],
        protocolAmendment='Explicit abstention; correct-to-original <=10%; zero correct-to-wrong and no fall in correct count.')
    binding.seal_policy(frozen,policy,all(v['calibrationPassed'] for v in result.values()))
    binding.publish(frozen,output,policy,records);print(json.dumps(result),flush=True);return policy


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('ranker','calibration_export','output'):p.add_argument(name,type=Path)
    p.add_argument('--corpus',type=Path);p.add_argument('--historical-reproduction',action='store_true')
    a=p.parse_args();run(a.ranker,a.calibration_export,a.output,a.historical_reproduction,a.corpus)


if __name__=='__main__':main()
