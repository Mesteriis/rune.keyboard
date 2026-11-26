#!/usr/bin/env python3
"""Reserve a new public article test before additional-epoch model selection."""
from pathlib import Path
import argparse
import json
import re
import unicodedata
import prepare_refinement as public

ROOT=public.ROOT
ROWS=1500
CHARACTERS=250_000
SEED='rune-extra-epochs-20260915-v1'

def excluded_articles(manifest):
    if manifest.get('containsPersonalMessages') is not False:
        raise ValueError('PUBLIC_PRIOR_REQUIRED')
    return {str(article) for part in manifest['partitions'].values() for article in part['articles']}

def prepare(parquet_path,frequency_path,output):
    import pyarrow.parquet as pq
    lock=json.loads((ROOT/'tools/model/rune-text-0.2/source-lock.json').read_text())
    source=lock['wikipediaContext']['files']['ru-0007.parquet']
    if parquet_path.stat().st_size!=source['bytes'] or public.file_hash(parquet_path)!=source['sha256']:
        raise ValueError('PUBLIC_PARQUET_IDENTITY')
    if public.file_hash(frequency_path)!=lock['frequencyWords']['files']['ru_50k.txt']:
        raise ValueError('PUBLIC_FREQUENCY_IDENTITY')
    prior_path=ROOT/'build/typing-refinement/data/manifest.json'
    binding=json.loads((ROOT/'build/typing-refinement/verified-observations/manifest.json').read_text())
    if public.file_hash(prior_path)!=binding['dataManifestSha256']:
        raise ValueError('PRIOR_MANIFEST_IDENTITY')
    prior=json.loads(prior_path.read_text());excluded=excluded_articles(prior)
    if prior['scannedArticles']!=1920:raise ValueError('UNEXPECTED_PRIOR_SCAN')
    output=output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('FRESH_BUILD_OUTPUT_REQUIRED')
    output.mkdir(parents=True)
    # Exclude exact earlier text fragments and row contexts in addition to article IDs.
    prior_text=set();seen_contexts=set()
    for part in ('train','dev','test'):
        for kind in ('text','rows'):
            path=prior_path.parent/f'{part}-{kind}.jsonl'
            if public.file_hash(path)!=prior['files'][path.name]:raise ValueError('PRIOR_DATA_IDENTITY')
            for line in path.read_text().splitlines():
                record=json.loads(line)
                if kind=='text':prior_text.add(public.digest(record['text'].encode()))
                else:seen_contexts.add(public.digest((record['prefix'].lower()+'\0'+record['expectedSpelling']).encode()))
    vocab={unicodedata.normalize('NFC',line.rsplit(' ',1)[0]).lower() for line in frequency_path.read_text().splitlines()}
    rows=[];texts=[];articles=[];seen_text=set();word_counts={};chars=0;scanned=0
    for batch in pq.ParquetFile(parquet_path).iter_batches(batch_size=128,columns=['id','text']):
        for article,text in zip(batch.column(0).to_pylist(),batch.column(1).to_pylist()):
            scanned+=1;article=str(article)
            if scanned<=1920 or article in excluded:continue
            normalized=unicodedata.normalize('NFC',text or '')
            clean=' '.join(public.WORD.findall(normalized.lower()))
            identity=public.digest(clean.encode())
            if identity in seen_text or identity in prior_text:continue
            seen_text.add(identity);articles.append(article)
            if chars<CHARACTERS and len(clean)>=80:
                fragment=clean[:min(12000,CHARACTERS-chars)]
                if public.digest(fragment.encode()) not in prior_text:
                    texts.append({'articleId':article,'text':fragment});chars+=len(fragment)
            selected=set();count=0
            for sentence in re.split(r'(?<=[.!?])\s+|\n+',normalized):
                for ordinal,match in enumerate(public.WORD.finditer(sentence)):
                    word=match.group()
                    if ordinal<3 or word!=word.lower() or not 5<=len(word)<=12 or word not in vocab:continue
                    if word in selected or word_counts.get(word,0)>=4:continue
                    prefix=sentence[:match.start()][-128:].lstrip()
                    if not prefix or not prefix[-1].isspace():continue
                    context=public.digest((prefix.lower()+'\0'+word).encode())
                    if context in seen_contexts:continue
                    identity=public.digest((SEED+':'+article+':'+str(match.start())+':'+context).encode())
                    mutation=public.perturb(word,identity,vocab)
                    if mutation is None:continue
                    if len(rows)>=ROWS or count>=12:break
                    typed,category=mutation
                    seen_contexts.add(context);selected.add(word);count+=1;word_counts[word]=word_counts.get(word,0)+1
                    rows.append({'id':'extra-'+identity[:24],'articleId':article,'language':'ru','partition':'test',
                        'split':'holdout','family':word,'template':'article-'+article,'typed':typed,'prefix':prefix,
                        'cohort':'typo','noAuto':False,'expectedSpelling':word,'category':category})
                if len(rows)>=ROWS or count>=12:break
            if len(rows)==ROWS and chars==CHARACTERS:break
        if len(rows)==ROWS and chars==CHARACTERS:break
        if scanned>=20000:break
    if len(rows)!=ROWS or chars!=CHARACTERS:raise ValueError('INSUFFICIENT_FRESH_TEST')
    if set(articles)&excluded:raise ValueError('ARTICLE_LEAKAGE')
    for part in ('train','dev','test'):
        for kind,records in [('rows',rows),('text',texts)]:
            (output/f'{part}-{kind}.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in (records if part=='test' else [])))
    (output/'all-rows.jsonl').write_bytes((output/'test-rows.jsonl').read_bytes())
    manifest={'schema':1,'seed':SEED,'containsPersonalMessages':False,'sourceSha256':source['sha256'],
        'frequencySha256':public.file_hash(frequency_path),'sourceRepository':lock['wikipediaContext']['repository'],
        'sourceRevision':lock['wikipediaContext']['parquetRevision'],'sourcePath':source['repositoryPath'],
        'license':lock['wikipediaContext']['licenses'],'priorManifestSha256':public.file_hash(prior_path),
        'excludedInitialArticles':1920,'excludedPriorArticles':len(excluded),'scannedArticles':scanned,
        'preparationScriptSha256':public.file_hash(Path(__file__)),
        'partitions':{p:{'characters':chars if p=='test' else 0,'rows':len(rows) if p=='test' else 0,'articles':articles if p=='test' else []} for p in ('train','dev','test')},
        'files':{p.name:public.file_hash(p) for p in output.glob('*.jsonl')}}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'rows':len(rows),'characters':chars,'articles':len(articles),'scannedArticles':scanned,'excludedPriorArticles':len(excluded)}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--parquet',type=Path,required=True);p.add_argument('--frequency',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();prepare(a.parquet,a.frequency,a.output)
