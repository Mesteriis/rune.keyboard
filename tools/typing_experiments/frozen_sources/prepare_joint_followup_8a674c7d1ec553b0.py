#!/usr/bin/env python3
"""Freeze fresh long-word calibration/holdout; exclude every previously selected lemma."""
import argparse
from collections import defaultdict, Counter
import hashlib
import json
from pathlib import Path
import unicodedata
import sys
import independent_corpus_guard as registry_guard
import joint_public_sources as public_sources
import joint_exclusion_inputs as exclusion_inputs
import prepare_joint_correction as joint
import prepare_external_spelling_holdout as common


def prepare(source_root, output, exclude_corpus=None, *, historical_reproduction=False):
    snapshot=registry_guard.begin(historical_reproduction)
    import pyarrow.parquet as parquet
    source_root, output = source_root.resolve(), output.resolve()
    if output.exists() or not output.is_relative_to(joint.ROOT/'build'): raise ValueError('FRESH_OUTPUT')
    prior=exclusion_inputs.capture(source_root/'corpus',('train.jsonl','calibration.jsonl','holdout.jsonl'))
    snapshots=[prior];excluded=set(prior['families']);excluded_articles=set(prior['articles'])
    if exclude_corpus is not None:
        extra=exclusion_inputs.capture(exclude_corpus,('calibration.jsonl','holdout.jsonl'))
        snapshots.append(extra);excluded.update(extra['families']);excluded_articles.update(extra['articles'])
    registered=[exclusion_inputs.verify_registered(item,snapshot['lexical']) for item in snapshots] if snapshot is not None else None
    public_origins=[exclusion_inputs.verify_public_origin(item) for item in snapshots] if snapshot is not None else None
    lock=json.loads((source_root/'followup-source-lock.json').read_text())
    public_sources.validate_lock(lock,('0020.parquet',))
    path=source_root/'0020.parquet';entry=next(e for e in lock['files'] if e['path']=='20231101.ru/train/'+path.name)
    if path.stat().st_size!=entry['size'] or common.sha256(path)!=entry['lfs']['oid']: raise ValueError('SOURCE_IDENTITY')
    frequency=joint.ROOT/'build/smart-typing-0.3/corpus-inputs/ru_50k.txt'
    if common.sha256(frequency)!=common.FREQUENCY_SHA256: raise ValueError('FREQUENCY_IDENTITY')
    known={s.split()[0] for s in frequency.read_text().splitlines() if 3<=len(s.split()[0])<=20}
    lemmas=joint.morphology(known)
    pools={p:defaultdict(list) for p in ['calibration','holdout']}
    for batch in parquet.ParquetFile(path).iter_batches(batch_size=128,columns=['id','text']):
        for article,text in zip(batch.column(0).to_pylist(),batch.column(1).to_pylist(),strict=True):
            if str(article) in excluded_articles:continue
            # Article assignment precedes token selection; no shared context across the two splits.
            part='calibration' if hashlib.sha256(('joint-followup:'+str(article)).encode()).digest()[0]<128 else 'holdout'
            text=unicodedata.normalize('NFC',text or '')
            for ordinal,m in enumerate(joint.WORDS.finditer(text)):
                word=m.group().casefold();family=lemmas.get(word)
                if ordinal<4 or len(word)<=4 or family is None or family in excluded or joint.partition(family)!=part: continue
                prefix=joint.GENERATOR.bounded_prefix(text[max(0,m.start()-256):m.start()]).rstrip()
                if not prefix: continue
                identity=hashlib.sha256((joint.SEED+str(article)+word+prefix).encode()).hexdigest()
                item=dict(word=word,family=family,prefix=prefix,article=str(article),source=path.name,selectionHash=identity)
                if snapshot is not None:
                    item['contextHash']=exclusion_inputs.source_context_hash(text,m,joint.GENERATOR)
                bucket=pools[part][family]
                if any(x['article']==str(article) for x in bucket):continue
                bucket.append(item);bucket.sort(key=lambda x:x['selectionHash']);del bucket[4:]
    manifest=dict(schema=1,stage='frozen-before-followup-calibration',sourceSha256=common.sha256(path),
        excludedFamilies=len(excluded),excludedArticles=len(excluded_articles),priorCorpusSha256=prior['manifestSha256'],
        additionalExclusionManifestSha256=extra['manifestSha256'] if exclude_corpus is not None else None,
        exclusionRegistryEntries=registered,exclusionPublicOrigins=public_origins,
        builderSha256=common.sha256(Path(__file__)),files={},counts={})
    selected={};articles={};selected_rows={}
    for part,pool in pools.items():
        rows=joint.rows_from_pool(pool,part,known)
        if len({r['family'] for r in rows})<400:raise ValueError('INSUFFICIENT_FAMILIES')
        selected[part]={r['family'] for r in rows}; articles[part]={r['article'] for r in rows}
        selected_rows[part]=rows
        manifest['counts'][part]=dict(rows=len(rows),families=len(selected[part]),groups=dict(Counter(r['group'] for r in rows)))
    if selected['calibration']&selected['holdout'] or articles['calibration']&articles['holdout']:raise ValueError('OVERLAP')
    check_rows=[row for rows in selected_rows.values() for row in rows]
    if snapshot is not None:
        sys.path.insert(0,str(joint.ROOT/'tools/morphology'))
        from ranker import PymorphyLexicon
        lexicon=PymorphyLexicon(cache_size=16384)
        check_rows=exclusion_inputs.canonical_registry_rows(selected_rows,lexicon)
        manifest['canonicalFamilyDictionary']=lexicon.receipt()
        manifest['canonicalFamilySources']={str(p.relative_to(joint.ROOT)):common.sha256(p) for p in (
            joint.ROOT/'tools/morphology/ranker.py',joint.ROOT/'tools/typing_experiments/joint_exclusion_inputs.py',
            joint.ROOT/'tools/typing_experiments/right_context_sentence_audit.py')}
    manifest.update(registry_guard.finish(snapshot,check_rows))
    for captured in snapshots:exclusion_inputs.verify(captured)
    output.mkdir(parents=True)
    for part,rows in selected_rows.items():
        target=output/f'{part}.jsonl';target.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
        manifest['files'][target.name]=common.sha256(target)
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(dict(counts=manifest['counts'],scope=manifest['scope'],independentQualification=False)),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--exclude-corpus',type=Path)
    p.add_argument('--historical-reproduction',action='store_true',help='Reproduce disclosed data without independent qualification.')
    a=p.parse_args();prepare(a.source_root,a.output,a.exclude_corpus,historical_reproduction=a.historical_reproduction)
