#!/usr/bin/env python3
"""Measure disclosed exclusions in public selector text; never approve a corpus."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

import control_ledger
from holdout_ledger import _digest, keys_for, source_segment_hash, validate_ledger
from source_identities import unsupported_surface_key
from independent_corpus_guard import selector_segments

ROOT=Path(__file__).resolve().parents[2]
WORD=re.compile('[а-яё]+',re.IGNORECASE)
PARTS=('train','dev','test')


def audit(texts,rows,sources,lexicon,lexical,controls):
    validate_ledger(lexical);control_ledger.validate(controls)
    if set(texts)!=set(PARTS) or set(rows)!=set(PARTS):raise ValueError('TEXT_AUDIT_PARTITIONS')
    keys={p:{axis:set() for axis in ('article','controlArticle','segment','family','surface','unresolvedSurface','unsupported','context','controlContext','sourceContext','sourceControlContext')} for p in PARTS}
    words={};unresolved=set();partial=0;records=0;observed=set();text_only={};unmapped=0
    for part in PARTS:
        for row in texts[part]:
            if not isinstance(row,dict) or set(row)!={'articleId','text'}:raise ValueError('TEXT_AUDIT_RECORD')
            article=row['articleId'];fragment=row['text']
            if not isinstance(article,str) or article not in sources or not isinstance(fragment,str) or not fragment:
                raise ValueError('TEXT_AUDIT_SOURCE')
            text=unicodedata.normalize('NFC',sources[article] or '')
            clean=' '.join(WORD.findall(text.lower()))
            if not clean.startswith(fragment):raise ValueError('TEXT_AUDIT_SOURCE_MISMATCH')
            if len(fragment)<len(clean) and fragment[-1].isalpha() and clean[len(fragment)].isalpha():partial+=1
            records+=1;observed.add(article)
            keys[part]['article'].update(keys_for([{'article':article}],'article'))
            keys[part]['controlArticle'].add(control_ledger.article_key({'language':'ru','article':article}))
            keys[part]['segment'].add(_digest('sentence',['tatoeba-full-sentence-normalized-v1',source_segment_hash(fragment)]))
            # Conservative: quarantine every complete selector segment of the source article.
            for segment,_ in selector_segments(text):
                if segment.strip():keys[part]['segment'].add(_digest('sentence',['tatoeba-full-sentence-normalized-v1',source_segment_hash(segment)]))
            # Training sees the cleaned fragment, so measure its actual left
            # contexts separately from the original article's punctuation/case.
            # A truncated last word has no verified complete target.
            for match in WORD.finditer(fragment):
                if match.end()==len(fragment) and len(fragment)<len(clean) and clean[len(fragment)].isalpha():
                    continue
                word=match.group();prefix=fragment[max(0,match.start()-128):match.start()].lstrip()
                context={'language':'ru','prefix':prefix,'typed':word,'expectedSpelling':word}
                keys[part]['context'].update(keys_for([context],'context'))
                keys[part]['controlContext'].add(control_ledger.key_for(context,'regression'))
            # Map emitted token positions back to the original text only when
            # lowercasing preserves the exact word sequence. This avoids
            # guessing source offsets across Unicode case expansions.
            source_matches=list(WORD.finditer(text))
            source_words=[match.group().lower() for match in source_matches]
            if source_words!=WORD.findall(text.lower()):
                unmapped+=1
            else:
                segments=list(selector_segments(text));segment_index=0
                for ordinal,clean_match in enumerate(WORD.finditer(fragment)):
                    if clean_match.end()==len(fragment) and len(fragment)<len(clean) and clean[len(fragment)].isalpha():
                        continue
                    if ordinal>=len(source_matches) or source_words[ordinal]!=clean_match.group():
                        raise ValueError('TEXT_AUDIT_CONTEXT_SOURCE_MISMATCH')
                    match=source_matches[ordinal]
                    while segment_index+1<len(segments) and segments[segment_index+1][1]<=match.start():
                        segment_index+=1
                    segment,start=segments[segment_index]
                    relative=match.start()-start
                    if relative<0 or segment[relative:relative+len(match.group())]!=match.group():
                        raise ValueError('TEXT_AUDIT_CONTEXT_SOURCE_MISMATCH')
                    prefix=segment[max(0,relative-128):relative].lstrip()
                    context={'language':'ru','prefix':prefix,'typed':match.group(),'expectedSpelling':match.group()}
                    keys[part]['sourceContext'].update(keys_for([context],'context'))
                    keys[part]['sourceControlContext'].add(control_ledger.key_for(context,'regression'))
            for word in WORD.findall(fragment):
                word=word.casefold()
                if word not in words:words[word]=sorted({item.lemma for item in lexicon.analyses(word)})
                families=words[word]
                if not families:
                    unresolved.add(word)
                    keys[part]['unresolvedSurface'].add(control_ledger.surface_key('ru',word))
                else:keys[part]['family'].update(keys_for([{'families':families}],'family'))
                keys[part]['surface'].add(control_ledger.surface_key('ru',word))
                key=unsupported_surface_key(word)
                if key:keys[part]['unsupported'].add(key)
        text_only[part]={axis:set(values) for axis,values in keys[part].items()}
        for row in rows[part]:
            if row.get('partition')!=part:raise ValueError('TEXT_AUDIT_ROW_PARTITION')
            keys[part]['article'].update(keys_for([row],'article'))
            keys[part]['controlArticle'].add(control_ledger.article_key(row))
            keys[part]['segment'].update(keys_for([row],'sentence'))
            keys[part]['family'].update(keys_for([row],'family'))
    blocked={axis:{k for entry in lexical['entries'] for k in entry['keys'].get(axis,[])} for axis in ('article','sentence','family','context')}
    surfaces={k for entry in controls['entries'] for k in entry.get('surfaceKeys',[])}
    control_articles={k for entry in controls['entries'] for k in entry.get('articleKeys',[])}
    control_contexts={k for entry in controls['entries'] if entry['kind']=='regression' for k in entry['keys']}
    unsupported={k for entry in lexical['entries'] for k in entry.get('unsupportedSurfaceKeys',[])}
    allkeys={axis:set().union(*(keys[p][axis] for p in PARTS)) for axis in keys['train']}
    textkeys={axis:set().union(*(text_only[p][axis] for p in PARTS)) for axis in keys['train']}
    cross={axis:sum(len(keys[a][axis]&keys[b][axis]) for i,a in enumerate(PARTS) for b in PARTS[i+1:]) for axis in ('article','segment','family','surface','unresolvedSurface','context','sourceContext')}
    return dict(schema=1,scope='diagnostic-only-not-qualification',records=records,sourceArticles=len(observed),
                distinctWords=len(words),unresolvedSurfaces=len(unresolved),truncatedInsideWord=partial,unmappedSourceFragments=unmapped,
                lexicalOverlaps=dict(article=len(allkeys['article']&blocked['article']),
                    sentence=len(allkeys['segment']&blocked['sentence']),family=len(allkeys['family']&blocked['family']),
                    unsupportedSurface=len(allkeys['unsupported']&unsupported),context=len(allkeys['context']&blocked['context']),sourceContext=len(allkeys['sourceContext']&blocked['context'])),
                textLexicalOverlaps=dict(article=len(textkeys['article']&blocked['article']),
                    sentence=len(textkeys['segment']&blocked['sentence']),family=len(textkeys['family']&blocked['family']),
                    unsupportedSurface=len(textkeys['unsupported']&unsupported),context=len(textkeys['context']&blocked['context']),sourceContext=len(textkeys['sourceContext']&blocked['context'])),
                controlArticleOverlaps=len(allkeys['controlArticle']&control_articles),
                controlSurfaceOverlaps=len(allkeys['surface']&surfaces),controlContextOverlaps=len(allkeys['controlContext']&control_contexts),
                sourceControlContextOverlaps=len(allkeys['sourceControlContext']&control_contexts),crossPartitionOverlaps=cross,
                textControlArticleOverlaps=len(textkeys['controlArticle']&control_articles),
                textControlSurfaceOverlaps=len(textkeys['surface']&surfaces),
                textControlContextOverlaps=len(textkeys['controlContext']&control_contexts),
                textSourceControlContextOverlaps=len(textkeys['sourceControlContext']&control_contexts),
                registryCoverageComplete=False,contextCoverageComplete=False,qualified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',type=Path,required=True);p.add_argument('--parquet',type=Path,required=True)
    args=p.parse_args()
    import pyarrow.parquet as pq
    sys.path.insert(0,str(ROOT/'tools/morphology'))
    from ranker import PymorphyLexicon
    lock=json.loads((ROOT/'tools/model/rune-text-0.2/source-lock.json').read_text())['wikipediaContext']['files']['ru-0007.parquet']
    with args.parquet.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    if digest!=lock['sha256'] or args.parquet.stat().st_size!=lock['bytes']:raise ValueError('TEXT_AUDIT_PARQUET_IDENTITY')
    manifest_path=args.data/'manifest.json';manifest_raw=manifest_path.read_bytes();manifest=json.loads(manifest_raw)
    if manifest.get('containsPersonalMessages') is not False or manifest.get('sourceSha256')!=digest:
        raise ValueError('TEXT_AUDIT_MANIFEST')
    captured={}
    for part in PARTS:
        for kind in ('text','rows'):
            name=f'{part}-{kind}.jsonl';raw=(args.data/name).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=manifest.get('files',{}).get(name):raise ValueError('TEXT_AUDIT_INPUT_IDENTITY')
            captured[name]=raw
    texts={p:[json.loads(line) for line in captured[f'{p}-text.jsonl'].decode().splitlines()] for p in PARTS}
    rows={p:[json.loads(line) for line in captured[f'{p}-rows.jsonl'].decode().splitlines()] for p in PARTS}
    wanted={r['articleId'] for records in texts.values() for r in records};sources={}
    for batch in pq.ParquetFile(args.parquet).iter_batches(batch_size=128,columns=['id','text']):
        for article,text in zip(batch.column(0).to_pylist(),batch.column(1).to_pylist(),strict=True):
            article=str(article)
            if article in wanted:
                if article in sources:raise ValueError('TEXT_AUDIT_DUPLICATE_SOURCE')
                sources[article]=text
    if set(sources)!=wanted:raise ValueError('TEXT_AUDIT_MISSING_SOURCE')
    lexical_path=Path(__file__).with_name('holdout-ledger.json');control_path=Path(__file__).with_name('control-ledger.json')
    lexical_raw=lexical_path.read_bytes();control_raw=control_path.read_bytes()
    lexical=json.loads(lexical_raw);controls=json.loads(control_raw)
    dictionary=PymorphyLexicon(cache_size=16384)
    result=audit(texts,rows,sources,dictionary,lexical,controls)
    result['sourceSha256']=digest
    result['dictionary']=dictionary.receipt()
    result['inputSha256']={name:hashlib.sha256(raw).hexdigest() for name,raw in captured.items()}
    result['manifestSha256']=hashlib.sha256(manifest_raw).hexdigest()
    result['registrySha256']={'lexical':hashlib.sha256(lexical_raw).hexdigest(),'controls':hashlib.sha256(control_raw).hexdigest()}
    result['auditorSha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if (manifest_path.read_bytes()!=manifest_raw or lexical_path.read_bytes()!=lexical_raw or control_path.read_bytes()!=control_raw
            or any((args.data/name).read_bytes()!=raw for name,raw in captured.items())):
        raise ValueError('TEXT_AUDIT_INPUT_DRIFT')
    with args.parquet.open('rb') as stream:
        if hashlib.file_digest(stream,'sha256').hexdigest()!=digest:raise ValueError('TEXT_AUDIT_SOURCE_DRIFT')
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__':main()
