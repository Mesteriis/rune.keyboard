from pathlib import Path
import sys,json,hashlib,shutil,collections
import numpy as np
from catboost import CatBoostRanker,Pool
sys.path.insert(0,'tools/typing_experiments');import rank_refinement as rank
root=Path('build/right-context-training-v6-20261027');parent=Path('build/right-context-training-v5-20261027');assets=Path('app/src/main/assets/smarttyping/experiments');load=lambda p:json.loads(Path(p).read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,obj):
 with (root/name).open('x') as f:json.dump(obj,f,indent=2);f.write('\n')
frozen=load(parent/'frozen-model.json');old_plan=load(parent/'plan.json');assert all(sha(p)==h for p,h in frozen['modelFeatureSources'].items())
assert all(sha(assets/name)==h for name,h in old_plan['installedAssets'].items())
assert sha(parent/'groups.jsonl')==frozen['groupsSha256'] and sha(parent/'train-vectors.npz')==frozen['vectorsSha256']
assert not (root/'experimental-ranker.bin').exists();(root/'corpus').mkdir()
for name in ['groups.jsonl','train-vectors.npz','morphology-receipt.json','selection.json','corpus/train.jsonl','corpus/manifest.json']:shutil.copyfile(parent/name,root/name)
plan=dict(old_plan,stage='frozen-before-depth-six-fit',depth=6,parentModelSha256=frozen['modelSha256'],reason='v5 training audit fits only 160/240 explicit noun-frame targets; increase conditional capacity within the existing export format',corpusAndCandidatePoolsChanged=False,sourceHashes=dict(frozen['modelFeatureSources'])|{str(Path(__file__).relative_to(Path.cwd())):sha(__file__)})
write('plan.json',plan)
data=np.load(root/'train-vectors.npz');x=data['features'];y=data['labels'];ids=data['group_ids'];assert x.shape[1]==plan['features'];groups=list(map(json.loads,(root/'groups.jsonl').read_text().splitlines()))
model=CatBoostRanker(iterations=plan['iterations'],depth=plan['depth'],learning_rate=plan['learningRate'],loss_function=plan['loss'],random_seed=plan['seed'],thread_count=2,verbose=False,allow_writing_files=False)
model.fit(Pool(x,y,group_id=ids));rank.export_tree(model,root/'experimental-ranker.bin',plan['features']);blob=(root/'experimental-ranker.bin').read_bytes();raw=model.predict(x);offset=0;stats=collections.Counter();scenarios=collections.defaultdict(lambda:dict(groups=0,targetFirst=0));error=0
for gid,g in enumerate(groups):
 n=len(g['candidates']);chosen=int(np.argmax(raw[offset:offset+n]));kind=g['row']['kind'];key=g['row']['scenario']+':'+kind;good=chosen==g['target'];stats[kind+'Groups']+=1;stats[kind+'TargetFirst']+=good;scenarios[key]['groups']+=1;scenarios[key]['targetFirst']+=good
 if gid<32:
  for i in range(n):error=max(error,abs(rank.tree_score(blob,x[offset+i])-raw[offset+i]))
 offset+=n
assert offset==len(x) and error<1e-5
write('training-diagnostic.json',dict(groups=len(groups),candidateRows=len(x),counts=dict(stats),scenarios=dict(scenarios),scalarVsCatBoostMaxAbsoluteDifference=error,trainingOnly=True))
assert all(sha(assets/name)==h for name,h in plan['installedAssets'].items())
write('frozen-model.json',dict(stage='frozen-before-new-calibration',qualified=False,featureCount=plan['features'],modelBytes=len(blob),modelSha256=sha(root/'experimental-ranker.bin'),planSha256=sha(root/'plan.json'),groupsSha256=sha(root/'groups.jsonl'),vectorsSha256=sha(root/'train-vectors.npz'),selectionSha256=sha(root/'selection.json'),modelFeatureSources=plan['sourceHashes'],trainingGroups=len(groups),candidateRows=len(x),trainingFamilies=frozen['trainingFamilies'],installedAssetsUnchanged=True))
print(json.dumps(load(root/'training-diagnostic.json')),flush=True);print('MODEL_FROZEN',sha(root/'experimental-ranker.bin'),flush=True)
