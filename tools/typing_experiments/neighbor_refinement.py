#!/usr/bin/env python3
"""Freeze and qualify same-request model refinements over public, owned-word replays."""
from __future__ import annotations
import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time
import neighbor_recovery as recovery

ROOT=recovery.ROOT
spec=importlib.util.spec_from_file_location('product_replay',ROOT/'tools/eval/smart-typing-0.3/pipeline/final_product_replay.py')
product=importlib.util.module_from_spec(spec);spec.loader.exec_module(product)

def score(export,output,reuse=None):
    if output.exists():raise ValueError('FRESH_OUTPUT_REQUIRED')
    receipt=json.loads((export/'receipt.json').read_text())
    if receipt['observations']!=recovery.digest(export/'observations.jsonl'):raise ValueError('EXPORT_DRIFT')
    for section in ('sources','assets'):
        if any(recovery.digest(ROOT/p)!=sha for p,sha in receipt[section].items()):raise ValueError('BINDING_DRIFT')
    if recovery.digest(product.RUNNER)!=product.RUNNER_SHA256 or recovery.digest(product.MODEL)!=product.MODEL_SHA256:
        raise ValueError('SCORER_IDENTITY')
    requests=[dict(o['refinementRequest'],id=o['id']) for o in recovery.read(export/'observations.jsonl') if o.get('refinementRequest')]
    cached={}
    if reuse is not None:
        prior=json.loads((reuse/'receipt.json').read_text())
        if prior['runner']!=product.RUNNER_SHA256 or prior['model']!=product.MODEL_SHA256 or prior['scores']!=recovery.digest(reuse/'scores.jsonl') or prior['requests']!=recovery.digest(reuse/'requests.jsonl'):
            raise ValueError('CACHE_IDENTITY')
        old_requests={r['id']:r for r in recovery.read(reuse/'requests.jsonl')}
        for response in recovery.read(reuse/'scores.jsonl'):
            request=old_requests[response['id']]
            product.validate_response(request,response)
            key=json.dumps(product.runner_request(request),sort_keys=True,ensure_ascii=False)
            cached[key]=response
    reused=0
    output.mkdir(parents=True)
    recovery.jsonl(output/'requests.jsonl',requests)
    with (output/'stderr.log').open('wb') as stderr:
        process=subprocess.Popen([str(product.RUNNER),str(product.MODEL)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=stderr,bufsize=0)
        selector=selectors.DefaultSelector();selector.register(process.stdout,selectors.EVENT_READ)
        pending=bytearray(); completed=0; started=time.monotonic()
        try:
            with (output/'scores.jsonl').open('x') as stream:
                for request in requests:
                    key=json.dumps(product.runner_request(request),sort_keys=True,ensure_ascii=False)
                    if key in cached:
                        product.validate_response(request,cached[key])
                        stream.write(json.dumps(cached[key],sort_keys=True)+'\n');stream.flush()
                        completed+=1;reused+=1
                        continue
                    process.stdin.write(json.dumps(product.runner_request(request),ensure_ascii=False).encode()+b'\n');process.stdin.flush()
                    deadline=time.monotonic()+60
                    while b'\n' not in pending:
                        remaining=deadline-time.monotonic()
                        if remaining<=0 or not selector.select(remaining):raise TimeoutError('SCORER_TIMEOUT')
                        chunk=os.read(process.stdout.fileno(),65536)
                        if not chunk:raise ValueError('SCORER_CLOSED')
                        pending.extend(chunk)
                        if len(pending)>65536:raise ValueError('SCORER_RESPONSE_BOUND')
                    line,_,tail=pending.partition(b'\n');pending=bytearray(tail)
                    response=json.loads(line);product.validate_response(request,response)
                    stream.write(json.dumps(response,sort_keys=True)+'\n');stream.flush();completed+=1
                    if completed%100==0:print(f'SCORED:{completed}/{len(requests)}',flush=True)
            process.stdin.close(); process.wait(timeout=15)
        finally:
            selector.close()
            if process.poll() is None:process.terminate();process.wait(timeout=5)
            process.stdout.close()
        if process.returncode!=0 or completed!=len(requests):raise ValueError('INCOMPLETE_SCORING')
    recovery.write(output/'receipt.json',dict(exportReceipt=recovery.digest(export/'receipt.json'),
        requests=recovery.digest(output/'requests.jsonl'),scores=recovery.digest(output/'scores.jsonl'),
        runner=recovery.digest(product.RUNNER),model=recovery.digest(product.MODEL),count=completed,
        exitCode=process.returncode,reused=reused,reuseReceipt=recovery.digest(reuse/"receipt.json") if reuse else None,elapsedSeconds=time.monotonic()-started))

def records(corpus,part,export,scores):
    rows={r['id']:r for r in recovery.read(corpus/f'{part}.jsonl')}
    observations={o['id']:o for o in recovery.read(export/'observations.jsonl')}
    receipt=json.loads((scores/'receipt.json').read_text())
    if receipt['scores']!=recovery.digest(scores/'scores.jsonl') or receipt['exportReceipt']!=recovery.digest(export/'receipt.json'):
        raise ValueError('SCORE_DRIFT')
    responses=recovery.read(scores/'scores.jsonl'); result=[]
    if len(responses)!=receipt['count']:raise ValueError('SCORE_COUNT')
    for response in responses:
        row=rows[response['id']]; observed=observations[row['id']]; request=observed['refinementRequest']
        product.validate_response(dict(request,id=row['id']),response)
        if 'error' in response:continue
        values=[score['sumLogProbability']/score['scoredTokenCount'] for score in response['scores']]
        order=sorted(range(len(values)),key=lambda i:(-values[i],i)); best=order[0]
        word=request['continuations'][best]
        local=observed['afterBoundary']['text'].rstrip().split()[-1]
        if word==local or not observed['refinementAdmission'].get(word):continue
        result.append(dict(id=row['id'],family=row['family'],group=row['group'],topScore=values[best],
            margin=values[best]-values[order[1]],candidate=word,local=local,
            correct=word==row['expected'],control=row['noAuto'],
            improvement=local!=row['expected'] and word==row['expected'],
            regression=local==row['expected'] and word!=row['expected']))
    return result

def calibrate(corpus,export,scores,output):
    if output.exists():raise ValueError('FRESH_OUTPUT_REQUIRED')
    data=records(corpus,'calibration',export,scores)
    policy=recovery.calibrate(data)
    recovery.write(output,dict(schema=1,thresholds=policy,modelSha256=product.MODEL_SHA256,
        calibrationReceiptSha256=recovery.digest(scores/'receipt.json'),records=data,
        frozenBeforeHoldout=True))
    print('REFINEMENT_CALIBRATED' if policy else 'REFINEMENT_CALIBRATION_REFUSED',flush=True)

def evaluate(corpus,export,scores,frozen,output):
    if output.exists():raise ValueError('FRESH_OUTPUT_REQUIRED')
    policy=json.loads(frozen.read_text()); thresholds=policy['thresholds']
    data=records(corpus,'holdout',export,scores)
    selected=[] if thresholds is None else [r for r in data if r['topScore']>=thresholds['minimumScore'] and r['margin']>=thresholds['minimumMargin']]
    improvements=sum(r['improvement'] for r in selected); regressions=sum(r['regression'] for r in selected)
    incorrect=sum(not r['correct'] for r in selected)
    passed=improvements>0 and regressions==0 and incorrect==0 and not any(r['control'] for r in selected)
    recovery.write(output,dict(schema=1,passed=passed,improvements=improvements,regressions=regressions,
        incorrectRefinements=incorrect,selected=selected,scoringReceiptSha256=recovery.digest(scores/'receipt.json'),
        frozenPolicySha256=recovery.digest(frozen)))
    print('REFINEMENT_PASS' if passed else 'REFINEMENT_REFUSED',flush=True)
    return passed

def main():
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    score_parser=sub.add_parser('score')
    for key in ['export','output']:score_parser.add_argument(key,type=Path)
    score_parser.add_argument('--reuse',type=Path)
    cal=sub.add_parser('calibrate')
    for key in ['corpus','export','scores','output']:cal.add_argument(key,type=Path)
    ev=sub.add_parser('evaluate')
    for key in ['corpus','export','scores','frozen','output']:ev.add_argument(key,type=Path)
    args=parser.parse_args()
    if args.command=='score':score(args.export,args.output,args.reuse)
    elif args.command=='calibrate':calibrate(args.corpus,args.export,args.scores,args.output)
    else:sys.exit(0 if evaluate(args.corpus,args.export,args.scores,args.frozen,args.output) else 2)

if __name__=='__main__':main()
