from pathlib import Path
import json,hashlib,collections,base64
root=Path('build/right-context-natural-frozen-20261027')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text())
original=load('build/right-context-focused-v2-20261027/plan.json');frozen=load('build/right-context-training-20261027/frozen-model.json')
assert sha('build/right-context-training-20261027/experimental-ranker.bin')==frozen['modelSha256']
roots=[Path('build/right-context-wikipedia-20261027')]+[Path('build/right-context-wiki'+n+'-20261027') for n in ['0012','0013','0014','0015','0016','0017']]
plan=dict(stage='frozen-before-independent-model-scoring',seed=original['seed'],contextsPerPart=original['contextsPerPart'],maximumContextsPerFamily=original['maximumContextsPerFamily'],minimumFamiliesPerPart=original['minimumFamiliesPerPart'],modelSha256=frozen['modelSha256'],sourceHashes={str(r/'contexts.unqualified.jsonl'):sha(r/'contexts.unqualified.jsonl') for r in roots},collectorHashes={str(r/'collect.py'):sha(r/'collect.py') for r in roots},sourceAssetHashes={},featureAndSelectorHashes={p:sha(p) for p in ['tools/typing_experiments/right_context_focus_forms.py','tools/typing_experiments/right_context_corpus_separation.py','tools/typing_experiments/right_context_grammar_features.py']},thresholdChanges=False,modelCalls=0)
with (root/'plan.json').open('x') as f:json.dump(plan,f,indent=2)
pools=collections.defaultdict(list);seen=set();articles=set();duplicates=0
for r in roots:
 report=load(r/'availability.json');assert sha(r/'contexts.unqualified.jsonl')==report['candidateContextsSha256'] and sha(r/'collect.py')==report['preparerSha256']
 collector=load(r/'plan.json');assert collector['modelSha256']==frozen['modelSha256']
 assert all(sha(p)==h for p,h in collector['exclusionBindings'].items())
 plan['sourceAssetHashes'][r.name]=report['sourceSha256']
 for line in (r/'contexts.unqualified.jsonl').read_text().splitlines():
  item=json.loads(line)
  assert item['article'] not in articles,'DUPLICATE_SOURCE_ARTICLE'
  articles.add(item['article'])
  if item['contextHash'] in seen:duplicates+=1;continue
  seen.add(item['contextHash']);pools[item['family']].append(item)
selected=collections.defaultdict(list)
for family,items in pools.items():
 assert family not in frozen['trainingFamilies']
 for item in sorted(items,key=lambda x:x['selectionHash'])[:plan['maximumContextsPerFamily']]:selected[item['provisionalSplit']].append(item)
selected={part:sorted(selected[part],key=lambda x:x['selectionHash'])[:plan['contextsPerPart']] for part in ['calibration','holdout']}
assert all(len(items)==plan['contextsPerPart'] and len({r['family'] for r in items})>=plan['minimumFamiliesPerPart'] for items in selected.values()),'ORIGINAL_NATURAL_GATE_NOT_MET'
assert not ({r['family'] for r in selected['calibration']}&{r['family'] for r in selected['holdout']})
assert not ({r['article'] for r in selected['calibration']}&{r['article'] for r in selected['holdout']})
assert not ({r['contextHash'] for r in selected['calibration']}&{r['contextHash'] for r in selected['holdout']})
out=root/'corpus';out.mkdir();counts={};files={}
for part,items in selected.items():
 rows=[]
 for item in items:
  for typed,kind,control in [(item['typed'],'typo',False),(item['word'],'correct',True),(item['rival'],'correct_rival',True),('@'+item['word'],'protected',True)]:
   rows.append(dict(item,id=f'right-natural-{part}-{len(rows):06d}',language='ru',split=part,typed=typed,expectedSpelling=typed if control else item['word'],noAuto=control,cohort='correct' if control else 'typo',group=kind,sourceSentenceUrl='https://ru.wikipedia.org/?curid='+item['article']))
  # The original source suffix is never sent to first-boundary candidate retrieval.
 path=out/(part+'.jsonl');path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows));files[path.name]=sha(path)
 enc=lambda x:base64.b64encode(x.encode()).decode()
 tsv=out/(part+'.tsv');tsv.write_text(''.join('\t'.join([str(i),enc(r['id']),part,'ru',enc(r['prefix']),enc(r['typed'])])+'\n' for i,r in enumerate(rows)));files[tsv.name]=sha(tsv)
 counts[part]=dict(rows=len(rows),contexts=len(items),families=len({r['family'] for r in items}),articles=len({r['article'] for r in items}),controls=sum(r['noAuto'] for r in rows),maxContextsInOneFamily=max(collections.Counter(r['family'] for r in items).values()))
manifest=dict(stage='frozen-before-independent-model-scoring',counts=counts,files=files,modelSha256=frozen['modelSha256'],planSha256=sha(root/'plan.json'),preparerSha256=sha(__file__),sourceAssetHashes=plan['sourceAssetHashes'],sourceContextBindings=plan['sourceHashes'],sourceLicense=['CC-BY-SA-3.0','GFDL-1.3'],excludedOriginalTrainingFamilies=frozen['trainingFamilies'],separation=dict(families=True,articles=True,normalizedContexts=True),duplicateContextsExcluded=duplicates,firstBoundaryQueryFields=['prefix','typed'],rightContextInRetrievalQuery=False,modelCalls=0,limitations=['Natural public article contexts with synthetic shared one-edit corruptions','Applied-word choice and ownership still require actual controller/device qualification','Not independent author separation or real human typing'])
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(counts),flush=True)
