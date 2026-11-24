#!/usr/bin/env python3
"""Compile actual product correction with opaque controller IDs and bound resources."""
import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
PIPELINE=ROOT/'tools/eval/smart-typing-0.3/pipeline'
old_path=sys.path[:]
try:
    sys.path.insert(0,str(PIPELINE))
    import final_product_replay as replay
finally:sys.path[:]=old_path

INPUT_FIELDS=('id','split','language','prefix','typed')


def controller_records(records):
    if not records or len({r['id'] for r in records})!=len(records):raise ValueError('DUPLICATE_OR_EMPTY_ID')
    output=[]
    for index,row in enumerate(records):
        if (any(not isinstance(row.get(key),str) for key in INPUT_FIELDS) or not row['id'] or
                row['split'] not in ('train','calibration','holdout') or row['language']!='ru'):
            raise ValueError('ROW_SCOPE')
        output.append(dict({key:row[key] for key in INPUT_FIELDS},id=f'joint-replay-{index:08d}'))
    return output


def restore_identities(records,controller,observations):
    if len(records)!=len(observations):raise ValueError('REPLAY_ROW_COUNT')
    result=[]
    for index,(row,expected,observed) in enumerate(zip(records,controller,observations,strict=True)):
        if (type(observed.get('index')) is not int or observed['index']!=index or
                observed.get('status')!='COMPLETE' or any(observed.get(key)!=expected[key] for key in INPUT_FIELDS)):
            raise ValueError('REPLAY_INPUT_IDENTITY')
        result.append(dict(observed,id=row['id']))
    return result


def run(rows,output,mode,java,config=None):
    out=Path(output).resolve();rows=Path(rows).resolve(strict=True)
    config=Path(config).resolve(strict=True) if config is not None else None;java=Path(java).resolve(strict=True)
    if out.exists() or not out.is_relative_to(ROOT/'build'):raise ValueError('FRESH_BUILD_OUTPUT')
    if (mode=='joint-ready')!=(config is not None):raise ValueError('CONFIG_MODE')
    if any(os.environ.get(k) for k in ('JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS')):
        raise ValueError('UNDECLARED_JAVA_OPTIONS')
    records=replay.read_jsonl(rows);controller=controller_records(records)
    sources,jars,android=replay.compile_inputs(java)
    config_model=[]
    if config is not None:
        fields=config.read_text().strip().split('\t');model=Path(fields[0]).resolve(strict=True)
        if len(fields)<2 or replay.sha256(model)!=fields[1]:raise ValueError('CONFIG_MODEL_IDENTITY')
        config_model=[model]
    assets=sorted(p for p in replay.ASSETS.rglob('*') if p.is_file())
    paths=list(dict.fromkeys([*sources,*assets,rows,*jars,android,java,Path(__file__),
        Path(replay.__file__),replay.SOURCE_MANIFEST,replay.TOOLCHAIN,*([config] if config else []),*config_model]))
    bindings={replay.path_key(path):replay.sha256(path) for path in paths}
    out.mkdir(parents=True,mode=0o700)
    enc=lambda value:base64.b64encode(value.encode()).decode('ascii')
    with (out/'inputs.tsv').open('x',encoding='ascii') as stream:
        for index,row in enumerate(controller):
            stream.write('\t'.join([str(index),enc(row['id']),row['split'],row['language'],enc(row['prefix']),enc(row['typed'])])+'\n')
    replay.write_jsonl(out/'input-identities.jsonl',[
        dict(index=i,id=c['id'],sourceId=r['id']) for i,(r,c) in enumerate(zip(records,controller,strict=True))])
    receipt=dict(schemaVersion=2,mode=mode,rowsSha256=replay.sha256(rows),
        configSha256=replay.sha256(config) if config else None,opaqueControllerIds=True,inputFieldsSent=list(INPUT_FIELDS),
        sources={str(p.relative_to(ROOT)):replay.sha256(p) for p in sources},files=bindings,
        runnerSha256=replay.sha256(Path(__file__)),status='STARTED',outputBindings={})
    try:
        jar,compile_command=replay.compile_harness(out,java,sources,jars,android)
        receipt['compileCommand']=compile_command;receipt['jarSha256']=replay.sha256(jar)
        receipt['executeCommand']=replay.run_harness(out,java,jars,android,jar,out/'inputs.tsv',out/'controller-observations.jsonl',mode,config)
        observed=restore_identities(records,controller,replay.read_jsonl(out/'controller-observations.jsonl'))
        replay.write_jsonl(out/'observations.jsonl',observed)
        replay.verify_bound_files({'files':bindings})
        receipt.update(status='COMPLETE',exitCode=0,observationsSha256=replay.sha256(out/'observations.jsonl'),
            outputBindings={p.name:replay.sha256(p) for p in out.iterdir() if p.is_file() and p.name!='receipt.json'})
    except Exception as error:
        receipt.update(status='FAILED',exitCode=error.returncode if isinstance(error,subprocess.CalledProcessError) else 1,
                       failureType=type(error).__name__);raise
    finally:(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rows',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--mode',choices=['joint-export','joint-ready','joint-production','joint-rescue-ready','joint-primary-only','word-context-ready','word-context-baseline','contextual-production','infinitive-revision-production','noun-case-production','current-product'],required=True)
    p.add_argument('--config',type=Path);p.add_argument('--java',type=Path,required=True)
    a=p.parse_args();run(a.rows,a.output,a.mode,a.java,a.config)

if __name__=='__main__':
    os.umask(0o077)
    main()
