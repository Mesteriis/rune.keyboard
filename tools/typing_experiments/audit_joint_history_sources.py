#!/usr/bin/env python3
"""Audit disclosed joint source rows; never grant fresh qualification."""
import collections,hashlib,json,unicodedata
from pathlib import Path
import pyarrow
import pyarrow.parquet as pq
import prepare_joint_correction as prepare
import joint_exclusion_inputs as exclusion
import joint_source_attestation as attest
from ranker import PymorphyLexicon


def main():
    root=Path(__file__).resolve().parents[2]; base=root/'build/joint-correction-20261025'; corp=base/'corpus'
    if pyarrow.__version__!='25.0.1':raise ValueError('HISTORICAL_PYARROW_VERSION')
    def sha(path):
     with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
    manifest_path=corp/'manifest.json'; expected='27c7084f8c739f608da77f617eca1c5ac552ff16b74da05a1a3c3cc888120e3f'
    if sha(manifest_path)!=expected:raise ValueError('HISTORICAL_MANIFEST_IDENTITY')
    manifest=json.loads(manifest_path.read_text()); files={manifest_path:expected}; rows={}; sources={}
    for name in ('tools/typing_experiments/audit_joint_history_sources.py','tools/typing_experiments/joint_source_attestation.py','tools/typing_experiments/joint_exclusion_inputs.py','tools/typing_experiments/prepare_joint_correction.py','tools/typing_experiments/prepare_external_spelling_holdout.py','tools/typing_experiments/neighbor_recovery.py','tools/typing_experiments/holdout_ledger.py','tools/typing_experiments/right_context_sentence_audit.py','tools/morphology/ranker.py','tools/eval/smart-typing-0.3/qualification-v2/generate_corpus.py','app/src/main/assets/smarttyping/lexicon/ru.morph'):
     path=root/name;files[path]=sha(path)
    for part in ('train','calibration','holdout'):
     path=corp/(part+'.jsonl');digest=sha(path)
     if digest!=manifest['files'][path.name]:raise ValueError('HISTORICAL_ROWS_IDENTITY')
     files[path]=digest
     rows[part]=[json.loads(s) for s in path.read_text().splitlines()]
    for name,digest in manifest['sourceBindings'].items():
     path=root/name
     if sha(path)!=digest:raise ValueError('HISTORICAL_SOURCE_IDENTITY')
     files[path]=digest;sources[path.name]=path
    words={r['word'] for part in rows.values() for r in part}; native=prepare.morphology(words); lex=PymorphyLexicon(cache_size=16384)
    by_source=collections.defaultdict(lambda:collections.defaultdict(list)); total=sum(map(len,rows.values()))
    for part,items in rows.items():
     for row in items:
      if row['split']!=part or row['source'] not in sources:raise ValueError('HISTORICAL_ROW_SCOPE')
      by_source[row['source']][row['article']].append(row)
    counts=collections.Counter(); sets={part:{axis:set() for axis in ('article','context','segment','family')} for part in rows}
    for source,groups in by_source.items():
     found=set()
     for batch in pq.ParquetFile(sources[source]).iter_batches(batch_size=128,columns=['id','text']):
      for ident,text in zip(batch.column(0).to_pylist(),batch.column(1).to_pylist(),strict=True):
       article=str(ident)
       if article not in groups:continue
       if article in found:raise ValueError('DUPLICATE_ARTICLE')
       found.add(article);text=unicodedata.normalize('NFC',text or '');index=exclusion.segment_index(text); matches=collections.defaultdict(list)
       for match in prepare.WORDS.finditer(text):
        word=match.group().casefold()
        if word in words:
         prefix=prepare.GENERATOR.bounded_prefix(text[max(0,match.start()-256):match.start()]).rstrip()
         matches[(word,prefix)].append(match)
       enriched=[]
       for row in groups[article]:
        options=matches.get((row['word'],row['prefix']),[])
        if not options:counts['missing_source']+=1;continue
        analyses=sorted({x.lemma for x in lex.analyses(row['word'])})
        if not analyses:counts['unresolved_dictionary']+=1;continue
        if len(options)>1:
         identities={(exclusion.source_context_hash(text,m,prepare.GENERATOR),exclusion.source_segment_hash_at(text,m,index)) for m in options}
         if len(identities)>1:
          for context,segment in identities:
           candidate=row|dict(families=analyses,contextHash=context,sourceSegmentHash=segment)
           attest.attest_article(article,source,text,[candidate],prepare.GENERATOR,lex,native,prepare.partition)
           group=sets[row['split']];group['article'].add(article);group['context'].add(context);group['segment'].add(segment);group['family'].update(analyses)
          counts['ambiguous_distinct_source']+=1;continue
        match=options[0];r=row|dict(families=analyses,contextHash=exclusion.source_context_hash(text,match,prepare.GENERATOR),sourceSegmentHash=exclusion.source_segment_hash_at(text,match,index));enriched.append(r)
       if enriched:
        try:counts['attested']+=attest.attest_article(article,source,text,enriched,prepare.GENERATOR,lex,native,prepare.partition)['checkedRows']
        except ValueError as exc:counts['rejected_'+str(exc)]+=len(enriched);continue
        for r in enriched:
         group=sets[r['split']];group['article'].add(article);group['context'].add(r['contextHash']);group['segment'].add(r['sourceSegmentHash']);group['family'].update(r['families'])
     for article in set(groups)-found:counts['missing_article']+=len(groups[article])
    if sum(counts.values())!=total:raise ValueError('HISTORICAL_ROW_ACCOUNTING')
    for path,digest in files.items():
     if sha(path)!=digest:raise ValueError('HISTORICAL_INPUT_DRIFT')
    parts=list(rows); overlaps={f'{a}-{b}':{axis:len(sets[a][axis]&sets[b][axis]) for axis in sets[a]} for i,a in enumerate(parts) for b in parts[i+1:]}
    result={'schema':1,'historicalDisclosed':True,'qualified':False,'rows':total,'counts':dict(counts),'overlaps':overlaps,'manifestSha256':expected,'sourceHashes':{str(p.relative_to(root)):v for p,v in files.items()},'dictionaryReceiptSha256':hashlib.sha256(json.dumps(lex.receipt(),sort_keys=True,separators=(',',':')).encode()).hexdigest()}
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':
    main()
