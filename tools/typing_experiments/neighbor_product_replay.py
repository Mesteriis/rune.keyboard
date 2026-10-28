#!/usr/bin/env python3
"""Replay immutable native scores through final controller, next-word typing and original Undo."""
import argparse
import base64
import json
import os
from pathlib import Path
import neighbor_refinement as ref
n=ref.recovery
product=ref.product


def replay(corpus, export, scores, output, unavailable=False):
    if output.exists():raise ValueError('FRESH_OUTPUT_REQUIRED')
    receipt=json.loads((scores/'receipt.json').read_text())
    if receipt['scores']!=n.digest(scores/'scores.jsonl') or receipt['requests']!=n.digest(scores/'requests.jsonl') or receipt['exportReceipt']!=n.digest(export/'receipt.json'):
        raise ValueError('SCORE_DRIFT')
    rows=n.read(corpus/'holdout.jsonl');by_id={r['id']:r for r in rows}
    responses={r['id']:r for r in n.read(scores/'scores.jsonl')}
    deliveries=[]
    for request in n.read(scores/'requests.jsonl'):
        response=responses[request['id']];product.validate_response(request,response)
        request=dict(request,split=by_id[request['id']]['split'],language='ru')
        if unavailable:response=dict(id=request['id'],error='SCORING_FAILED')
        deliveries.append(product.delivery_for(request,response))
    output.mkdir(parents=True)
    java=Path(os.environ['JAVA_HOME'])/'bin/java'
    sources,jars,android=product.compile_inputs(java)
    jar,compile_command=product.compile_harness(output,java,sources,jars,android)
    replies=output/'deliveries.tsv';replies.write_text(''.join(product.delivery_tsv_line(r)+'\n' for r in deliveries))
    b64=lambda s:base64.b64encode(s.encode()).decode()
    inputs=output/'inputs.tsv'
    inputs.write_text(''.join(f"{i}\t{b64(r['id'])}\t{r['split']}\tru\t{b64(r['prefix'])}\t{b64(r['typed'])}\n" for i,r in enumerate(rows)))
    command=product.run_harness(output,java,jars,android,jar,inputs,output/'observations.jsonl','refinement-ready',replies)
    observed=n.read(output/'observations.jsonl')
    if len(observed)!=len(rows) or any(o['status']!='COMPLETE' or o['id']!=r['id'] for r,o in zip(rows,observed)):
        raise ValueError('PRODUCT_REPLAY_INCOMPLETE')
    n.write(output/'receipt.json',dict(schema=1,rows=n.digest(corpus/'holdout.jsonl'),scoreReceipt=n.digest(scores/'receipt.json'),
        observations=n.digest(output/'observations.jsonl'),jar=n.digest(jar),unavailable=unavailable,
        sources={str(p.relative_to(n.ROOT)):n.digest(p) for p in sources},
        assets={str(p.relative_to(n.ROOT)):n.digest(p) for p in [*product.asset_paths(),*product.compact_asset_paths()]},
        compileCommand=compile_command,command=command))
    print('PRODUCT_REPLAY_COMPLETE',len(observed),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for field in ('corpus','export','scores','output'):p.add_argument(field,type=Path)
    p.add_argument('--unavailable',action='store_true');args=p.parse_args()
    replay(args.corpus,args.export,args.scores,args.output,args.unavailable)
