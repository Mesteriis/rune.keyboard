"""Screen disclosed reviewed Russian controls as complete controller sessions."""
import argparse
import base64
import bz2
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/typing_experiments'),str(ROOT/'tools/eval/smart-typing-0.3/pipeline')]
import chat_corpus as corpus
import final_product_replay as harness
from holdout_ledger import keys_for,load_ledger
from import_tatoeba_history import CC0_LOCK_SHA

SOURCE=ROOT/'tools/typing_experiments/public_sources/tatoeba-ru-cc0-20261024/rus_sentences_CC0.tsv.bz2'
LOCK=SOURCE.with_name('tatoeba-source-lock.json')
REVIEW=ROOT/'tools/typing_experiments/chat_regression/source-control-review-v1.json'
LEDGER=ROOT/'tools/typing_experiments/holdout-ledger.json'


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def inputs():
    if digest(LOCK)!=CC0_LOCK_SHA:raise ValueError('PHRASE_REVIEW_LOCK')
    lock=json.loads(LOCK.read_text());review=json.loads(REVIEW.read_text())
    if lock.get('url')!=corpus.URL or lock.get('license')!='CC0-1.0' or digest(SOURCE)!=lock.get('compressedSha256'):
        raise ValueError('PHRASE_REVIEW_SOURCE')
    cases=review['cases'];ids={c['id'] for c in cases}
    if len(cases)!=11 or len(ids)!=11 or any(c['label'] not in ('preserve','possible_source_typo') for c in cases):
        raise ValueError('PHRASE_REVIEW_SCOPE')
    articles={c['id'].removeprefix('chat-regression-').removesuffix('-control') for c in cases}
    ledger=load_ledger(LEDGER);blocked={k for e in ledger['entries'] for k in e['keys'].get('article',[])}
    lines=[]
    with bz2.open(SOURCE,'rt',encoding='utf-8') as stream:
        for line in stream:
            if line.split('\t',1)[0] in articles:lines.append(line)
    generated,_=corpus.generate(lines,blocked)
    selected={r['id']:r for r in generated if r['id'] in ids}
    if set(selected)!=ids:raise ValueError('PHRASE_REVIEW_SOURCE_COVERAGE')
    rows=[]
    for case in cases:
        row=selected[case['id']]
        if row['typed']!=case['typed'] or row['cohort']!='correct':raise ValueError('PHRASE_REVIEW_LABEL_BINDING')
        rows.append((case,row['prefix']+' '+row['typed']))
    return rows


def evaluate(cases,rows):
    if len(cases)!=len(rows):raise ValueError('PHRASE_REVIEW_COUNT')
    counts={'rows':len(rows),'preserveRows':0,'preserved':0,'changedLastWord':0,'prefixChanges':0,
            'caseOnlyChanges':0,'undoChecked':0,'undoFailures':0,'possibleSourceTypos':0}
    for (case,phrase),row in zip(cases,rows,strict=True):
        stages=row.get('phraseStages');words=phrase.split(' ')
        if row.get('status')!='COMPLETE' or row.get('id')!=case['id'] or row.get('typed')!=phrase or not isinstance(stages,list) or len(stages)!=len(words):
            raise ValueError('PHRASE_REVIEW_OBSERVATION')
        for i,(word,stage) in enumerate(zip(words,stages,strict=True)):
            if stage.get('wordIndex')!=i or stage.get('typed')!=word:raise ValueError('PHRASE_REVIEW_STAGE')
            before,after=stage.get('before'),stage.get('after')
            if not isinstance(before,str) or not isinstance(after,str) or not before.endswith(word):raise ValueError('PHRASE_REVIEW_TEXT')
            if (i==0 and before!=word) or (i and before!=stages[i-1]['after']+word):raise ValueError('PHRASE_REVIEW_SESSION')
            changed=after!=before+' ';prefix=not after.startswith(before[:-len(word)])
            case_only=changed and after.casefold()==(before+' ').casefold()
            if (stage.get('changed'),stage.get('prefixChanged'),stage.get('caseOnly'))!=(changed,prefix,case_only):raise ValueError('PHRASE_REVIEW_FLAGS')
            counts['prefixChanges']+=prefix;counts['caseOnlyChanges']+=case_only
        final=stages[-1];final_word=final['after'].rstrip().split(' ')[-1]
        counts['changedLastWord']+=final_word!=case['typed']
        if case['label']=='preserve':counts['preserveRows']+=1;counts['preserved']+=final_word==case['typed']
        else:counts['possibleSourceTypos']+=1
        if final.get('automaticEdit') is True:
            counts['undoChecked']+=1
            counts['undoFailures']+=final.get('undoResult')!='HANDLED' or final.get('undoExact') is not True
    if counts['undoFailures']:raise ValueError('PHRASE_REVIEW_UNDO')
    return counts


def ensure_disclosed(rows, registered):
    import control_ledger as control
    allowed_controls={control.key_for(row,'regression') for row in registered}
    allowed_contexts=keys_for(registered,'context')
    for row in rows:
        for stage in row['phraseStages']:
            before=stage['before']; word=stage['typed']; after=stage['after']
            if not after.endswith(' '):raise ValueError('PHRASE_REVIEW_BOUNDARY')
            actual=after[:-1].split(' ')
            if not actual or not actual[-1]:raise ValueError('PHRASE_REVIEW_BOUNDARY')
            variants=((before[:-len(word)].strip(),word),(' '.join(actual[:-1]),actual[-1]))
            for prefix,target in variants:
                candidate=dict(language='ru',prefix=prefix,typed=target,expectedSpelling=target)
                if (control.key_for(candidate,'regression') not in allowed_controls or
                        not keys_for([candidate],'context') <= allowed_contexts):
                    raise ValueError('PHRASE_REVIEW_UNDISCLOSED_CONTEXT')


def run(java,output):
    java=Path(java).resolve(strict=True);output=Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('PHRASE_REVIEW_OUTPUT')
    from register_review_phrase import CONTROL, check, rows as disclosed_rows
    check()
    sources,jars,android=harness.compile_inputs(java)
    assets=sorted(p for p in (harness.ASSETS/'smarttyping').rglob('*') if p.is_file())
    files=[*sources,*jars,android,java,java.parent.parent/'release',*assets,SOURCE,LOCK,REVIEW,LEDGER,CONTROL,
           Path(corpus.__file__),ROOT/'tools/typing_experiments/holdout_ledger.py',
           ROOT/'tools/typing_experiments/source_identities.py',ROOT/'tools/typing_experiments/import_tatoeba_history.py',
           ROOT/'tools/ci/register_review_phrase.py',Path(harness.__file__),Path(__file__)]
    keys=[str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else f'external/{i}-{p.name}' for i,p in enumerate(files)]
    before={k:digest(p) for k,p in zip(keys,files,strict=True)}
    check()
    cases=inputs();output.mkdir(parents=True)
    jar,_=harness.compile_harness(output,java,sources,jars,android)
    enc=lambda value:base64.b64encode(value.encode()).decode('ascii')
    input_path=output/'input.tsv';input_path.write_text(''.join('\t'.join((str(i),enc(case['id']),'holdout','ru',enc(''),enc(phrase)))+'\n' for i,(case,phrase) in enumerate(cases)))
    cp=os.pathsep.join(map(str,[jar,jars[1],jars[2],android]))
    command=[str(java),'-XX:ActiveProcessorCount=2','-Xmx768m','-Drune.replay.phrase=true','-Drune.replay.phraseUndo=true','-cp',cp,
        'io.github.mesteriis.rune.keyboard.smarttyping.session.FinalProductSpellingReplay',str(input_path),str(harness.ASSETS),'current-product','all']
    outputs=[]
    for i in (1,2):
        with (output/f'run-{i}.jsonl').open('xb') as f,(output/f'run-{i}.log').open('xb') as log:
            subprocess.run(command,cwd=ROOT,stdout=f,stderr=log,check=True,timeout=1200)
        outputs.append((output/f'run-{i}.jsonl').read_bytes())
    if outputs[0]!=outputs[1]:raise ValueError('PHRASE_REVIEW_NONDETERMINISTIC')
    observations=[json.loads(line) for line in outputs[0].splitlines()]
    metrics=evaluate(cases,observations)
    ensure_disclosed(observations,disclosed_rows())
    if before!={k:digest(p) for k,p in zip(keys,files,strict=True)}:raise ValueError('PHRASE_REVIEW_INPUT_DRIFT')
    check()
    receipt=dict(scope='posthoc-disclosed-public-phrase-regression',independentQualification=False,
        externalModelCalls=0,metrics=metrics,inputSha256=before,resultSha256=hashlib.sha256(outputs[0]).hexdigest())
    (output/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps(metrics,sort_keys=True))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--java',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();run(args.java,args.output)
