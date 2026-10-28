#!/usr/bin/env python3
"""Compile and replay actual product correction; expected labels never enter the Kotlin process."""
import argparse
import base64
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
PIPELINE=ROOT/'tools/eval/smart-typing-0.3/pipeline'
sys.path.insert(0,str(PIPELINE))
import final_product_replay as replay


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rows',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--mode',choices=['joint-export','joint-ready','joint-production','joint-rescue-ready','joint-primary-only','word-context-ready','word-context-baseline','contextual-production','infinitive-revision-production','noun-case-production','current-product'],required=True)
    p.add_argument('--config',type=Path)
    p.add_argument('--java',type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();rows=a.rows.resolve();config=a.config.resolve() if a.config else None
    if out.exists() or not out.is_relative_to(ROOT/'build'):raise ValueError('FRESH_BUILD_OUTPUT')
    if (a.mode=='joint-ready')!=(config is not None):raise ValueError('CONFIG_MODE')
    records=replay.read_jsonl(rows)
    if len({r['id'] for r in records})!=len(records):raise ValueError('DUPLICATE_ID')
    for r in records:
        if r['split'] not in ('train','calibration','holdout') or r['language']!='ru':raise ValueError('ROW_SCOPE')
    sources,jars,android=replay.compile_inputs(a.java)
    bindings={str(path.relative_to(ROOT)):replay.sha256(path) for path in sources}
    out.mkdir(parents=True)
    enc=lambda value:base64.b64encode(value.encode()).decode('ascii')
    with (out/'inputs.tsv').open('x',encoding='ascii') as stream:
        for i,r in enumerate(records):
            stream.write('\t'.join([str(i),enc(r['id']),r['split'],r['language'],enc(r['prefix']),enc(r['typed'])])+'\n')
    receipt=dict(mode=a.mode,rowsSha256=replay.sha256(rows),configSha256=replay.sha256(config) if config else None,
        sources=bindings,runnerSha256=replay.sha256(Path(__file__)),status='STARTED')
    try:
        jar,compile_command=replay.compile_harness(out,a.java,sources,jars,android)
        receipt['compileCommand']=compile_command;receipt['jarSha256']=replay.sha256(jar)
        receipt['executeCommand']=replay.run_harness(out,a.java,jars,android,jar,out/'inputs.tsv',out/'observations.jsonl',a.mode,config)
        if any(replay.sha256(ROOT/key)!=value for key,value in bindings.items()):raise ValueError('SOURCE_DRIFT')
        if replay.sha256(rows)!=receipt['rowsSha256']:raise ValueError('ROWS_DRIFT')
        receipt.update(status='COMPLETE',exitCode=0,observationsSha256=replay.sha256(out/'observations.jsonl'))
    except subprocess.CalledProcessError as error:
        receipt.update(status='FAILED',exitCode=error.returncode);raise
    finally:
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')

if __name__=='__main__':main()
