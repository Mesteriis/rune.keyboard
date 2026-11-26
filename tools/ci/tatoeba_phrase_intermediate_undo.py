"""Reproduce each disclosed phrase correction at its own boundary and test Undo."""
import argparse
import base64
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/ci'),str(ROOT/'tools/eval/smart-typing-0.3/pipeline')]
import final_product_replay as harness
import register_tatoeba_phrase_inputs as source
import tatoeba_phrase_replay as replay
from authored_phrase_replay import evaluate
import holdout_ledger as lexical


def targets(cases, rows):
    if len(cases)!=len(rows): raise ValueError('UNDO_TARGET_COUNT')
    chosen=[]
    for (name, phrase), row in zip(cases, rows, strict=True):
        if row.get('id')!=name or row.get('typed')!=phrase or row.get('status')!='COMPLETE':
            raise ValueError('UNDO_TARGET_IDENTITY')
        words=phrase.split(' ');stages=row.get('phraseStages')
        if not isinstance(stages,list) or len(stages)!=len(words):raise ValueError('UNDO_TARGET_STAGES')
        for index,stage in enumerate(stages):
            if stage.get('wordIndex')!=index or stage.get('typed')!=words[index]:raise ValueError('UNDO_TARGET_WORD')
            if stage.get('automaticEdit') is True:
                chosen.append(dict(id=f'{name}#{index}',typed=' '.join(words[:index+1]),
                    before=stage['before'],after=stage['after'],index=index))
    return chosen


def verify(target, row, phrase):
    if row.get('id')!=target['id'] or row.get('status')!='COMPLETE':raise ValueError('UNDO_REPLAY_IDENTITY')
    if phrase:
        stages=row.get('phraseStages')
        if not isinstance(stages,list) or len(stages)!=target['index']+1:raise ValueError('UNDO_REPLAY_STAGES')
        last=stages[-1]
        if (last.get('before')!=target['before'] or last.get('after')!=target['after'] or
                last.get('automaticEdit') is not True):raise ValueError('UNDO_REPLAY_DECISION')
        if last.get('undoResult')!='HANDLED' or last.get('undoExact') is not True:raise ValueError('UNDO_REPLAY_FAILED')
    else:
        if (row.get('beforeBoundary',{}).get('text')!=target['before'] or
                row.get('afterBoundary',{}).get('text')!=target['after']):raise ValueError('UNDO_REPLAY_DECISION')
        if row.get('backspaceResult')!='HANDLED' or row.get('restoredBeforeBoundaryExactly') is not True:
            raise ValueError('UNDO_REPLAY_FAILED')


def run(java, baseline, output):
    java=Path(java).resolve(strict=True);baseline=Path(baseline).resolve();output=Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build') or not baseline.is_relative_to(ROOT/'build'):
        raise ValueError('UNDO_OUTPUT_SCOPE')
    receipt=json.loads((baseline/'receipt.json').read_bytes());raw=(baseline/'run-1.jsonl').read_bytes()
    if (raw!=(baseline/'run-2.jsonl').read_bytes() or hashlib.sha256(raw).hexdigest()!=receipt.get('resultSha256') or
            receipt.get('scope')!='disclosed-tatoeba-full-session-diagnostic' or receipt.get('independentQualification') is not False):
        raise ValueError('UNDO_BASELINE')
    for name,digest in receipt['inputSha256'].items():
        if not isinstance(name,str) or Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('UNDO_BINDING_PATH')
        if not name.startswith('external/') and (not (ROOT/name).is_file() or replay.digest(ROOT/name)!=digest):
            raise ValueError('UNDO_BASELINE_DRIFT')
    ledger=lexical.load_ledger(source.LEXICAL); cases=source.cases(ledger)
    rows=[json.loads(line) for line in raw.splitlines()]
    if evaluate(cases,rows)!=receipt['metrics']:raise ValueError('UNDO_BASELINE_METRICS')
    selected=targets(cases,rows)
    sources,jars,android=harness.compile_inputs(java)
    assets=sorted(p for p in (harness.ASSETS/'smarttyping').rglob('*') if p.is_file())
    files=[*sources,*jars,android,java,java.parent.parent/'release',*assets,source.CONTROL,source.LEXICAL,
           Path(source.__file__).resolve(),Path(replay.__file__).resolve(),ROOT/'tools/ci/authored_phrase_replay.py',
           Path(__file__).resolve(),Path(harness.__file__).resolve(),harness.SOURCE_MANIFEST]
    keys=[str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else f'external/{i}-{p.name}' for i,p in enumerate(files)]
    if len(set(keys))!=len(keys):raise ValueError('UNDO_DUPLICATE_BINDING')
    bindings={k:replay.digest(p) for k,p in zip(keys,files,strict=True)}
    output.mkdir(parents=True,mode=0o700);jar,_=harness.compile_harness(output,java,sources,jars,android)
    cp=os.pathsep.join(map(str,[jar,jars[1],jars[2],android]));enc=lambda s:base64.b64encode(s.encode()).decode('ascii')
    counts=Counter();hashes={}
    for kind in ('single','phrase'):
        group=[v for v in selected if (v['index']>0)==(kind=='phrase')]
        if not group:continue
        inp=output/(kind+'.tsv')
        inp.write_text(''.join('\t'.join((str(i),enc(item['id']),'holdout','ru',enc(''),enc(item['typed'])))+'\n' for i,item in enumerate(group)))
        cmd=[str(java),'-XX:ActiveProcessorCount=2','-Xmx768m']
        if kind=='phrase':cmd+=['-Drune.replay.phrase=true','-Drune.replay.phraseUndo=true']
        cmd+=['-cp',cp,'io.github.mesteriis.rune.keyboard.smarttyping.session.FinalProductSpellingReplay',str(inp),str(harness.ASSETS),'current-product','all']
        with (output/(kind+'.jsonl')).open('xb') as out, (output/(kind+'.log')).open('xb') as log:
            subprocess.run(cmd,cwd=ROOT,stdout=out,stderr=log,check=True,timeout=1200)
        observed=[json.loads(line) for line in (output/(kind+'.jsonl')).read_bytes().splitlines()]
        if len(observed)!=len(group):raise ValueError('UNDO_REPLAY_COUNT')
        for target,row in zip(group,observed,strict=True):verify(target,row,kind=='phrase')
        counts[kind]=len(group);hashes[kind+'InputSha256']=replay.digest(inp)
    if bindings!={k:replay.digest(p) for k,p in zip(keys,files,strict=True)}:raise ValueError('UNDO_INPUT_DRIFT')
    result=dict(schema=1,scope='disclosed-phrase-boundary-undo-diagnostic',independentQualification=False,
                baselineResultSha256=receipt['resultSha256'],corrections=len(selected),singleWordChecks=counts['single'],
                multiwordChecks=counts['phrase'],exactUndo=len(selected),inputSha256=bindings,selectionHashes=hashes)
    (output/'receipt.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('corrections','singleWordChecks','multiwordChecks','exactUndo')},sort_keys=True))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--java',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.java,a.baseline,a.output)
