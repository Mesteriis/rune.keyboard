#!/usr/bin/env python3
"""Evaluate full editor behavior plus an independent precision gate for new long-word replacements."""
import argparse
import json
from pathlib import Path
import train_joint_correction as training
from evaluate_joint_product import evaluate


def acquisition(rows, baseline, product):
    # evaluate() must validate matching identities and editor ownership before this join.
    correct=wrong=0
    for r,left,right in zip(rows,baseline,product,strict=True):
        if len(r['typed'])<=4:continue
        original=r['typed'].casefold()
        before=left['afterBoundary']['text'].split()[-1].casefold()
        after=right['afterBoundary']['text'].split()[-1].casefold()
        if before==original and after!=original:
            if after==r.get('expectedSpelling',r['typed']).casefold() and not r['noAuto']:correct+=1
            else:wrong+=1
    precision=correct/(correct+wrong) if correct+wrong else None
    return dict(correct=correct,wrong=wrong,precision=precision,
        passed=precision is not None and precision>=.99 and correct>=100)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['rows','baseline','product','policy','output']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();policy=json.loads(a.policy.read_text())
    if policy['stage']!='frozen-before-independent-holdout' or training.sha(a.rows)!=policy['holdoutSha256']:raise ValueError('FROZEN_HOLDOUT_IDENTITY')
    rows,baseline,product=map(training.read,[a.rows,a.baseline,a.product])
    metrics=evaluate(rows,baseline,product);new=acquisition(rows,baseline,product)
    record=dict(stage='independent-followup-product-holdout',passed=metrics['long']['passed'] and new['passed'],
        policySha256=training.sha(a.policy),rowsSha256=training.sha(a.rows),baselineSha256=training.sha(a.baseline),
        productSha256=training.sha(a.product),evaluatorSha256=training.sha(Path(__file__)),metrics=metrics,acquisition=new)
    with a.output.open('x') as stream:json.dump(record,stream,indent=2);stream.write('\n')
    print(json.dumps(record),flush=True)
    if not record['passed']:raise SystemExit(1)

if __name__=='__main__':main()
