"""Compare saved residual models on retained training vectors, without qualification."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

if not __debug__:
    raise RuntimeError('RESIDUAL_REPLAY_REQUIRES_ASSERTIONS')
ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
output = args.output.resolve()
if Path.cwd().resolve() != ROOT or not output.is_relative_to(ROOT / 'build') or output.exists():
    raise ValueError('RESIDUAL_REPLAY_OUTPUT_OR_WORKDIR')

import numpy as np
sys.path.insert(0, 'tools/typing_experiments')
import rank_refinement as legacy
from right_context_residual_ranker import ResidualRightContextRanker
from right_context_applied_ranker import AppliedResidualRanker
from right_context_left_role_ranker import LeftRoleResidualRanker
from residual_tree_batch import forest_scores


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


NAMES = ('right-context-residual-v9-20261027', 'right-context-applied-residual-v10-20261027',
         'right-context-left-role-residual-v11-20261027', 'right-context-oblique-residual-v12-20261027',
         'right-context-symmetric-residual-v13-20261027', 'right-context-signature-residual-v14-20261027')
results = []
for name in NAMES:
    directory = ROOT / 'build' / name
    record_path = directory / 'frozen-model.json'
    record_raw = record_path.read_bytes()
    frozen = json.loads(record_raw)
    assert frozen['qualified'] is False and frozen['modelIdentityIsCompositeManifest'] is True
    pairs = (('modelSha256', 'composite.json'), ('baseModelSha256', 'base-ranker.bin'),
             ('residualModelSha256', 'residual-ranker.bin'), ('planSha256', 'plan.json'),
             ('groupsSha256', 'groups.jsonl'), ('vectorsSha256', 'train-vectors.npz'),
             ('weightsSha256', 'train-group-weights.npy'))
    assert all(sha(directory / file) == frozen[key] for key, file in pairs)
    width = frozen['featureCount']
    decoder_class, decoder_source = {202: (ResidualRightContextRanker, None),
                                     221: (AppliedResidualRanker, 'right_context_applied_ranker.py'),
                                     242: (LeftRoleResidualRanker, 'right_context_left_role_ranker.py')}[width]
    scorers = ('rank_refinement.py', 'right_context_residual_ranker.py', 'residual_tree_batch.py')
    if decoder_source is not None:
        scorers += (decoder_source,)
    for filename in scorers:
        relative = 'tools/typing_experiments/' + filename
        assert sha(ROOT / relative) == frozen['modelFeatureSources'][relative]
    base_blob = (directory / 'base-ranker.bin').read_bytes()
    delta_blob = (directory / 'residual-ranker.bin').read_bytes()
    ranker = decoder_class(base_blob, delta_blob)
    features = np.load(directory / 'train-vectors.npz', allow_pickle=False)['features']
    assert features.shape == (frozen['candidateRows'], frozen['featureCount'])
    raw_max = bounded_max = batch_max = 0.0
    nonfinite = 0
    for start in range(0, len(features), 2048):
        matrix = np.asarray(features[start:start + 2048], dtype=np.float64)
        batch = forest_scores(ranker.base, matrix[:, :178]) + forest_scores(ranker.residual, matrix[:, 146:])
        for index, vector in enumerate(matrix):
            expected = legacy.tree_score(base_blob, vector[:178]) + legacy.tree_score(delta_blob, vector[146:])
            raw = ranker.raw_score(vector)
            bounded = ranker.score(vector)
            deltas = (abs(expected - raw), abs(.8 * math.tanh(expected / 4) - bounded),
                      abs(expected - float(batch[index])))
            nonfinite += int(not all(math.isfinite(value) for value in (expected, raw, bounded, *deltas)))
            raw_max, bounded_max, batch_max = (max(old, value) for old, value in zip(
                (raw_max, bounded_max, batch_max), deltas))
        if start // 2048 % 50 == 0:
            print('model', name, 'rows', min(start + len(matrix), len(features)), flush=True)
    assert nonfinite == 0 and raw_max == bounded_max == batch_max == 0.0
    assert record_path.read_bytes() == record_raw and all(sha(directory / file) == frozen[key] for key, file in pairs)
    for filename in scorers:
        relative = 'tools/typing_experiments/' + filename
        assert sha(ROOT / relative) == frozen['modelFeatureSources'][relative]
    results.append(dict(model=name, rows=len(features), features=features.shape[1], nonfinite=nonfinite,
                        rawMaximumDifference=raw_max, boundedMaximumDifference=bounded_max,
                        batchMaximumDifference=batch_max))
    print('completed', name, 'rows', len(features), flush=True)
with output.open('x') as stream:
    stream.write(json.dumps(dict(scope='historical-training-vectors-only', qualification=False, models=results),
                            sort_keys=True, indent=2, allow_nan=False) + '\n')
