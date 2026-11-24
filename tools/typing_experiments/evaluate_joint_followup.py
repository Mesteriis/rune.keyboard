#!/usr/bin/env python3
"""Evaluate full editor behavior plus an independent precision gate for new long-word replacements."""
import argparse
import json
from pathlib import Path
import joint_evaluation_receipt as binding
from evaluate_joint_product import evaluate,arguments


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


def run(rows,baseline,product,policy,output,historical_reproduction=False,short_policy=None,corpus_manifest=None):
    frozen=binding.freeze(rows,baseline,product,policy,historical_reproduction,
        short_policy_path=short_policy,corpus_manifest_path=corpus_manifest)
    output=Path(output).resolve()
    binding.require(output.is_relative_to(binding.ROOT/'build') and not output.exists() and not output.is_symlink(),'FRESH_JOINT_OUTPUT')
    metrics=evaluate(frozen['rows'],frozen['baseline'],frozen['product'])
    new=acquisition(frozen['rows'],frozen['baseline'],frozen['product'])
    observed=metrics['long']['passed'] and new['passed']
    record=dict(stage='disclosed-followup-regression' if historical_reproduction else 'registry-checked-followup-holdout',
        policySha256=frozen['receipt']['policySha256'],rowsSha256=frozen['receipt']['rowsSha256'],metrics=metrics,acquisition=new)
    binding.finish_report(frozen,record,observed)
    encoded=json.dumps(record,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n'
    with output.open('x',encoding='utf-8') as stream:stream.write(encoded)
    print(json.dumps(record),flush=True);return record


def main():
    a=arguments();record=run(a.rows,a.baseline,a.product,a.policy,a.output,a.historical_reproduction,a.short_policy,a.corpus_manifest)
    if not record['passed']:raise SystemExit(1)


if __name__=='__main__':main()
