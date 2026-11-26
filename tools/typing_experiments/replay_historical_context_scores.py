"""Compare historical exported and CatBoost scores on retained training vectors."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

if not __debug__:
    raise RuntimeError('CONTEXT_SCORE_REQUIRES_ASSERTIONS')
ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
output = args.output.resolve()
if Path.cwd().resolve() != ROOT or not output.is_relative_to(ROOT / 'build') or output.exists():
    raise ValueError('CONTEXT_SCORE_OUTPUT_OR_WORKDIR')

import numpy as np
from catboost import CatBoostRanker
sys.path.insert(0, 'tools/typing_experiments')
import rank_refinement as rank


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


results = []
for version in range(1, 9):
    name = 'v' + str(version)
    directory = ROOT / ('build/right-context-training-20261027' if version == 1
                        else 'build/right-context-training-' + name + '-20261027')
    frozen_path = directory / 'frozen-model.json'
    frozen_bytes = frozen_path.read_bytes()
    frozen = json.loads(frozen_bytes)
    assert frozen['qualified'] is False
    inputs = {'planSha256': directory / 'plan.json', 'modelSha256': directory / 'experimental-ranker.bin',
              'vectorsSha256': directory / 'train-vectors.npz', 'groupsSha256': directory / 'groups.jsonl'}
    assert all(sha(path) == frozen[key] for key, path in inputs.items())
    scorer_path = ROOT / 'tools/typing_experiments/rank_refinement.py'
    assert sha(scorer_path) == frozen['modelFeatureSources']['tools/typing_experiments/rank_refinement.py']
    json_model = directory / 'experimental-ranker.json'
    json_model_sha = sha(json_model)
    diagnostic_path = directory / 'training-diagnostic.json'
    diagnostic_sha = sha(diagnostic_path)
    diagnostic = json.loads(diagnostic_path.read_bytes())
    vectors = np.load(inputs['vectorsSha256'], allow_pickle=False)
    features, labels, ids = vectors['features'], vectors['labels'], vectors['group_ids']
    assert features.shape == (frozen['candidateRows'], frozen['featureCount'])
    assert len(labels) == len(ids) == len(features)
    groups = [json.loads(line) for line in inputs['groupsSha256'].read_text().splitlines()]
    assert len(groups) == frozen['trainingGroups']
    model = CatBoostRanker()
    model.load_model(str(json_model), format='json')
    scores = model.predict(features, thread_count=2)
    binary = inputs['modelSha256'].read_bytes()
    offset = nonfinite = 0
    maximum = 0.0
    counts = {}
    for gid, group in enumerate(groups):
        size = len(group['candidates'])
        assert size > 0 and np.all(ids[offset:offset + size] == gid)
        assert int(labels[offset:offset + size].sum()) == 1 and int(labels[offset + group['target']]) == 1
        kind = group['row']['kind']
        counts[kind + 'Groups'] = counts.get(kind + 'Groups', 0) + 1
        counts[kind + 'TargetFirst'] = counts.get(kind + 'TargetFirst', 0) + int(
            int(np.argmax(scores[offset:offset + size])) == group['target'])
        for index in range(offset, offset + size):
            score = float(rank.tree_score(binary, features[index]))
            delta = abs(score - float(scores[index]))
            nonfinite += int(not np.isfinite(score) or not np.isfinite(delta))
            maximum = max(maximum, delta)
        offset += size
        if (gid + 1) % 5000 == 0:
            print('model', name, 'groups', gid + 1, 'rows', offset, flush=True)
    assert offset == len(features) and counts == diagnostic['counts']
    assert nonfinite == 0 and maximum < 1e-5
    assert frozen_path.read_bytes() == frozen_bytes and all(sha(path) == frozen[key] for key, path in inputs.items())
    assert sha(json_model) == json_model_sha and sha(diagnostic_path) == diagnostic_sha
    assert sha(scorer_path) == frozen['modelFeatureSources']['tools/typing_experiments/rank_refinement.py']
    results.append(dict(model=name, rows=offset, groups=len(groups), features=features.shape[1],
                        maximumDifference=maximum, nonfinite=nonfinite, trainingCountsMatch=True,
                        jsonModelSha256=json_model_sha, binaryModelSha256=frozen['modelSha256']))
    print('completed', name, 'rows', offset, 'maximumDifference', maximum, flush=True)
receipt = dict(scope='historical-training-vectors-only', qualification=False, models=results)
with output.open('x') as stream:
    stream.write(json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False) + '\n')
