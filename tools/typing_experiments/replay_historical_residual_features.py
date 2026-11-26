"""Replay saved residual training features without fitting or qualifying models."""
import argparse
import functools
import hashlib
import json
from pathlib import Path
import sys

if not __debug__:
    raise RuntimeError('RESIDUAL_FEATURE_REQUIRES_ASSERTIONS')
ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
output = args.output.resolve()
if Path.cwd().resolve() != ROOT or not output.is_relative_to(ROOT / 'build') or output.exists():
    raise ValueError('RESIDUAL_FEATURE_OUTPUT_OR_WORKDIR')

import numpy as np
sys.path[:0] = [str(ROOT / 'tools/ci'), str(ROOT / 'tools/typing_experiments'), str(ROOT / 'tools/morphology')]
import verify_role_model_sources as inventory
import rank_refinement as rank
import neural_refinement as neural
from ranker import PymorphyLexicon
from word_context_features import WordContextFeatures
from grammar_context_features import GrammarContextFeatures
from right_context_grammar_features import RightContextGrammarFeatures
from right_context_role_features import RightContextRoleFeatures, role_revision_features
from right_context_continuation_features import RightContextContinuationFeatures, extend_continuation_features
from right_context_applied_features import AppliedWordFeatures
from right_context_left_sequence_features import LeftSequenceFeatures
from right_context_training_weights import strong_supervision_weight
from right_context_signature_weights import TargetSignatureWeights

ASSETS = ROOT / 'app/src/main/assets/smarttyping/experiments'
COUNTS = [ROOT / 'build/context-ranking-20261025/counts-v3/model-counts.jsonl',
          ROOT / 'build/context-feature-ranker-20261026/tatoeba-train-counts.jsonl']
MODELS = ('right-context-applied-residual-v10-20261027', 'right-context-left-role-residual-v11-20261027',
          'right-context-oblique-residual-v12-20261027', 'right-context-symmetric-residual-v13-20261027',
          'right-context-signature-residual-v14-20261027')
RUNTIME = ('rank_refinement.py', 'neural_refinement.py', 'word_context_features.py', 'grammar_context_features.py',
           'right_context_grammar_features.py', 'right_context_role_features.py', 'right_context_continuation_features.py',
           'right_context_applied_features.py', 'right_context_left_sequence_features.py',
           'right_context_training_weights.py', 'right_context_signature_weights.py')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_model(name, source_records):
    directory = ROOT / 'build' / name
    frozen_path = directory / 'frozen-model.json'
    raw = frozen_path.read_bytes()
    source_record = source_records[name]
    assert hashlib.sha256(raw).hexdigest() == source_record['recordSha256']
    frozen = json.loads(raw)
    plan = json.loads((directory / 'plan.json').read_bytes())
    assert frozen['qualified'] is False and frozen['modelIdentityIsCompositeManifest'] is True
    assert frozen['modelFeatureSources'] == plan['sourceHashes']
    pairs = (('planSha256', 'plan.json'), ('groupsSha256', 'groups.jsonl'),
             ('vectorsSha256', 'train-vectors.npz'), ('weightsSha256', 'train-group-weights.npy'))
    assert all(sha(directory / file) == frozen[key] for key, file in pairs)
    assert [sha(path) for path in COUNTS] == plan['countsSha256']
    assert all(sha(ASSETS / name) == digest for name, digest in plan['installedAssets'].items())
    for name in RUNTIME:
        relative = 'tools/typing_experiments/' + name
        if relative in frozen['modelFeatureSources']:
            assert sha(ROOT / relative) == frozen['modelFeatureSources'][relative]
    return directory, raw, frozen, plan


inventory.verify(ROOT)
records = {record['model']: record for record in json.loads((ROOT / inventory.INVENTORY).read_bytes())['records']}
lexicon = PymorphyLexicon(cache_size=16384)
tables = [WordContextFeatures.load(path) for path in COUNTS]
grammar = GrammarContextFeatures(lexicon)
right = RightContextGrammarFeatures(lexicon)
role = RightContextRoleFeatures(lexicon)
continuation = RightContextContinuationFeatures(lexicon)
applied = AppliedWordFeatures(lexicon)
sequence = LeftSequenceFeatures(lexicon)
character = neural.load_model(ASSETS / 'ru-ranking-context.bin')


@functools.lru_cache(maxsize=100000)
def base(context, original, serialized):
    candidate = json.loads(serialized)
    return tuple(rank.features(context, original, candidate)
                 + [value for table in tables for value in table.extract(context, original, candidate['text'])]
                 + [neural.context_score(character, context, candidate['text'])]
                 + grammar.extract(context, original, candidate['text']))


@functools.lru_cache(maxsize=100000)
def applied_extra(context, original, previous, candidate):
    return tuple(applied.extract(context, original, previous, candidate))


results = {}
for name in MODELS:
    directory, raw, frozen, plan = load_model(name, records)
    assert lexicon.receipt() == json.loads((directory / 'morphology-receipt.json').read_bytes())
    if name in MODELS[3:]:
        parent = results[MODELS[2]]
        parent_frozen = load_model(MODELS[2], records)[2]
        for key in ('groupsSha256', 'vectorsSha256', 'featureCount', 'candidateRows', 'trainingGroups'):
            assert frozen[key] == parent_frozen[key]
        groups = [json.loads(line) for line in (directory / 'groups.jsonl').read_text().splitlines()]
        weights = np.load(directory / 'train-group-weights.npy', allow_pickle=False)
        parent_weights = np.load(ROOT / 'build' / MODELS[2] / 'train-group-weights.npy', allow_pickle=False)
        assert len(groups) == frozen['trainingGroups'] and len(weights) == len(parent_weights) == frozen['candidateRows']
        policy = TargetSignatureWeights.fit([group['row'] for group in groups], lexicon) if name == MODELS[4] else None
        index = weight_errors = changed_weights = 0
        for group in groups:
            row = group['row']
            size = len(group['candidates'])
            expected_weight = np.float32(policy.weight(row, lexicon) if policy else strong_supervision_weight(row))
            current = weights[index:index + size]
            assert len(current) == size and np.isfinite(current).all()
            weight_errors += int(np.count_nonzero(current != expected_weight))
            changed_weights += int(np.count_nonzero(current != parent_weights[index:index + size]))
            index += size
        assert index == len(weights)
        results[name] = dict(parent, model=name, replayed=False, identicalInputsTo=MODELS[2],
                             weightMismatchRows=weight_errors, weightRowsChangedFromV12=changed_weights)
    else:
        groups = [json.loads(line) for line in (directory / 'groups.jsonl').read_text().splitlines()]
        saved = np.load(directory / 'train-vectors.npz', allow_pickle=False)
        features, labels, ids = saved['features'], saved['labels'], saved['group_ids']
        weights = np.load(directory / 'train-group-weights.npy', allow_pickle=False)
        width = frozen['featureCount']
        assert width == (221 if name == MODELS[0] else 242)
        assert features.shape == (frozen['candidateRows'], width) and len(groups) == frozen['trainingGroups']
        assert len(labels) == len(ids) == len(weights) == len(features)
        index = mismatched = nonfinite = label_errors = 0
        maximum = 0.0
        for gid, group in enumerate(groups):
            row = group['row']
            context = row['leftContext'][-128:]
            weight = 3.0 if (row['kind'] == 'unknown_original' and row['expectedApplied'] != row['applied']
                             and row['applied'] != row['original']) else 1.0
            for candidate_index, candidate in enumerate(group['candidates']):
                prior = base(context, row['original'], json.dumps(candidate, sort_keys=True))
                values = role_revision_features(prior, right, role, context, row['rightContext'], row['applied'], candidate['text'])
                values = list(extend_continuation_features(values, continuation, context, row['rightContext'], candidate['text']))
                values.extend(applied_extra(context, row['original'], row['applied'], candidate['text']))
                if width == 242:
                    values.extend(sequence.extract(context, row['rightContext'], row['applied'], candidate['text']))
                actual = np.asarray(values, dtype=np.float32)
                assert actual.shape == (width,)
                delta = np.abs(actual - features[index])
                nonfinite += int(not np.isfinite(actual).all() or not np.isfinite(delta).all())
                mismatched += int(not np.array_equal(actual, features[index]))
                maximum = max(maximum, float(np.max(delta)))
                label_errors += int(int(labels[index]) != int(candidate_index == group['target']) or
                                    int(ids[index]) != gid or float(weights[index]) != weight)
                index += 1
            if (gid + 1) % 5000 == 0:
                print('model', name, 'groups', gid + 1, 'rows', index, 'mismatched', mismatched, flush=True)
        assert index == len(features)
        results[name] = dict(model=name, groups=len(groups), rows=index, features=width,
                             mismatchedRows=mismatched, maximumDifference=maximum, nonfinite=nonfinite,
                             labelOrWeightErrors=label_errors, replayed=True)
    assert load_model(name, records) == (directory, raw, frozen, plan)
    assert lexicon.receipt() == json.loads((directory / 'morphology-receipt.json').read_bytes())
    print('completed', name, 'mismatched', results[name]['mismatchedRows'], flush=True)
inventory.verify(ROOT)
receipt = dict(scope='historical-training-vectors-only', qualification=False, models=list(results.values()))
with output.open('x') as stream:
    stream.write(json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False) + '\n')
if any(x['mismatchedRows'] or x['nonfinite'] or x['labelOrWeightErrors'] or x.get('weightMismatchRows', 0) for x in results.values()):
    raise SystemExit(1)
