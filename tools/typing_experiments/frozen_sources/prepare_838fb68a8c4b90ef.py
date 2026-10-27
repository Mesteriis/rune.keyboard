from pathlib import Path
import sys,json,hashlib,base64,collections
sys.path.insert(0,'tools/typing_experiments');from right_context_training_exclusion import exclude_training_contexts
root=Path('build/right-context-fresh-side-v5-20261027');source=Path('build/right-context-fresh-side-v4-20261027');train=Path('build/right-context-training-v5-20261027');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();load=lambda p:json.loads(Path(p).read_text())
manifest=load(source/'corpus/manifest.json');training=load(train/'corpus/manifest.json');families=training['families'];plan=load(source/'plan.json')
freeze=dict(stage='frozen-before-additional-training-family-exclusion',sourceManifestSha256=sha(source/'corpus/manifest.json'),trainingCorpusManifestSha256=sha(train/'corpus/manifest.json'),excludedFamilies=families,filterSourceSha256=sha('tools/typing_experiments/right_context_training_exclusion.py'),scriptSha256=sha(__file__),modelScoresUsed=False,requirements={k:plan[k] for k in ['minimumNegativeContextsPerPart','minimumPositiveSubjectContextsPerPart','minimumFamiliesPerPart']})
with (root/'plan.json').open('x') as f:json.dump(freeze,f,indent=2)
out=root/'corpus';out.mkdir();files={};counts={};audits={};parts={}
for part in ['calibration','holdout']:
 p=source/'corpus'/(part+'.jsonl');assert sha(p)==manifest['files'][p.name];rows=[json.loads(s) for s in p.read_text().splitlines()];kept,audit=exclude_training_contexts(rows,families);audits[part]=audit
 contexts={r['contextHash']:r for r in kept};parts[part]=contexts;groups=collections.Counter(r['sideGroup'] for r in contexts.values());n_families=len({f for r in contexts.values() for f in r['families']})
 assert sum(v for k,v in groups.items() if k!='direct_subject_positive')>=plan['minimumNegativeContextsPerPart']
 assert groups['direct_subject_positive']>=plan['minimumPositiveSubjectContextsPerPart'] and n_families>=plan['minimumFamiliesPerPart']
 path=out/(part+'.jsonl');path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in kept));files[path.name]=sha(path);enc=lambda s:base64.b64encode(s.encode()).decode();tsv=out/(part+'.tsv')
 tsv.write_text(''.join('\t'.join([str(i),enc(r['id']),part,'ru',enc(r['prefix']),enc(r['typed'])])+'\n' for i,r in enumerate(kept)));files[tsv.name]=sha(tsv)
 counts[part]=dict(rows=len(kept),contexts=len(contexts),groups=dict(groups),families=n_families,controls=sum(r['noAuto'] for r in kept),unfinishedControls=sum(r['retainBaseline'] for r in kept))
assert not ({f for r in parts['calibration'].values() for f in r['families']}&{f for r in parts['holdout'].values() for f in r['families']})
assert not (set(parts['calibration'])&set(parts['holdout']))
assert not ({r['article'] for r in parts['calibration'].values()}&{r['article'] for r in parts['holdout'].values()})
result=dict(stage='frozen-before-any-model-scoring',files=files,counts=counts,exclusionAudits=audits,planSha256=sha(root/'plan.json'),sourceManifestSha256=sha(source/'corpus/manifest.json'),trainingCorpusManifestSha256=sha(train/'corpus/manifest.json'),familyArticleContextSeparation=True,excludedAdditionalTrainingFamilies=True,modelScoresUsed=False,modelBindingRequiredBeforeScoring=True)
(out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(counts),flush=True)
