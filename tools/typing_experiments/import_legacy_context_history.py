"""Verify early contextual ranker corpora against pinned public Wikipedia text."""
import argparse
import copy
import json
from pathlib import Path
import re
import sys
import unicodedata

from holdout_ledger import keys_for,load_ledger,validate_ledger
from import_joint_history import SOURCES
from recover_legacy_families import sha
from recover_legacy_holdout import load_generator
from right_context_sentence_audit import _source_hash

ROOT=Path(__file__).resolve().parents[2]
PREFIX='public-legacy-context-'
ANCHOR='build/right-context-wikipedia-20261027/plan.json'
CORPORA={
 'word-context':('build/context-ranking-20261025/corpus','0a10608b993d3688c832f7af349294604d8cb7fd1114b2646c527ed9728b3034'),
 'word-context-extra':('build/context-ranking-20261025/corpus-extra','64edff6524629a7e26163ba672214e32ffab00909459afaa1a96b005c1027b67'),
 'context-feature':('build/context-feature-ranker-20261026/corpus','c6c6e5cb53646d9ae3e3f86145854472190d496ff8dba9c4dbc1fe2add301f2b'),
}


def captures(text,frames,generator):
    text=unicodedata.normalize('NFC',text or '');result={}
    for word,prefix in frames:
        hashes=set()
        # Original joint.WORDS excludes word characters, but permits hyphens.
        # Recovery preserves historical tokenization; it grants no new admission.
        for match in re.finditer(r'(?<![\w])'+re.escape(word)+r'(?![\w])',text,re.IGNORECASE):
            actual=generator.bounded_prefix(text[max(0,match.start()-256):match.start()]).rstrip()
            if actual==prefix:hashes.add(_source_hash(prefix,word,text[match.end():match.end()+128]))
        if not hashes:raise ValueError('LEGACY_CONTEXT_SOURCE_CAPTURE')
        result[(word,prefix)]=hashes
    return result


def entries_for(name,part,rows,windows,lexicon,bindings):
    if not rows or len({r['id'] for r in rows})!=len(rows):raise ValueError('LEGACY_CONTEXT_ROW_ID')
    families=set();unknown=[];projected=[]
    for row in rows:
        if row['language']!='ru' or row['split']!=part:raise ValueError('LEGACY_CONTEXT_ROW_SCOPE')
        targets={row['word']};expected=row['expectedSpelling']
        if row.get('group')=='protected':
            if row.get('cohort') not in ('protected','correct') or row.get('noAuto') is not True or expected!='@'+row['word'] or row['typed']!=expected:
                raise ValueError('LEGACY_CONTEXT_PROTECTED_CONSTRUCTION')
        else:targets.add(expected)
        for target in targets:
            analyses=lexicon.analyses(target)
            if not analyses:unknown.append(row['id'])
            else:families.update(keys_for([dict(families=sorted({a.lemma for a in analyses}))],'family'))
        for window in windows[(row['source'],row['article'],row['word'],row['prefix'])]:projected.append(row|dict(contextHash=window))
    keys={axis:sorted(keys_for(projected,axis)) for axis in ('article','sentence','context')}
    if not unknown:keys['family']=sorted(families)
    parent=PREFIX+name+'-'+part
    entries=[dict(id=parent,usage='historical-exclusion',rowCount=len(rows),keys=keys,missingAxes=['family'] if unknown else [],bindings=bindings,
        notes='Public RU original article captures verified. All matching projected windows retained. Native/ambiguous surface family IDs are not canonical lemmas.')]
    if unknown and families:entries.append(dict(id=parent+'-families',usage='historical-family-exclusion',keys={'family':sorted(families)},missingAxes=[],bindings=bindings,parentEntries=[parent]))
    return entries,dict(rows=len(rows),articles=len(keys['article']),sourceWindows=len(keys['sentence']),contexts=len(keys['context']),dictionaryFamilies=len(families),unresolvedRows=sorted(set(unknown)))


def build(root,base,lexicon,read_batches):
    root=Path(root);result=copy.deepcopy(validate_ledger(base))
    if any(e['id'].startswith(PREFIX) for e in result['entries']):raise ValueError('LEGACY_CONTEXT_ALREADY_IMPORTED')
    anchored=next(e for e in base['entries'] if e['id']=='public-natural-context-pool-right-context-wikipedia-20261027')
    if sha(root/ANCHOR)!=anchored['bindings'][ANCHOR]:raise ValueError('LEGACY_CONTEXT_ANCHOR')
    anchor=json.loads((root/ANCHOR).read_text());jobs=[];needed={};bindings={ANCHOR:sha(root/ANCHOR)}
    for name,(directory,digest) in CORPORA.items():
        manifest_path=directory+'/manifest.json'
        if sha(root/manifest_path)!=digest:raise ValueError('LEGACY_CONTEXT_MANIFEST')
        manifest=json.loads((root/manifest_path).read_text())
        for part in ('calibration','holdout'):
            path=directory+'/'+part+'.jsonl';expected=anchor['exclusionBindings'][path]
            declaration=manifest['files'][part+'.jsonl'] if 'files' in manifest else manifest['partitions'][part]['sha256']
            if sha(root/path)!=expected or declaration!=expected:raise ValueError('LEGACY_CONTEXT_ROWS')
            rows=[json.loads(line) for line in (root/path).read_text().splitlines()]
            count=manifest['counts'][part]['rows'] if 'counts' in manifest else manifest['partitions'][part]['rows']
            if len(rows)!=count:raise ValueError('LEGACY_CONTEXT_COUNT')
            for row in rows:
                source=next((p for p in SOURCES if Path(p).name==row['source']),None)
                if source is None:raise ValueError('LEGACY_CONTEXT_PUBLIC_SOURCE')
                needed.setdefault(source,{}).setdefault(row['article'],set()).add((row['word'],row['prefix']))
            local={ANCHOR:bindings[ANCHOR],manifest_path:digest,path:expected};bindings.update(local);jobs.append((name,part,rows,local))
    generator=load_generator('2cbcb2508ef66b32a60b5c7665ad96c66dc1c6477c9da4ad6dde0ea969806e65');windows={}
    for source,wanted in needed.items():
        if sha(root/source)!=SOURCES[source]:raise ValueError('LEGACY_CONTEXT_SOURCE_HASH')
        remaining=set(wanted)
        for articles,texts in read_batches(root/source):
            for article,text in zip(articles,texts,strict=True):
                article=str(article)
                if article not in remaining:continue
                for (word,prefix),hashes in captures(text,wanted[article],generator).items():windows[(Path(source).name,article,word,prefix)]=hashes
                remaining.remove(article)
        if remaining:raise ValueError('LEGACY_CONTEXT_ARTICLES_MISSING')
        bindings[source]=SOURCES[source]
    source_bindings={p:sha(root/p) for p in ('tools/typing_experiments/import_legacy_context_history.py','tools/morphology/ranker.py','tools/typing_experiments/right_context_sentence_audit.py')}
    counts={}
    for name,part,rows,local in jobs:
        sources={p:SOURCES[p] for p in needed if Path(p).name in {r['source'] for r in rows}}
        entries,counts[name+'/'+part]=entries_for(name,part,rows,windows,lexicon,local|sources|source_bindings);result['entries'].extend(entries)
    added={k for e in result['entries'] if e['id'].startswith(PREFIX) for k in e['keys'].get('article',[])}
    receipt=dict(purpose='LEGACY_PUBLIC_CONTEXT_EXCLUSIONS_NOT_QUALIFICATION',counts=counts,bindings=bindings,sourceBindings=source_bindings,
        dictionary=lexicon.receipt(),modelCalls=0,allSourceCapturesVerified=True,
        currentArticleOverlap={e['id']:len(added&set(e['keys'].get('article',[]))) for e in base['entries'] if e['id'].startswith('public-right-context-available-')})
    return validate_ledger(result),receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():parser.error('output already exists')
    sys.path.insert(0,str(ROOT/'tools/morphology'));from ranker import PymorphyLexicon
    import pyarrow.parquet as parquet
    def batches(path):
        for batch in parquet.ParquetFile(path).iter_batches(batch_size=128,columns=['id','text']):yield batch.column(0).to_pylist(),batch.column(1).to_pylist()
    ledger,receipt=build(ROOT,load_ledger(args.base),PymorphyLexicon(cache_size=16384),batches)
    args.output.mkdir(parents=True,exist_ok=False)
    for name,value in (('ledger.json',ledger),('receipt.json',receipt)):(args.output/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps(dict(rows=sum(c['rows'] for c in receipt['counts'].values()),unresolvedRows=sum(len(c['unresolvedRows']) for c in receipt['counts'].values()),currentArticleOverlap=receipt['currentArticleOverlap'])))


if __name__=='__main__':main()
