"""Verify and preserve pinned public Wikipedia context pools, without scoring."""
import argparse
import copy
import json
from pathlib import Path
import re
import sys
import unicodedata

from holdout_ledger import keys_for,load_ledger,validate_ledger
from recover_legacy_families import sha
from recover_legacy_holdout import load_generator
from right_context_sentence_audit import _source_hash

ROOT=Path(__file__).resolve().parents[2]
PLAN='build/right-context-natural-frozen-20261027/plan.json'
PLAN_SHA='a744b5afbb92fc655037fa6ace8890d4f40a10d7f37b02527c2b00c2c1141e89'
PREFIX='public-natural-context-pool-'
GENERATOR_SHA='2cbcb2508ef66b32a60b5c7665ad96c66dc1c6477c9da4ad6dde0ea969806e65'


def verify_article(text,rows,generator):
    text=unicodedata.normalize('NFC',text or '');folded=text.lower()
    if len(text)!=len(folded):raise ValueError('CONTEXT_SOURCE_CASE_OFFSETS')
    for row in rows:
        found=False
        if _source_hash(row['prefix'],row['word'],row['rightContext'])!=row['contextHash']:
            raise ValueError('CONTEXT_WINDOW_IDENTITY')
        for match in re.finditer(r'(?<![\w-])'+re.escape(row['word'])+r'(?![\w-])',folded):
            prefix=generator.bounded_prefix(text[max(0,match.start()-256):match.start()]).rstrip(' \t')
            suffix=text[match.end():match.end()+128]
            if prefix==row['prefix'] and suffix==row['rightContext']:found=True;break
        if not found:raise ValueError('CONTEXT_SOURCE_CAPTURE')


def entries_for(name,rows,lexicon,bindings):
    if not rows or len({r['selectionHash'] for r in rows})!=len(rows):raise ValueError('CONTEXT_POOL_ROW_IDS')
    records=[r|dict(expectedSpelling=r['word']) for r in rows]
    keys={axis:sorted(keys_for(records,axis)) for axis in ('article','sentence','context')}
    families=set();unknown=[]
    for row in rows:
        for field in ('word','rival'):
            analyses=lexicon.analyses(row[field])
            if not analyses:unknown.append(dict(id=row['selectionHash'],field=field))
            else:families.update(keys_for([dict(families=sorted({a.lemma for a in analyses}))],'family'))
    missing=[] if not unknown else ['family']
    if not unknown:keys['family']=sorted(families)
    entry=dict(id=PREFIX+name,usage='historical-exclusion',rowCount=len(rows),bindings=bindings,keys=keys,missingAxes=missing,
        notes='Public RU source pool; both candidate analyses excluded when dictionary-supported. All source captures verified; no model scores read.')
    entries=[entry]
    if unknown and families:
        entries.append(dict(id=entry['id']+'-families',usage='historical-family-exclusion',bindings=bindings,
            keys={'family':sorted(families)},missingAxes=[],parentEntries=[entry['id']]))
    return entries,dict(rows=len(rows),articles=len(keys['article']),contexts=len(keys['context']),
                        dictionaryFamilies=len(families),unresolvedCandidateAnalyses=unknown)


def build(root,base,lexicon,read_batches):
    root=Path(root);result=copy.deepcopy(validate_ledger(base))
    if any(e['id'].startswith(PREFIX) for e in result['entries']):raise ValueError('CONTEXT_POOLS_ALREADY_IMPORTED')
    if sha(root/PLAN)!=PLAN_SHA:raise ValueError('CONTEXT_POOL_PLAN_IDENTITY')
    plan=json.loads((root/PLAN).read_text());generator=load_generator(GENERATOR_SHA)
    counts={};all_bindings={PLAN:PLAN_SHA};archive=root/'tools/typing_experiments/frozen_sources'
    archive_manifest=json.loads((archive/'manifest.json').read_text())['sources']
    for row_path,digest in plan['sourceHashes'].items():
        directory=Path(row_path).parent;name=directory.name;collector=str(directory/'collect.py');local_plan=directory/'plan.json'
        expected=plan['collectorHashes'][collector]
        if sha(root/row_path)!=digest or sha(root/collector)!=expected:raise ValueError('CONTEXT_POOL_FROZEN_INPUT')
        archived=archive/archive_manifest[expected]['file']
        if archive_manifest[expected]['originalPath']!=collector or sha(archived)!=expected:raise ValueError('CONTEXT_POOL_ARCHIVE')
        metadata=json.loads((root/local_plan).read_text())
        if name=='right-context-wikipedia-20261027':
            source='build/joint-correction-20261025/0020.parquet';lock='build/joint-correction-20261025/followup-source-lock.json'
            public=json.loads((root/lock).read_text())
            if public['repository']!='wikimedia/wikipedia' or public['revision']!='a634f78b1c435397c07001e175fa74cc4ad5e775':raise ValueError('CONTEXT_PUBLIC_REVISION')
            source_info=next(s for s in public['files'] if s['path']=='20231101.ru/train/0020.parquet')
            source_sha=source_info['lfs']['oid'];source_size=source_info['size']
        else:
            shard=int(name.removeprefix('right-context-wiki').split('-')[0]);source=f'build/typing-ranker-v2/ru-{shard:04d}.parquet'
            lock=f'build/typing-ranker-v2/external-holdout-v{shard-5}-ru{shard:04d}/manifest.json'
            public=json.loads((root/lock).read_text())['source']
            parent=next(e for e in base['entries'] if e['id']==f'public-spelling-v{shard-5}')
            if sha(root/lock)!=parent['bindings'][lock] or public['path']!=f'20231101.ru/train/{shard:04d}.parquet':raise ValueError('CONTEXT_SOURCE_LOCK')
            source_sha=public['sha256'];source_size=public['bytes']
        if metadata['sourceSha256']!=source_sha or sha(root/source)!=source_sha or (root/source).stat().st_size!=source_size or sha(root/lock)!=metadata['sourceLockSha256']:
            raise ValueError('CONTEXT_PUBLIC_SOURCE')
        rows=[json.loads(line) for line in (root/row_path).read_text().splitlines()];wanted={}
        for row in rows:
            if row['source']!=Path(source).name:raise ValueError('CONTEXT_ROW_SOURCE')
            wanted.setdefault(row['article'],[]).append(row)
        remaining=set(wanted)
        for articles,texts in read_batches(root/source):
            for article,text in zip(articles,texts,strict=True):
                article=str(article)
                if article in remaining:verify_article(text,wanted[article],generator);remaining.remove(article)
        if remaining:raise ValueError('CONTEXT_SOURCE_ARTICLES_MISSING')
        bindings={PLAN:PLAN_SHA,row_path:digest,collector:expected,str(archived.relative_to(root)):expected,
            str(local_plan):sha(root/local_plan),source:source_sha,lock:sha(root/lock)}
        entries,counts[name]=entries_for(name,rows,lexicon,bindings);result['entries'].extend(entries);all_bindings.update(bindings)
        print(json.dumps(dict(pool=name,verifiedRows=len(rows))),flush=True)
    new_articles={k for e in result['entries'] if e['id'].startswith(PREFIX) for k in e['keys'].get('article',[])}
    receipt=dict(purpose='PUBLIC_CONTEXT_POOL_EXCLUSIONS_NOT_QUALIFICATION',bindings=all_bindings,counts=counts,
        dictionary=lexicon.receipt(),modelCalls=0,allSourceCapturesVerified=True,
        currentArticleOverlap={e['id']:len(new_articles&set(e['keys'].get('article',[]))) for e in base['entries'] if e['id'].startswith('public-right-context-available-')},
        sourceBindings={p:sha(root/p) for p in ('tools/typing_experiments/import_natural_context_history.py','tools/morphology/ranker.py','tools/typing_experiments/right_context_sentence_audit.py')})
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
    print(json.dumps(dict(rows=sum(c['rows'] for c in receipt['counts'].values()),currentArticleOverlap=receipt['currentArticleOverlap'])))


if __name__=='__main__':main()
