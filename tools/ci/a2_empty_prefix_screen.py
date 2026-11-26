"""Measure pinned host scorer outcomes on disclosed empty-prefix controls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/ci'),str(ROOT/'tools/eval/smart-typing-0.3/pipeline')]
import final_product_replay as replay
import register_a2_empty_prefix as disclosure


def normalize(cases,lines):
    if len(lines)!=len(cases):raise ValueError('A2_EMPTY_RESPONSE_COUNT')
    result=[]
    for case,line in zip(cases,lines,strict=True):
        item=json.loads(line)
        replay.validate_response({'id':case['id'], 'candidateIds':list(range(len(case['candidates'])))}, item)
        if 'error' not in item:
            item={k:v for k,v in item.items() if k!='durationMillis'}
        result.append(item)
    return result


def run(output):
    output=Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('A2_EMPTY_OUTPUT')
    if any(os.environ.get(name) for name in ('JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS')):raise ValueError('A2_EMPTY_ENVIRONMENT')
    disclosure.check();cases_raw=(disclosure.DATA/'cases.json').read_bytes();cases=json.loads(cases_raw)
    if replay.sha256(replay.MODEL)!=replay.MODEL_SHA256 or replay.sha256(replay.RUNNER)!=replay.RUNNER_SHA256:
        raise ValueError('A2_EMPTY_MODEL_IDENTITY')
    paths=(Path(__file__).resolve(),Path(disclosure.__file__).resolve(),disclosure.DATA/'cases.json',disclosure.DATA/'NOTICE.md',
           disclosure.CONTROL,disclosure.LEXICAL,Path(replay.__file__).resolve())
    before={str(p.relative_to(ROOT)):replay.sha256(p) for p in paths}
    requests=[{k:case[k] for k in ('id','prefix','candidates')} for case in cases]
    payload=''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for r in requests)
    output.mkdir(parents=True,mode=0o700);results=[]
    for index in (1,2):
        with (output/f'run-{index}.log').open('w') as log:
            result=subprocess.run([str(replay.RUNNER),str(replay.MODEL)],input=payload,text=True,stdout=subprocess.PIPE,
                                  stderr=log,timeout=120,check=True)
        rows=normalize(cases,result.stdout.splitlines());results.append(rows)
    if results[0]!=results[1]:raise ValueError('A2_EMPTY_NONDETERMINISTIC')
    if before!={str(p.relative_to(ROOT)):replay.sha256(p) for p in paths} or replay.sha256(replay.MODEL)!=replay.MODEL_SHA256 or replay.sha256(replay.RUNNER)!=replay.RUNNER_SHA256:
        raise ValueError('A2_EMPTY_DRIFT')
    disclosure.check();answers=results[0]
    summary={case['id']:answer.get('error','SCORED') for case,answer in zip(cases,answers,strict=True)}
    raw=(''.join(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n' for row in answers)).encode()
    (output/'scores.jsonl').write_bytes(raw)
    receipt=dict(scope='disclosed-synthetic-host-scorer-diagnostic',independentQualification=False,
        outcomes=summary,modelSha256=replay.MODEL_SHA256,runnerSha256=replay.RUNNER_SHA256,
        inputSha256=before,scoresSha256=hashlib.sha256(raw).hexdigest(),deterministic=True)
    (output/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps(summary,sort_keys=True))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args();run(args.output)
