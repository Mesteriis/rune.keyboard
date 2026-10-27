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
from right_context_residual_ranker import NumericForest, ResidualRightContextRanker, STRUCTURAL_START, RESIDUAL_FEATURES
from residual_tree_batch import forest_scores

root = Path(__file__).parent
parent = Path('build/right-context-training-v8-20261027')
base_root = Path('build/right-context-training-v6-20261027')
assets = Path('app/src/main/assets/smarttyping/experiments')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
load = lambda p: json.loads(Path(p).read_text())


def write(name, value):
    with (root / name).open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


old = load(parent / 'frozen-model.json')
base_frozen = load(base_root / 'frozen-model.json')
previous_plan = load(parent / 'plan.json')
assert sha(parent / 'groups.jsonl') == old['groupsSha256']
assert sha(parent / 'train-vectors.npz') == old['vectorsSha256']
assert sha(parent / 'train-group-weights.npy') == old['weightsSha256']
assert sha(base_root / 'experimental-ranker.bin') == base_frozen['modelSha256']
assert all(sha(p) == h for p, h in old['modelFeatureSources'].items())
assert all(sha(p) == h for p, h in base_frozen['modelFeatureSources'].items())
assert all(sha(assets / p) == h for p, h in previous_plan['installedAssets'].items())
for name in ('groups.jsonl', 'train-vectors.npz', 'train-group-weights.npy', 'selection.json', 'morphology-receipt.json'):
    shutil.copyfile(parent / name, root / name)
shutil.copyfile(base_root / 'experimental-ranker.bin', root / 'base-ranker.bin')
groups = [json.loads(line) for line in (root / 'groups.jsonl').read_text().splitlines()]
data = np.load(root / 'train-vectors.npz')
x, y, ids = data['features'], data['labels'], data['group_ids']
weights = np.load(root / 'train-group-weights.npy')
assert x.shape == (428865, 202) and len(groups) == 30512 and len(weights) == len(x)
base = NumericForest.decode((root / 'base-ranker.bin').read_bytes(), 178)
baseline = forest_scores(base, x[:, :178])
assert np.isfinite(baseline).all()
np.save(root / 'baseline-raw-scores.npy', baseline)
probe_indices = sorted(set(range(32)) | set(range(0, len(x), 997)) | set(range(len(x) - 32, len(x))))
base_parity = max(abs(base.score(x[i, :178]) - baseline[i]) for i in probe_indices)
assert base_parity == 0
structural = np.ascontiguousarray(x[:, STRUCTURAL_START:])
assert structural.shape[1] == RESIDUAL_FEATURES == 56
pool = Pool(structural, y, group_id=ids, group_weight=weights, baseline=baseline)
pool_baseline = pool.get_baseline()[:, 0]
baseline_quantization = float(np.max(np.abs(pool_baseline - baseline)))
np.save(root / 'pool-baseline.npy', pool_baseline)
sources = dict(old['modelFeatureSources']) | {
    str(p): sha(p) for p in (Path('tools/typing_experiments/right_context_residual_ranker.py'),
                            Path('tools/typing_experiments/residual_tree_batch.py'), Path(__file__))}
plan = dict(previous_plan, stage='frozen-before-residual-fit', modelType='frozen-v6-plus-structural-residual',
            features=202, residualFeatures=56, residualStart=146, baseFeatures=178,
            baseModelSha256=base_frozen['modelSha256'], baseFrozenSha256=sha(base_root / 'frozen-model.json'),
            groupWeightsChanged=False, groupsAndVectorsChanged=False,
            architectureChange='Frozen v6 raw scores as per-candidate baseline; correction sees only 56 structural fields',
            baselineSha256=sha(root / 'baseline-raw-scores.npy'), baselineScalarBatchMaxDifference=base_parity,
            baselineParityProbes=len(probe_indices), poolBaselineQuantizationMaxDifference=baseline_quantization,
            sourceHashes=sources, holdoutScoresRead=False)
write('plan.json', plan)
print('BASELINE_READY', len(x), baseline_quantization, flush=True)
model = CatBoostRanker(iterations=plan['iterations'], depth=plan['depth'], learning_rate=plan['learningRate'],
                      loss_function=plan['loss'], random_seed=plan['seed'], thread_count=2,
                      verbose=False, allow_writing_files=False)
model.fit(pool)
rank.export_tree(model, root / 'residual-ranker.bin', RESIDUAL_FEATURES)
residual = NumericForest.decode((root / 'residual-ranker.bin').read_bytes(), 56)
delta = forest_scores(residual, structural)
combined = baseline + delta
cat_delta = model.predict(structural)
cat_combined = model.predict(pool)
delta_error = float(np.max(np.abs(delta - cat_delta)))
composition_error = float(np.max(np.abs(combined - cat_combined)))
pool_addition_error = float(np.max(np.abs(cat_delta + pool_baseline - cat_combined)))
assert delta_error < 1e-5 and composition_error < 1e-5 and pool_addition_error < 1e-12
ranker = ResidualRightContextRanker((root / 'base-ranker.bin').read_bytes(), (root / 'residual-ranker.bin').read_bytes())
composition_parity = max(abs(ranker.raw_score(x[i]) - combined[i]) for i in probe_indices)
assert composition_parity == 0
stats = collections.Counter()
scenarios = collections.defaultdict(lambda: dict(groups=0, targetFirst=0, baseTargetFirst=0))
offset = 0
for gid, group in enumerate(groups):
    n = len(group['candidates'])
    assert np.all(ids[offset:offset + n] == gid)
    assert np.all(weights[offset:offset + n] == weights[offset])
    chosen = int(np.argmax(combined[offset:offset + n]))
    base_chosen = int(np.argmax(baseline[offset:offset + n]))
    kind = group['row']['kind']
    good = chosen == group['target']
    base_good = base_chosen == group['target']
    key = group['row']['scenario'] + ':' + kind
    stats[kind + 'Groups'] += 1
    stats[kind + 'TargetFirst'] += good
    stats[kind + 'BaseTargetFirst'] += base_good
    scenarios[key]['groups'] += 1
    scenarios[key]['targetFirst'] += good
    scenarios[key]['baseTargetFirst'] += base_good
    offset += n
assert offset == len(x)
assert all(sha(assets / p) == h for p, h in plan['installedAssets'].items())
write('training-diagnostic.json', dict(groups=len(groups), candidateRows=len(x), counts=dict(stats),
      scenarios=dict(scenarios), deltaVsCatBoostMaxDifference=delta_error,
      combinedVsCatBoostMaxDifference=composition_error, catBoostPoolAddsBaselineMaxDifference=pool_addition_error,
      scalarBatchCombinedMaxDifference=composition_parity, trainingOnly=True))
write('composite.json', dict(schema=1, mode='raw_sum_then_0.8_tanh_div_4', fullFeatures=202,
      base=dict(file='base-ranker.bin', features=178, sha256=sha(root / 'base-ranker.bin')),
      residual=dict(file='residual-ranker.bin', features=56, start=146, sha256=sha(root / 'residual-ranker.bin'))))
write('frozen-model.json', dict(stage='frozen-before-disclosed-diagnostic', qualified=False, modelType=plan['modelType'],
      featureCount=202, residualFeatureCount=56, modelSha256=sha(root / 'composite.json'),
      modelIdentityIsCompositeManifest=True, modelBytes=(root / 'base-ranker.bin').stat().st_size + (root / 'residual-ranker.bin').stat().st_size,
      baseModelSha256=sha(root / 'base-ranker.bin'), residualModelSha256=sha(root / 'residual-ranker.bin'),
      planSha256=sha(root / 'plan.json'), groupsSha256=sha(root / 'groups.jsonl'), vectorsSha256=sha(root / 'train-vectors.npz'),
      weightsSha256=sha(root / 'train-group-weights.npy'), modelFeatureSources=sources,
      trainingGroups=len(groups), candidateRows=len(x), trainingFamilies=old['trainingFamilies'], installedAssetsUnchanged=True))
print(json.dumps(load(root / 'training-diagnostic.json')), flush=True)
print('COMPOSITE_FROZEN', sha(root / 'composite.json'), flush=True)
