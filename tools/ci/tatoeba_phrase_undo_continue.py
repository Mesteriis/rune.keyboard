"""Observe subsequent phrase typing after undoing a disclosed boundary edit."""
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
import control_ledger as control
import holdout_ledger as lexical


def select(cases,rows):
    if len(cases)!=len(rows):raise ValueError('CONTINUE_COUNT')
    result=[]
    for (name,phrase),row in zip(cases,rows,strict=True):
        words=phrase.split(' ');stages=row.get('phraseStages')
        if (row.get('id')!=name or row.get('typed')!=phrase or row.get('status')!='COMPLETE' or
                not isinstance(stages,list) or len(stages)!=len(words)):
            raise ValueError('CONTINUE_BASELINE')
        for index,stage in enumerate(stages):
            if (stage.get('wordIndex'),stage.get('typed'))!=(index,words[index]):raise ValueError('CONTINUE_WORD')
            if index<len(words)-1 and stage.get('automaticEdit') is True:
                result.append(dict(id=f'{name}#{index}',phrase=phrase,index=index,
                                   before=stage['before'],after=stage['after']))
    return result


def verify(target,row):
    words=target['phrase'].split(' ');stages=row.get('phraseStages');index=target['index']
    if (row.get('id')!=target['id'] or row.get('typed')!=target['phrase'] or row.get('status')!='COMPLETE' or
            not isinstance(stages,list) or len(stages)!=len(words)):raise ValueError('CONTINUE_IDENTITY')
    special=stages[index]
    if (special.get('before')!=target['before'] or special.get('after')!=target['after'] or
            special.get('automaticEdit') is not True):raise ValueError('CONTINUE_DECISION')
    if (special.get('undoResult')!='HANDLED' or special.get('undoExact') is not True or
            special.get('afterUndoBoundary')!=target['before']+' '):raise ValueError('CONTINUE_UNDO')
    previous=None;later=0;prefix_changes=0
    for i,(word,stage) in enumerate(zip(words,stages,strict=True)):
        if (stage.get('wordIndex'),stage.get('typed'))!=(i,word):raise ValueError('CONTINUE_WORD')
        before=stage.get('before');after=stage.get('after')
        if not isinstance(before,str) or not isinstance(after,str) or not before.endswith(word) or not after.endswith(' '):
            raise ValueError('CONTINUE_TEXT')
        if i==0 and before!=word or i and before!=previous+word:raise ValueError('CONTINUE_SESSION')
        changed=after!=before+' '; prefix=not after.startswith(before[:-len(word)])
        if stage.get('changed')!=changed or stage.get('prefixChanged')!=prefix:raise ValueError('CONTINUE_FLAGS')
        previous=stage.get('afterUndoBoundary') if i==index else after
        if i>index:later+=1;prefix_changes+=int(prefix)
    return later,prefix_changes


def run(java, baseline, output):
    java=Path(java).resolve(strict=True);baseline=Path(baseline).resolve();output=Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build') or not baseline.is_relative_to(ROOT/'build'):
        raise ValueError('CONTINUE_OUTPUT')
    receipt=json.loads((baseline/'receipt.json').read_bytes());raw=(baseline/'run-1.jsonl').read_bytes()
    if (raw!=(baseline/'run-2.jsonl').read_bytes() or hashlib.sha256(raw).hexdigest()!=receipt.get('resultSha256') or
            receipt.get('scope')!='disclosed-tatoeba-full-session-diagnostic' or receipt.get('independentQualification') is not False):
        raise ValueError('CONTINUE_BASELINE_RECEIPT')
    for name,digest in receipt['inputSha256'].items():
        if not isinstance(name,str) or Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('CONTINUE_BINDING_PATH')
        if not name.startswith('external/') and (not (ROOT/name).is_file() or replay.digest(ROOT/name)!=digest):raise ValueError('CONTINUE_INPUT_DRIFT')
    a=control.load(source.CONTROL);b=lexical.load_ledger(source.LEXICAL);cases=source.cases(b)
    rows=[json.loads(line) for line in raw.splitlines()]
    if evaluate(cases,rows)!=receipt['metrics']:raise ValueError('CONTINUE_METRICS')
    selected=select(cases,rows);sources,jars,android=harness.compile_inputs(java)
    assets=sorted(p for p in (harness.ASSETS/'smarttyping').rglob('*') if p.is_file())
    files=[*sources,*jars,android,java,java.parent.parent/'release',*assets,source.CONTROL,source.LEXICAL,
           Path(source.__file__).resolve(),Path(replay.__file__).resolve(),ROOT/'tools/ci/authored_phrase_replay.py',
           Path(__file__).resolve(),Path(harness.__file__).resolve(),harness.SOURCE_MANIFEST]
    names=[str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else f'external/{i}-{p.name}' for i,p in enumerate(files)]
    if len(set(names))!=len(names):raise ValueError('CONTINUE_DUPLICATE_BINDING')
    bindings={k:replay.digest(p) for k,p in zip(names,files,strict=True)}
    output.mkdir(parents=True,mode=0o700);jar,_=harness.compile_harness(output,java,sources,jars,android)
    cp=os.pathsep.join(map(str,[jar,jars[1],jars[2],android]));enc=lambda s:base64.b64encode(s.encode()).decode('ascii')
    known_c={k for entry in a['entries'] if entry['kind']=='regression' for k in entry['keys']}
    known_l={k for entry in b['entries'] for k in entry['keys'].get('context',[])}
    missing_c=set();missing_l=set();counts=Counter();hashes={}
    for index in sorted({item['index'] for item in selected}):
        group=[item for item in selected if item['index']==index];inp=output/f'index-{index}.tsv'
        inp.write_text(''.join('\t'.join((str(i),enc(x['id']),'holdout','ru',enc(''),enc(x['phrase'])))+'\n' for i,x in enumerate(group)))
        command=[str(java),'-XX:ActiveProcessorCount=2','-Xmx768m','-Drune.replay.phrase=true',f'-Drune.replay.phraseUndoAtIndex={index}',
                 '-cp',cp,'io.github.mesteriis.rune.keyboard.smarttyping.session.FinalProductSpellingReplay',str(inp),str(harness.ASSETS),'current-product','all']
        for n in (1,2):
            with (output/f'index-{index}-{n}.jsonl').open('xb') as out,(output/f'index-{index}-{n}.log').open('xb') as log:
                subprocess.run(command,cwd=ROOT,stdout=out,stderr=log,check=True,timeout=1200)
        one=(output/f'index-{index}-1.jsonl').read_bytes();two=(output/f'index-{index}-2.jsonl').read_bytes()
        if one!=two:raise ValueError('CONTINUE_NONDETERMINISTIC')
        observed=[json.loads(line) for line in one.splitlines()]
        if len(observed)!=len(group):raise ValueError('CONTINUE_RESULT_COUNT')
        for target,row in zip(group,observed,strict=True):
            later,prefix=verify(target,row);counts['cases']+=1;counts['subsequentWords']+=later;counts['laterPrefixChanges']+=prefix
            for stage in row['phraseStages']:
                before=stage['before'];word=stage['typed'];after=stage['after'];pieces=after[:-1].split(' ')
                for p,w in ((before[:-len(word)].strip(),word),(' '.join(pieces[:-1]),pieces[-1])):
                    data=dict(language='ru',prefix=p,typed=w,expectedSpelling=w)
                    k=control.key_for(data,'regression')
                    if k not in known_c:missing_c.add(k)
                    missing_l.update(lexical.keys_for([data],'context')-known_l)
        hashes[f'index-{index}-input']=replay.digest(inp);hashes[f'index-{index}-result']=hashlib.sha256(one).hexdigest()
    if bindings!={k:replay.digest(p) for k,p in zip(names,files,strict=True)}:raise ValueError('CONTINUE_INPUT_DRIFT')
    result=dict(schema=1,scope='disclosed-undo-continue-diagnostic',independentQualification=False,
        baselineResultSha256=receipt['resultSha256'],cases=counts['cases'],subsequentWords=counts['subsequentWords'],
        laterPrefixChanges=counts['laterPrefixChanges'],unregisteredControlKeys=sorted(missing_c),
        unregisteredContextKeys=sorted(missing_l),inputSha256=bindings,resultsSha256=hashes)
    (output/'receipt.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('cases','subsequentWords','laterPrefixChanges') }|{'unregisteredControlKeys':len(missing_c),'unregisteredContextKeys':len(missing_l)},sort_keys=True))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--java',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();run(args.java,args.baseline,args.output)
