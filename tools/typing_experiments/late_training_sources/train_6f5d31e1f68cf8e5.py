from pathlib import Path
import collections
import hashlib
import json
import shutil
import sys
import numpy as np
from catboost import CatBoostRanker, Pool

sys.path.insert(0, 'tools/typing_experiments')
import rank_refinement as rank

root = Path(__file__).parent
parent = Path('build/right-context-training-v7-20261027')
assets = Path('app/src/main/assets/smarttyping/experiments')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
load = lambda p: json.loads(Path(p).read_text())


def write(name, value):
    with (root / name).open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


frozen = load(parent / 'frozen-model.json')
old_plan = load(parent / 'plan.json')
assert all(sha(p) == h for p, h in frozen['modelFeatureSources'].items())
assert sha(parent / 'groups.jsonl') == frozen['groupsSha256']
assert sha(parent / 'train-vectors.npz') == frozen['vectorsSha256']
assert all(sha(assets / p) == h for p, h in old_plan['installedAssets'].items())
for name in ('groups.jsonl', 'train-vectors.npz', 'selection.json', 'morphology-receipt.json'):
    shutil.copyfile(parent / name, root / name)
groups = [json.loads(line) for line in (root / 'groups.jsonl').read_text().splitlines()]
data = np.load(root / 'train-vectors.npz')
x, y, ids = data['features'], data['labels'], data['group_ids']
weights = np.empty(len(x), dtype=np.float32)
offset = 0
weighted = 0
for gid, group in enumerate(groups):
    row = group['row']
    revision = (row['kind'] == 'unknown_original' and row['expectedApplied'] != row['applied']
                and row['applied'] != row['original'])
    n = len(group['candidates'])
    assert np.all(ids[offset:offset + n] == gid)
    weights[offset:offset + n] = 3.0 if revision else 1.0
    weighted += revision
    offset += n
assert offset == len(x)
np.save(root / 'train-group-weights.npy', weights)
plan = dict(old_plan, stage='frozen-before-authored-revision-weight-fit',
            parentModelSha256=frozen['modelSha256'], corpusAndVectorsChanged=False,
            weightPolicy=dict(resolvedWrongAppliedRevision=3.0, allOtherGroups=1.0,
                rationale='400 of 402 authored closure errors retain a wrong already applied form; raw acquisition is not the same training task',
                basedOnAuthoredTrainingOnly=True, weightedGroups=weighted),
            weightsSha256=sha(root / 'train-group-weights.npy'),
            sourceHashes=dict(frozen['modelFeatureSources']) | {str(Path(__file__)): sha(__file__)})
write('plan.json', plan)
model = CatBoostRanker(iterations=plan['iterations'], depth=plan['depth'],
                      learning_rate=plan['learningRate'], loss_function=plan['loss'],
                      random_seed=plan['seed'], thread_count=2, verbose=False, allow_writing_files=False)
model.fit(Pool(x, y, group_id=ids, group_weight=weights))
rank.export_tree(model, root / 'experimental-ranker.bin', plan['features'])
blob = (root / 'experimental-ranker.bin').read_bytes()
raw = model.predict(x)
stats = collections.Counter()
scenarios = collections.defaultdict(lambda: dict(groups=0, targetFirst=0))
offset = 0
error = 0
for gid, group in enumerate(groups):
    n = len(group['candidates'])
    chosen = int(np.argmax(raw[offset:offset + n]))
    kind = group['row']['kind']
    good = chosen == group['target']
    key = group['row']['scenario'] + ':' + kind
    stats[kind + 'Groups'] += 1
    stats[kind + 'TargetFirst'] += good
    scenarios[key]['groups'] += 1
    scenarios[key]['targetFirst'] += good
    if gid < 32 or gid % 1000 == 0 or gid >= len(groups) - 32:
        for index in range(n):
            error = max(error, abs(rank.tree_score(blob, x[offset + index]) - raw[offset + index]))
    offset += n
assert offset == len(x) and error < 1e-5
assert all(sha(assets / p) == h for p, h in plan['installedAssets'].items())
write('training-diagnostic.json', dict(groups=len(groups), candidateRows=len(x), counts=dict(stats),
      scenarios=dict(scenarios), scalarVsCatBoostMaxAbsoluteDifference=error, trainingOnly=True))
write('frozen-model.json', dict(stage='frozen-before-diagnostic-scoring', qualified=False,
      featureCount=plan['features'], modelBytes=len(blob), modelSha256=sha(root / 'experimental-ranker.bin'),
      planSha256=sha(root / 'plan.json'), groupsSha256=sha(root / 'groups.jsonl'),
      vectorsSha256=sha(root / 'train-vectors.npz'), weightsSha256=sha(root / 'train-group-weights.npy'),
      selectionSha256=sha(root / 'selection.json'), modelFeatureSources=plan['sourceHashes'],
      trainingGroups=len(groups), candidateRows=len(x), trainingFamilies=frozen['trainingFamilies'],
      installedAssetsUnchanged=True))
print(json.dumps(load(root / 'training-diagnostic.json')), flush=True)
print('MODEL_FROZEN', sha(root / 'experimental-ranker.bin'), flush=True)
