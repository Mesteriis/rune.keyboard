from pathlib import Path
import sys,json,hashlib,functools,math,collections
import numpy as np
from catboost import CatBoostRanker,Pool
sys.path.insert(0,'tools/typing_experiments')
import rank_refinement as rank,neural_refinement as neural
from word_context_features import WordContextFeatures
from grammar_context_features import GrammarContextFeatures
from right_context_grammar_features import RightContextGrammarFeatures
from right_context_role_features import RightContextRoleFeatures,role_revision_features,FEATURES
sys.path.insert(0,'tools/morphology');from ranker import PymorphyLexicon
root=Path('build/right-context-training-v4-20261027');assets=Path('app/src/main/assets/smarttyping/experiments')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text())
def write(name,obj):
 with (root/name).open('x') as out:json.dump(obj,out,ensure_ascii=False,indent=2);out.write('\n')
assert not (root/'experimental-ranker.bin').exists(),'FRESH_MODEL_REQUIRED'
selection=load(root/'selection.json');assert sha(root/'groups.jsonl')==selection['groupsSha256']
assert sha(root/'production-pools/observations.jsonl')==selection['observationsSha256']
assert all(sha(p)==h for p,h in selection['sourceHashes'].items())
counts=[Path('build/context-ranking-20261025/counts-v3/model-counts.jsonl'),Path('build/context-feature-ranker-20261026/tatoeba-train-counts.jsonl')]
previous=load('build/noun-case-training-20261026/frozen-model.json')
assert [sha(p) for p in counts]==previous['countsSha256']
assert all(sha(p)==h for p,h in previous['featureSources'].items())
lex=PymorphyLexicon(cache_size=16384);assert lex.receipt()==load('build/noun-case-training-20261026/morphology-receipt.json')
write('morphology-receipt.json',lex.receipt())
groups=[json.loads(line) for line in (root/'groups.jsonl').read_text().splitlines()]
sources=['tools/typing_experiments/right_context_grammar_features.py','tools/typing_experiments/right_context_revision_features.py','tools/typing_experiments/right_context_training_groups.py','tools/typing_experiments/right_context_role_features.py','tools/typing_experiments/right_context_role_corpus.py','tools/typing_experiments/rank_refinement.py','tools/typing_experiments/train.py','tools/typing_experiments/word_context_features.py','tools/typing_experiments/grammar_context_features.py','tools/typing_experiments/neural_refinement.py',__file__]
plan=dict(stage='frozen-before-fit',purpose='EXPERIMENTAL_TRAINING_ONLY',features=FEATURES,layout='163 frozen revision features + 15 case-role and singular-gender features',iterations=128,depth=5,learningRate=.05,seed=25102026,loss='PairLogitPairwise',groups=len(groups),families=len({g['row']['family'] for g in groups}),groupsSha256=sha(root/'groups.jsonl'),counterfactualApplied=True,priorProductionModelsReplaced=False,
 qualification=dict(requiredPrecision=.95,maximumWrongChanges=0,maximumControlChanges=0,maximumPriorCorrectLosses=0,minimumNewCorrect=100,independentFamilyExclusion=True,disclosedRegressionExcluded=True,productionAdmissionAndOwnershipRequired=True),sourceHashes={p:sha(p) for p in sources},countsSha256=[sha(p) for p in counts],installedAssets={p.name:sha(p) for p in assets.iterdir() if p.suffix in ['.bin','.ctx','.gram','.json']})
write('plan.json',plan)
tables=[WordContextFeatures.load(path) for path in counts];grammar=GrammarContextFeatures(lex);right=RightContextGrammarFeatures(lex);role=RightContextRoleFeatures(lex)
character_model=neural.load_model(assets/'ru-ranking-context.bin')
@functools.lru_cache(maxsize=100000)
def base(context,original,serialized):
 candidate=json.loads(serialized)
 return tuple(rank.features(context,original,candidate)+[v for table in tables for v in table.extract(context,original,candidate['text'])]+[neural.context_score(character_model,context,candidate['text'])]+grammar.extract(context,original,candidate['text']))
x=[];y=[];ids=[]
for gid,g in enumerate(groups):
 r=g['row'];context=r['leftContext'][-128:]
 for i,c in enumerate(g['candidates']):
  b=base(context,r['original'],json.dumps(c,sort_keys=True))
  values=role_revision_features(b,right,role,context,r['rightContext'],r['applied'],c['text'])
  assert len(values)==FEATURES
  x.append(values);y.append(int(i==g['target']));ids.append(gid)
 if gid%300==0:print('VECTORIZED',gid,flush=True)
x=np.asarray(x,dtype=np.float32);y=np.asarray(y,dtype=np.int32);ids=np.asarray(ids,dtype=np.int32)
np.savez_compressed(root/'train-vectors.npz',features=x,labels=y,group_ids=ids)
model=CatBoostRanker(iterations=plan['iterations'],depth=plan['depth'],learning_rate=plan['learningRate'],loss_function=plan['loss'],random_seed=plan['seed'],thread_count=2,verbose=False,allow_writing_files=False)
model.fit(Pool(x,y,group_id=ids));rank.export_tree(model,root/'experimental-ranker.bin',FEATURES)
blob=(root/'experimental-ranker.bin').read_bytes();raw=model.predict(x);offset=0;stats=collections.Counter();maxScalarDifference=0
for gid,g in enumerate(groups):
 length=len(g['candidates']);prediction=int(np.argmax(raw[offset:offset+length]));kind=g['row']['kind']
 stats[kind+'Groups']+=1;stats[kind+'TargetFirst']+=prediction==g['target']
 if gid<32:
  for i in range(length):maxScalarDifference=max(maxScalarDifference,abs(rank.tree_score(blob,x[offset+i])-raw[offset+i]))
 offset+=length
write('training-diagnostic.json',dict(groups=len(groups),candidateRows=len(x),counts=dict(stats),scalarVsCatBoostMaxAbsoluteDifference=maxScalarDifference,trainingOnly=True))
assert maxScalarDifference<1e-5
assert all(sha(assets/name)==h for name,h in plan['installedAssets'].items())
write('frozen-model.json',dict(stage='frozen-before-independent-evaluation',qualified=False,featureCount=FEATURES,modelBytes=len(blob),modelSha256=sha(root/'experimental-ranker.bin'),planSha256=sha(root/'plan.json'),groupsSha256=sha(root/'groups.jsonl'),vectorsSha256=sha(root/'train-vectors.npz'),selectionSha256=sha(root/'selection.json'),modelFeatureSources=plan['sourceHashes'],trainingGroups=len(groups),candidateRows=len(x),trainingFamilies=sorted({g['row']['family'] for g in groups}),installedAssetsUnchanged=True))
print(json.dumps(load(root/'training-diagnostic.json')),flush=True)
print('MODEL_FROZEN',sha(root/'experimental-ranker.bin'),flush=True)
