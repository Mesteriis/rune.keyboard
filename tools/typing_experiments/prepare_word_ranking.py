#!/usr/bin/env python3
"""Frozen public article splits with exact one/two/three-edit typo cohorts."""
from pathlib import Path
import argparse
import json
import re
import unicodedata
import prepare_refinement as public

ROOT=public.ROOT
SEED='rune-word-ranking-20260915-v1'
QUOTAS={'train':{1:2000,2:2000,3:1000,0:1000},'dev':{1:400,2:400,3:200,0:200},'test':{1:600,2:600,3:300,0:300}}
TEXT_CAPS={'train':250000,'dev':100000,'test':100000}
SKIP=2155

def partition(article):
    bucket=int(public.digest((SEED+':'+str(article)).encode())[:8],16)%10
    return 'train' if bucket<8 else 'dev' if bucket==8 else 'test'

def distance(a,b):
    """Optimal-string-alignment distance, including an adjacent transposition."""
    d=[[0]*(len(b)+1) for _ in range(len(a)+1)]
    for i in range(len(a)+1):d[i][0]=i
    for j in range(len(b)+1):d[0][j]=j
    for i in range(1,len(a)+1):
        for j in range(1,len(b)+1):
            d[i][j]=min(d[i-1][j]+1,d[i][j-1]+1,d[i-1][j-1]+int(a[i-1]!=b[j-1]))
            if i>1 and j>1 and a[i-1]==b[j-2] and a[i-2]==b[j-1]:d[i][j]=min(d[i][j],d[i-2][j-2]+1)
    return d[-1][-1]

def mutate(word,identity,count,vocabulary):
    if count==0:return word,[]
    if count not in (1,2,3):raise ValueError('EDIT_COUNT')
    for attempt in range(24):
        value=word;operations=[]
        for step in range(count):
            change=public.perturb(value,f'{identity}:{attempt}:{step}',vocabulary)
            if change is None:break
            value,operation=change;operations.append(operation)
        if len(operations)==count and value not in vocabulary and distance(word,value)==count:
            return value,operations
    return None

def prior_evidence():
    specs=[(ROOT/'build/typing-refinement/data/manifest.json',ROOT/'build/typing-refinement/verified-observations/manifest.json'),
           (ROOT/'build/typing-extra-epochs/data/manifest.json',ROOT/'build/typing-extra-epochs/observations/manifest.json')]
    articles=set();contexts=set();texts=set();hashes={}
    for path,binding_path in specs:
        binding=json.loads(binding_path.read_text())
        if public.file_hash(path)!=binding['dataManifestSha256']:raise ValueError('PRIOR_MANIFEST_IDENTITY')
        manifest=json.loads(path.read_text())
        if manifest.get('containsPersonalMessages') is not False:raise ValueError('PUBLIC_PRIOR_REQUIRED')
        if manifest['scannedArticles']>SKIP:raise ValueError('PRIOR_SCAN_CHANGED')
        hashes[str(path.relative_to(ROOT))]=public.file_hash(path)
        for part in ('train','dev','test'):
            articles.update(map(str,manifest['partitions'][part]['articles']))
            for kind in ('rows','text'):
                source=path.parent/f'{part}-{kind}.jsonl'
                if public.file_hash(source)!=manifest['files'][source.name]:raise ValueError('PRIOR_DATA_IDENTITY')
                for line in source.read_text().splitlines():
                    row=json.loads(line)
                    if kind=='rows':contexts.add(public.digest((row['prefix'].lower()+'\0'+row['expectedSpelling']).encode()))
                    else:texts.add(public.digest(row['text'].encode()))
    return articles,contexts,texts,hashes

def run(parquet,frequency,output):
    import pyarrow.parquet as pq
    lock=json.loads((ROOT/'tools/model/rune-text-0.2/source-lock.json').read_text())
    source=lock['wikipediaContext']['files']['ru-0007.parquet']
    if parquet.stat().st_size!=source['bytes'] or public.file_hash(parquet)!=source['sha256']:raise ValueError('PUBLIC_PARQUET_IDENTITY')
    if public.file_hash(frequency)!=lock['frequencyWords']['files']['ru_50k.txt']:raise ValueError('PUBLIC_FREQUENCY_IDENTITY')
    excluded,seen_contexts,prior_text,prior_hashes=prior_evidence()
    output=output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('FRESH_BUILD_OUTPUT_REQUIRED')
    output.mkdir(parents=True)
    vocab={unicodedata.normalize('NFC',s.rsplit(' ',1)[0]).lower() for s in frequency.read_text().splitlines()}
    rows={p:[] for p in QUOTAS};texts={p:[] for p in QUOTAS};articles={p:[] for p in QUOTAS}
    counts={p:{k:0 for k in QUOTAS[p]} for p in QUOTAS};chars={p:0 for p in QUOTAS}
    words={p:{} for p in QUOTAS};seen_text=set();scanned=0
    def complete(p):return counts[p]==QUOTAS[p] and chars[p]>=TEXT_CAPS[p]
    for batch in pq.ParquetFile(parquet).iter_batches(batch_size=128,columns=['id','text']):
        for article,text in zip(batch.column(0).to_pylist(),batch.column(1).to_pylist()):
            scanned+=1;article=str(article)
            if scanned<=SKIP or article in excluded:continue
            p=partition(article)
            if complete(p):continue
            normalized=unicodedata.normalize('NFC',text or '')
            clean=' '.join(public.WORD.findall(normalized.lower()));text_hash=public.digest(clean.encode())
            if text_hash in seen_text or text_hash in prior_text:continue
            seen_text.add(text_hash);articles[p].append(article)
            if chars[p]<TEXT_CAPS[p] and len(clean)>=80:
                fragment=clean[:min(12000,TEXT_CAPS[p]-chars[p])]
                if public.digest(fragment.encode()) not in prior_text:
                    texts[p].append({'articleId':article,'text':fragment});chars[p]+=len(fragment)
            selected=set();count=0
            for sentence in re.split(r'(?<=[.!?])\s+|\n+',normalized):
                for ordinal,match in enumerate(public.WORD.finditer(sentence)):
                    word=match.group()
                    if ordinal<3 or word!=word.lower() or not 5<=len(word)<=12 or word not in vocab:continue
                    if word in selected or words[p].get(word,0)>=4:continue
                    prefix=sentence[:match.start()][-128:].lstrip()
                    if not prefix or not prefix[-1].isspace():continue
                    identity=public.digest((prefix.lower()+'\0'+word).encode())
                    if identity in seen_contexts:continue
                    rid=public.digest((SEED+':'+article+':'+identity).encode())
                    errors=(1,1,2,2,3,0)[int(rid[:8],16)%6]
                    if counts[p][errors]>=QUOTAS[p][errors]:continue
                    mutation=mutate(word,rid,errors,vocab)
                    if mutation is None:continue
                    typed,operations=mutation
                    seen_contexts.add(identity);selected.add(word);count+=1;words[p][word]=words[p].get(word,0)+1;counts[p][errors]+=1
                    rows[p].append({'id':'wordrank-'+rid[:24],'articleId':article,'language':'ru','partition':p,
                        'split':{'train':'calibration','dev':'diagnostic','test':'holdout'}[p],'family':word,'template':'article-'+article,
                        'typed':typed,'prefix':prefix,'cohort':'correct' if errors==0 else 'typo','noAuto':errors==0,
                        'expectedSpelling':word,'category':f'edit-{errors}','errorCount':errors,'operations':operations})
                    if count>=12:break
                if count>=12:break
        if all(complete(p) for p in QUOTAS):break
        if scanned>=20000:break
    if not all(complete(p) for p in QUOTAS):raise ValueError('INSUFFICIENT_COHORTS: '+str(counts))
    for p in QUOTAS:
        if set(articles[p])&excluded:raise ValueError('ARTICLE_LEAKAGE')
        for kind,records in [('rows',rows[p]),('text',texts[p])]:
            (output/f'{p}-{kind}.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in records))
    (output/'all-rows.jsonl').write_bytes(b''.join((output/f'{p}-rows.jsonl').read_bytes() for p in QUOTAS))
    manifest={'schema':1,'seed':SEED,'containsPersonalMessages':False,'sourceSha256':source['sha256'],
        'frequencySha256':public.file_hash(frequency),'sourceRepository':lock['wikipediaContext']['repository'],
        'sourceRevision':lock['wikipediaContext']['parquetRevision'],'sourcePath':source['repositoryPath'],'license':lock['wikipediaContext']['licenses'],
        'excludedInitialArticles':SKIP,'excludedPriorArticles':len(excluded),'priorManifestSha256':prior_hashes,'scannedArticles':scanned,
        'preparationScriptSha256':public.file_hash(Path(__file__)),
        'partitions':{p:{'rows':len(rows[p]),'characters':chars[p],'articles':articles[p],'errorCounts':counts[p]} for p in QUOTAS},
        'files':{p.name:public.file_hash(p) for p in output.glob('*.jsonl')}}
    (output/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    print(json.dumps({p:{'rows':len(rows[p]),'characters':chars[p],'articles':len(articles[p]),'errorCounts':counts[p]} for p in QUOTAS}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--parquet',type=Path,required=True);p.add_argument('--frequency',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.parquet,a.frequency,a.output)
