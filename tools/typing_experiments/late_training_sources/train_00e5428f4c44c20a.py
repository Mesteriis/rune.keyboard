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
from right_context_residual_ranker import NumericForest
from right_context_applied_ranker import AppliedResidualForest, AppliedResidualRanker
from residual_tree_batch import forest_scores

root = Path(__file__).parent
inputs = Path('build/right-context-applied-v10-v2-20261027')
previous = Path('build/right-context-residual-v9-20261027')
base_root = Path('build/right-context-training-v6-20261027')
assets = Path('app/src/main/assets/smarttyping/experiments')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
load = lambda p: json.loads(Path(p).read_text())


def write(name, value):
    with (root / name).open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


prepared = load(inputs / 'feature-preparation.json')
previous_frozen = load(previous / 'frozen-model.json')
old_plan = load(previous / 'plan.json')
base_frozen = load(base_root / 'frozen-model.json')
assert all(sha(p) == h for p, h in prepared['sourceHashes'].items())
assert all(sha(p) == h for p, h in previous_frozen['modelFeatureSources'].items())
assert sha(inputs / 'groups.jsonl') == prepared['groupsSha256']
assert sha(inputs / 'train-vectors.npz') == prepared['vectorsSha256']
assert sha(inputs / 'train-group-weights.npy') == prepared['weightsSha256']
assert sha(base_root / 'experimental-ranker.bin') == base_frozen['modelSha256']
assert all(sha(assets / p) == h for p, h in prepared['installedAssets'].items())
for name in ('groups.jsonl', 'train-vectors.npz', 'train-group-weights.npy', 'morphology-receipt.json'):
    shutil.copyfile(inputs / name, root / name)
shutil.copyfile(base_root / 'experimental-ranker.bin', root / 'base-ranker.bin')
groups = [json.loads(line) for line in (root / 'groups.jsonl').read_text().splitlines()]
data = np.load(root / 'train-vectors.npz')
x, y, ids = data['features'], data['labels'], data['group_ids']
weights = np.load(root / 'train-group-weights.npy')
assert x.shape == (445321, 221) and len(groups) == 32024
base = NumericForest.decode((root / 'base-ranker.bin').read_bytes(), 178)
baseline = forest_scores(base, x[:, :178])
structural = np.ascontiguousarray(x[:, 146:])
assert structural.shape[1] == 75 and np.isfinite(baseline).all()
np.save(root / 'baseline-raw-scores.npy', baseline)
pool = Pool(structural, y, group_id=ids, group_weight=weights, baseline=baseline)
pool_baseline = pool.get_baseline()[:, 0]
sources = dict(previous_frozen['modelFeatureSources']) | prepared['sourceHashes'] | {
    str(p): sha(p) for p in (Path('tools/typing_experiments/right_context_applied_ranker.py'), Path(__file__))}
plan = dict(stage='frozen-before-applied-role-fit', purpose='EXPERIMENTAL_TRAINING_ONLY',
            modelType='frozen-v6-plus-applied-role-residual', features=221, residualFeatures=75,
            residualStart=146, baseFeatures=178, baseModelSha256=base_frozen['modelSha256'],
            groups=len(groups), candidateRows=len(x), iterations=128, depth=6, learningRate=.05,
            seed=25102026, loss='PairLogitPairwise', qualification=old_plan['qualification'],
            sourceHashes=sources, installedAssets=prepared['installedAssets'], countsSha256=prepared['countsSha256'],
            preparationSha256=sha(inputs / 'feature-preparation.json'),
            groupsSha256=sha(root / 'groups.jsonl'), vectorsSha256=sha(root / 'train-vectors.npz'),
            weightsSha256=sha(root / 'train-group-weights.npy'), baselineSha256=sha(root / 'baseline-raw-scores.npy'),
            poolBaselineQuantizationMaxDifference=float(np.max(np.abs(baseline - pool_baseline))),
            naturalFailuresUsedForSupervision=False, holdoutScoresRead=False)
write('plan.json', plan)
print('BASELINE_READY', len(x), flush=True)
model = CatBoostRanker(iterations=128, depth=6, learning_rate=.05, loss_function='PairLogitPairwise',
                      random_seed=25102026, thread_count=2, verbose=False, allow_writing_files=False)
model.fit(pool)
rank.export_tree(model, root / 'residual-ranker.bin', 75)
head = AppliedResidualForest.decode((root / 'residual-ranker.bin').read_bytes())
delta = forest_scores(head, structural)
combined = baseline + delta
cat_delta, cat_combined = model.predict(structural), model.predict(pool)
delta_error = float(np.max(np.abs(delta - cat_delta)))
combined_error = float(np.max(np.abs(combined - cat_combined)))
assert delta_error < 1e-5 and combined_error < 1e-5
assert float(np.max(np.abs(cat_delta + pool_baseline - cat_combined))) < 1e-12
ranker = AppliedResidualRanker((root / 'base-ranker.bin').read_bytes(), (root / 'residual-ranker.bin').read_bytes())
probes = sorted(set(range(32)) | set(range(0, len(x), 997)) | set(range(len(x)-32, len(x))))
reference_error = 0.
for i in probes:
    expected = rank.tree_score((root / 'base-ranker.bin').read_bytes(), x[i, :178]) + rank.tree_score((root / 'residual-ranker.bin').read_bytes(), x[i, 146:])
    reference_error = max(reference_error, abs(expected - ranker.raw_score(x[i])), abs(expected - combined[i]))
assert reference_error == 0
stats = collections.Counter()
scenarios = collections.defaultdict(lambda: dict(groups=0, targetFirst=0))
offset = 0
for gid, group in enumerate(groups):
    n = len(group['candidates'])
    assert np.all(ids[offset:offset+n] == gid) and np.all(weights[offset:offset+n] == weights[offset])
    chosen = int(np.argmax(combined[offset:offset+n]))
    kind = group['row']['kind']
    good = chosen == group['target']
    key = group['row']['scenario'] + ':' + kind
    stats[kind + 'Groups'] += 1
    stats[kind + 'TargetFirst'] += good
    scenarios[key]['groups'] += 1
    scenarios[key]['targetFirst'] += good
    offset += n
assert offset == len(x)
assert all(sha(assets / p) == h for p, h in plan['installedAssets'].items())
write('training-diagnostic.json', dict(groups=len(groups), candidateRows=len(x), counts=dict(stats),
      scenarios=dict(scenarios), deltaVsCatBoostMaxDifference=delta_error,
      combinedVsCatBoostMaxDifference=combined_error, scalarBatchLegacyMaxDifference=reference_error,
      referenceProbes=len(probes), trainingOnly=True))
write('composite.json', dict(schema=2, mode='raw_sum_then_0.8_tanh_div_4', fullFeatures=221,
      base=dict(file='base-ranker.bin', features=178, sha256=sha(root / 'base-ranker.bin')),
      residual=dict(file='residual-ranker.bin', features=75, start=146, sha256=sha(root / 'residual-ranker.bin'))))
write('frozen-model.json', dict(stage='frozen-before-disclosed-diagnostic', qualified=False,
      featureCount=221, residualFeatureCount=75, modelType=plan['modelType'],
      modelSha256=sha(root / 'composite.json'), modelIdentityIsCompositeManifest=True,
      modelBytes=(root / 'base-ranker.bin').stat().st_size + (root / 'residual-ranker.bin').stat().st_size,
      baseModelSha256=sha(root / 'base-ranker.bin'), residualModelSha256=sha(root / 'residual-ranker.bin'),
      planSha256=sha(root / 'plan.json'), groupsSha256=sha(root / 'groups.jsonl'), vectorsSha256=sha(root / 'train-vectors.npz'),
      weightsSha256=sha(root / 'train-group-weights.npy'), modelFeatureSources=sources,
      trainingGroups=len(groups), candidateRows=len(x), trainingFamilies=prepared['trainingFamilies'], installedAssetsUnchanged=True))
print(json.dumps(load(root / 'training-diagnostic.json')), flush=True)
print('COMPOSITE_FROZEN', sha(root / 'composite.json'), flush=True)
