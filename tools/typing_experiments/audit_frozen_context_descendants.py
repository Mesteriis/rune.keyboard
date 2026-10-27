"""Audit historical natural/side variants and public captures without scoring.

Pinned preparation scripts are archived but never executed. Side selection is
not reproduced; capture/variant identity and v5 parent filtering are verified.
"""
import argparse
from collections import defaultdict
import copy
import json
from pathlib import Path
import sys

from audit_late_authored_history import archive_path
from holdout_ledger import keys_for,load_ledger,validate_ledger
from import_natural_context_history import verify_article,GENERATOR_SHA
from recover_legacy_holdout import load_generator,sha
from right_context_grammar_features import completed_following_words
from right_context_training_exclusion import exclude_training_contexts

ROOT=Path(__file__).resolve().parents[2]
PREFIX='public-frozen-context-descendant-'
SPECS={
  "natural-frozen": {
    "manifestSha256": "7ed0a1f09bf39a73659c66ba21243de92ea39bdf7bd49ac75f9e2aed759662aa",
    "planSha256": "a744b5afbb92fc655037fa6ace8890d4f40a10d7f37b02527c2b00c2c1141e89",
    "script": "freeze.py",
    "scriptSha256": "7d2b6254024680f4bee6fe91848ac7221242ef50ccfcd755481e5a18c02be3a0"
  },
  "side": {
    "manifestSha256": "67d6d51f20af739c27ee8526796ae3f7c6331a4ed990861a14b587a39a8685fd",
    "planSha256": "263e382b58e82a9a317d23d8ea30e4fdb7c0debfe1933eb1c41ff337e47369a9",
    "script": "prepare.py",
    "scriptSha256": "a108a87b00fca32165eedc11fcfbec1fa95da9665a21a156b6f440e83abb55e4"
  },
  "fresh-side-v4": {
    "manifestSha256": "62eb452779ca787bab3f5df2957fffefccf19f3ecd534395d5d0efebfcdfca47",
    "planSha256": "f47f1bd191b64c0cc62d8afa6056b0fff7e06e6ca15001cfb44fad2fa67d56ef",
    "script": "prepare.py",
    "scriptSha256": "e13b6201fcfa97dccdff17f22cf3891d44f850c79719f9ba79e85df02f7e354c"
  },
  "fresh-side-v5": {
    "manifestSha256": "e99d69c161e645479c557ef169facb55740572953258ae39325779ee2a6b2504",
    "planSha256": "1d27c2c87c7da4dfa30b231e3384ecb191da9231c34b32775b304e693093701f",
    "script": "prepare.py",
    "scriptSha256": "838fb68a8c4b90efbe0a68433afb6395b4b91fd311b8ea3fd4bc92ba0b369615"
  }
}


def folder(name):return 'build/right-context-'+name+'-20261027'


def verify_variants(rows,natural=False):
    if not rows or len({r['id'] for r in rows})!=len(rows):raise ValueError('DESCENDANT_ROW_IDS')
    groups=defaultdict(list)
    for row in rows:groups[row['contextHash']].append(row)
    captures=[]
    for variants in groups.values():
        first=variants[0]
        if first['group']!='typo' or not first['word'] or first['typed']==first['word']:
            raise ValueError('DESCENDANT_TYPO_PARENT')
        forms=[(first['typed'],'typo',False,False,first['rightContext'])]
        if not natural:
            completed=completed_following_words(first['rightContext'])
            if not completed:raise ValueError('DESCENDANT_UNFINISHED_PARENT')
            forms.append((first['typed'],'unfinished',False,True,' '+completed[0]))
        forms.extend([(first['word'],'correct',True,False,first['rightContext']),
            ('@'+first['word'],'protected',True,False,first['rightContext'])])
        if first.get('rival'):
            rival=(first['rival'],'correct_rival',True,False,first['rightContext'])
            if natural:forms.insert(-1,rival)
            else:forms.append(rival)
        if len(variants)!=len(forms):raise ValueError('DESCENDANT_VARIANT_COUNT')
        for actual,(typed,kind,control,retain,suffix) in zip(variants,forms,strict=True):
            expected=first|dict(id=actual['id'],typed=typed,group=kind,noAuto=control,
                rightContext=suffix,expectedSpelling=typed if control else first['word'])
            if natural:expected['cohort']='correct' if control else 'typo'
            else:expected['retainBaseline']=retain
            if actual!=expected:raise ValueError('DESCENDANT_VARIANT_IDENTITY')
        captures.append(first)
    return captures


def verify_filtered(parent,rows,families,audit):
    kept,actual=exclude_training_contexts(parent,families)
    if rows!=kept or audit!=actual:raise ValueError('DESCENDANT_FILTER_LINEAGE')
    return actual


def verify_pool_ancestry(captures,parents):
    indexed={(r['source'],r['selectionHash']):r for r in parents}
    if len(indexed)!=len(parents):raise ValueError('DESCENDANT_POOL_DUPLICATES')
    for row in captures:
        parent=indexed.get((row['source'],row['selectionHash']))
        if parent is None or any(row.get(k)!=v for k,v in parent.items()):
            raise ValueError('DESCENDANT_POOL_ANCESTRY')


def entries_for(name,part,rows,captures,lexicon,bindings):
    keys={axis:sorted(keys_for(rows,axis)) for axis in ('article','sentence','context')}
    families=set();unknown=[]
    for row in captures:
        for field in ('word','rival'):
            if not row.get(field):continue
            analyses=lexicon.analyses(row[field])
            if not analyses:unknown.append(dict(id=row['id'],field=field))
            else:families.update(keys_for([dict(families=sorted({a.lemma for a in analyses}))],'family'))
    if not unknown:keys['family']=sorted(families)
    entry=dict(id=PREFIX+name+'-'+part,usage='historical-exclusion',rowCount=len(rows),bindings=bindings,
        keys=keys,missingAxes=['family'] if unknown else [],
        notes='Public historical variants, not fresh qualification. Exact source captures verified. Family labels rebuilt from dictionary analyses of source word and rival, never guessed from corrupted or protected forms.')
    entries=[entry]
    if unknown and families:
        entries.append(dict(id=entry['id']+'-families',usage='historical-family-exclusion',bindings=bindings,
            keys={'family':sorted(families)},missingAxes=[],parentEntries=[entry['id']]))
    return entries,dict(rows=len(rows),contexts=len(captures),dictionaryFamilies=len(families),unresolved=unknown)


def build(root,base,lexicon,read_batches):
    root=Path(root);result=copy.deepcopy(validate_ledger(base));bindings={};datasets={};metadata={};captures={}
    if any(e['id'].startswith(PREFIX) for e in result['entries']):raise ValueError('DESCENDANTS_ALREADY_IMPORTED')
    archive=root/'tools/typing_experiments/frozen_sources'
    for name,spec in SPECS.items():
        directory=folder(name);manifest_path=directory+'/corpus/manifest.json';plan_path=directory+'/plan.json'
        if sha(root/manifest_path)!=spec['manifestSha256'] or sha(root/plan_path)!=spec['planSha256']:
            raise ValueError('DESCENDANT_MANIFEST_IDENTITY')
        manifest=json.loads((root/manifest_path).read_text());plan=json.loads((root/plan_path).read_text());metadata[name]=(manifest,plan)
        if manifest['planSha256']!=spec['planSha256']:raise ValueError('DESCENDANT_PLAN_BINDING')
        archived=archive_path(archive,directory+'/'+spec['script'],spec['scriptSha256'])
        bindings.update({manifest_path:sha(root/manifest_path),plan_path:sha(root/plan_path),str(archived.relative_to(root)):spec['scriptSha256']})
        if name!='fresh-side-v5' and manifest['preparerSha256']!=spec['scriptSha256']:raise ValueError('DESCENDANT_SCRIPT_BINDING')
        for filename,digest in manifest['files'].items():
            if filename not in ('calibration.jsonl','holdout.jsonl','calibration.tsv','holdout.tsv'):raise ValueError('DESCENDANT_FILE_PATH')
            path=directory+'/corpus/'+filename
            if sha(root/path)!=digest:raise ValueError('DESCENDANT_PAYLOAD_IDENTITY')
            bindings[path]=digest
        for part in ('calibration','holdout'):
            rows=[json.loads(line) for line in (root/directory/'corpus'/(part+'.jsonl')).read_text().splitlines()]
            if len(rows)!=manifest['counts'][part]['rows'] or any(r['split']!=part for r in rows):raise ValueError('DESCENDANT_SPLIT_COUNT')
            datasets[name,part]=rows;captures[name,part]=verify_variants(rows,natural=name=='natural-frozen')
    # v5 is an order-preserving whole-context filter of v4, not independent data.
    manifest,plan=metadata['fresh-side-v5'];training='build/right-context-training-v5-20261027/corpus/manifest.json'
    parent=next(e for e in base['entries'] if e['id']=='authored-right-context-late-history-v5-families')
    digest=sha(root/training)
    if (parent['bindings'].get(training)!=digest or manifest['trainingCorpusManifestSha256']!=digest
            or plan['trainingCorpusManifestSha256']!=digest
            or manifest['sourceManifestSha256']!=SPECS['fresh-side-v4']['manifestSha256']
            or plan['sourceManifestSha256']!=SPECS['fresh-side-v4']['manifestSha256']
            or plan['scriptSha256']!=SPECS['fresh-side-v5']['scriptSha256']):raise ValueError('DESCENDANT_PARENT_BINDING')
    families=json.loads((root/training).read_text())['families']
    if plan['excludedFamilies']!=families:raise ValueError('DESCENDANT_FILTER_FAMILIES')
    filter_source='tools/typing_experiments/right_context_training_exclusion.py'
    if sha(root/filter_source)!=plan['filterSourceSha256']:raise ValueError('DESCENDANT_FILTER_SOURCE')
    bindings[training]=digest;bindings[filter_source]=sha(root/filter_source)
    filtered={part:verify_filtered(datasets['fresh-side-v4',part],datasets['fresh-side-v5',part],families,
        manifest['exclusionAudits'][part]) for part in ('calibration','holdout')}
    natural_manifest,natural_plan=metadata['natural-frozen'];pool_rows=[]
    if natural_manifest['sourceContextBindings']!=natural_plan['sourceHashes']:
        raise ValueError('DESCENDANT_POOL_BINDING')
    for path,digest in natural_plan['sourceHashes'].items():
        parents=[e for e in base['entries'] if e['id'].startswith('public-natural-context-pool-') and e['bindings'].get(path)==digest]
        if len(parents)!=1 or sha(root/path)!=digest:raise ValueError('DESCENDANT_POOL_BINDING')
        bindings[path]=digest
        pool_rows.extend(json.loads(line) for line in (root/path).read_text().splitlines())
    for part in ('calibration','holdout'):verify_pool_ancestry(captures['natural-frozen',part],pool_rows)
    # Each capture must map to a pinned already-proven public source asset.
    public={p:h for e in base['entries'] if e['id'].startswith('public-natural-context-pool-') for p,h in e['bindings'].items() if p.endswith('.parquet')}
    if len(public)!=7:raise ValueError('DESCENDANT_PUBLIC_SOURCES')
    assets={e['id'].removeprefix('public-natural-context-pool-'):next(h for p,h in e['bindings'].items() if p.endswith('.parquet'))
        for e in base['entries'] if e['id'].startswith('public-natural-context-pool-')}
    if natural_manifest['sourceAssetHashes']!=assets:raise ValueError('DESCENDANT_SOURCE_BINDING')
    for name in ('side','fresh-side-v4'):
        if metadata[name][0]['sourceBindings']!=public or metadata[name][1]['sourceBindings']!=public:
            raise ValueError('DESCENDANT_SOURCE_BINDING')
    grouped=defaultdict(dict)
    for rows in captures.values():
        for row in rows:
            key=(row['article'],row['contextHash'])
            previous=grouped[row['source']].get(key)
            if previous and any(previous[f]!=row[f] for f in ('prefix','word','rightContext')):raise ValueError('DESCENDANT_SOURCE_DIVERGENCE')
            grouped[row['source']][key]=row
    generator=load_generator(GENERATOR_SHA)
    for path,digest in public.items():
        if sha(root/path)!=digest:raise ValueError('DESCENDANT_PUBLIC_IDENTITY')
        bindings[path]=digest;wanted=defaultdict(list)
        for row in grouped.pop(Path(path).name,{}).values():wanted[row['article']].append(row)
        remaining=set(wanted)
        for articles,texts in read_batches(root/path):
            for article,text in zip(articles,texts,strict=True):
                article=str(article)
                if article in remaining:verify_article(text,wanted[article],generator);remaining.remove(article)
        if remaining:raise ValueError('DESCENDANT_SOURCE_ARTICLE_MISSING')
    if grouped:raise ValueError('DESCENDANT_UNKNOWN_SOURCE')
    source_bindings={p:sha(root/p) for p in ('tools/typing_experiments/audit_frozen_context_descendants.py',
        'tools/typing_experiments/import_natural_context_history.py','tools/typing_experiments/right_context_grammar_features.py',
        'tools/typing_experiments/right_context_training_exclusion.py','tools/morphology/ranker.py')}
    bindings.update(source_bindings);counts={}
    for (name,part),rows in datasets.items():
        entries,counts[name+'-'+part]=entries_for(name,part,rows,captures[name,part],lexicon,dict(bindings));result['entries'].extend(entries)
    new=result['entries'][len(base['entries']):]
    for name in SPECS:
        partitions=[next(e for e in new if e['id']==PREFIX+name+'-'+part) for part in ('calibration','holdout')]
        if any(set(partitions[0]['keys'].get(axis,[]))&set(partitions[1]['keys'].get(axis,[])) for axis in ('article','sentence','context','family')):
            raise ValueError('DESCENDANT_PARTITION_OVERLAP')
    receipt=dict(purpose='HISTORICAL_PUBLIC_VARIANTS_AND_FILTER_LINEAGE_NOT_QUALIFICATION',counts=counts,
        bindings=bindings,sourceBindings=source_bindings,dictionary=lexicon.receipt(),filtered=filtered,
        modelCalls=0,preparationScriptsExecuted=False,selectionAlgorithmsReproduced=False,
        allPublicSourceCapturesVerified=True,naturalPoolAncestryVerified=True,globalCoverageComplete=False)
    return validate_ledger(result),receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():parser.error('fresh output required')
    sys.path.insert(0,str(ROOT/'tools/morphology'));from ranker import PymorphyLexicon
    import pyarrow.parquet as parquet
    def batches(path):
        for batch in parquet.ParquetFile(path).iter_batches(batch_size=128,columns=['id','text']):yield batch.column(0).to_pylist(),batch.column(1).to_pylist()
    ledger,receipt=build(ROOT,load_ledger(args.base),PymorphyLexicon(cache_size=16384),batches)
    args.output.mkdir(parents=True,exist_ok=False)
    for name,value in (('ledger.json',ledger),('receipt.json',receipt)):(args.output/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps(receipt['counts']))


if __name__=='__main__':main()
