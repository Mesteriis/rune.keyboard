from pathlib import Path
import collections
import functools
import hashlib
import json
import math
import shutil
import sys

import numpy as np

sys.path.insert(0, 'tools/typing_experiments')
sys.path.insert(0, 'tools/morphology')
import rank_refinement as rank
import neural_refinement as neural
from ranker import PymorphyLexicon
from word_context_features import WordContextFeatures
from grammar_context_features import GrammarContextFeatures
from right_context_grammar_features import RightContextGrammarFeatures
from right_context_role_features import RightContextRoleFeatures, role_revision_features
from right_context_continuation_features import RightContextContinuationFeatures, extend_continuation_features
from right_context_applied_features import AppliedWordFeatures, FEATURE_NAMES as APPLIED_NAMES
from right_context_left_sequence_features import LeftSequenceFeatures, FEATURES, FEATURE_NAMES

root = Path(__file__).parent
parent = Path('build/right-context-applied-v10-v2-20261027')
assets = Path('app/src/main/assets/smarttyping/experiments')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
load = lambda p: json.loads(Path(p).read_text())
selection = load(root / 'selection.json')
old = load(parent / 'feature-preparation.json')
old_plan = old
assert all(sha(p) == h for p, h in selection['sourceHashes'].items())
assert all(sha(p) == h for p, h in old['sourceHashes'].items())
assert sha(root / 'groups.jsonl') == selection['groupsSha256']
assert sha(parent / 'groups.jsonl') == old['groupsSha256']
assert sha(parent / 'train-vectors.npz') == old['vectorsSha256']
assert all(sha(assets / p) == h for p, h in old_plan['installedAssets'].items())
groups = [json.loads(line) for line in (root / 'groups.jsonl').read_text().splitlines()]
old_groups = [json.loads(line) for line in (parent / 'groups.jsonl').read_text().splitlines()]
old_data = np.load(parent / 'train-vectors.npz')
old_index = {}
offset = 0
for group in old_groups:
    n = len(group['candidates'])
    old_index[group['row']['id']] = group, offset, offset + n
    offset += n
assert offset == len(old_data['features'])
old_x = old_data['features']
lexicon = PymorphyLexicon(cache_size=16384)
assert lexicon.receipt() == load(parent / 'morphology-receipt.json')
shutil.copyfile(parent / 'morphology-receipt.json', root / 'morphology-receipt.json')
counts = [Path('build/context-ranking-20261025/counts-v3/model-counts.jsonl'),
          Path('build/context-feature-ranker-20261026/tatoeba-train-counts.jsonl')]
assert [sha(p) for p in counts] == old_plan['countsSha256']
tables = [WordContextFeatures.load(p) for p in counts]
grammar = GrammarContextFeatures(lexicon)
right = RightContextGrammarFeatures(lexicon)
role = RightContextRoleFeatures(lexicon)
continuation = RightContextContinuationFeatures(lexicon)
applied = AppliedWordFeatures(lexicon)
sequence = LeftSequenceFeatures(lexicon)
character = neural.load_model(assets / 'ru-ranking-context.bin')


@functools.lru_cache(maxsize=100000)
def base(context, original, serialized):
    c = json.loads(serialized)
    return tuple(rank.features(context, original, c)
                 + [v for table in tables for v in table.extract(context, original, c['text'])]
                 + [neural.context_score(character, context, c['text'])]
                 + grammar.extract(context, original, c['text']))


@functools.lru_cache(maxsize=100000)
def extra(context, original, previous, candidate):
    values = applied.extract(context, original, previous, candidate)
    assert len(values) == len(APPLIED_NAMES) and all(math.isfinite(v) for v in values)
    return values


total = sum(len(g['candidates']) for g in groups)
x = np.empty((total, FEATURES), dtype=np.float32)
y = np.empty(total, dtype=np.int32)
ids = np.empty(total, dtype=np.int32)
weights = np.empty(total, dtype=np.float32)
stats = collections.Counter()
offset = 0
for gid, group in enumerate(groups):
    row = group['row']
    n = len(group['candidates'])
    old_entry = old_index.get(row['id'])
    context = row['leftContext'][-128:]
    reuse = old_entry is not None and old_entry[0]['row'] == row and old_entry[0]['candidates'] == group['candidates'] and old_entry[0]['target'] == group['target']
    if reuse:
        x[offset:offset + n, :221] = old_x[old_entry[1]:old_entry[2]]
        stats['unchangedOldGroupsReused'] += 1
    else:
        stats['freshGroups'] += 1
        stats['oldGroupsWithChangedPool'] += old_entry is not None
    for index, candidate in enumerate(group['candidates']):
        if not reuse:
            original_base = base(context, row['original'], json.dumps(candidate, sort_keys=True))
            v178 = role_revision_features(original_base, right, role, context, row['rightContext'], row['applied'], candidate['text'])
            x[offset + index, :202] = extend_continuation_features(v178, continuation, context, row['rightContext'], candidate['text'])
        values = extra(context, row['original'], row['applied'], candidate['text'])
        if not reuse:
            x[offset + index, 202:221] = values
        x[offset + index, 221:] = sequence.extract(context, row['rightContext'], row['applied'], candidate['text'])
        y[offset + index] = int(index == group['target'])
        ids[offset + index] = gid
        weights[offset + index] = 3. if (row['kind'] == 'unknown_original' and row['expectedApplied'] != row['applied'] and row['applied'] != row['original']) else 1.
    offset += n
    if gid % 5000 == 0:
        print('VECTORIZED', gid, flush=True)
assert offset == total and np.isfinite(x).all() and FEATURES == 242
assert stats['unchangedOldGroupsReused'] == len(old_groups) and stats['oldGroupsWithChangedPool'] == 0
assert np.array_equal(x[:len(old_x), :221], old_x)
assert np.array_equal(weights[:len(old_x)], np.load(parent/'train-group-weights.npy'))
np.savez_compressed(root / 'train-vectors.npz', features=x, labels=y, group_ids=ids)
np.save(root / 'train-group-weights.npy', weights)
new_groups = [g for g in groups if g['row']['id'] not in old_index]
sources = dict(selection['sourceHashes']) | {str(p): sha(p) for p in (
    Path('tools/typing_experiments/right_context_applied_features.py'),
    Path('tools/typing_experiments/right_context_left_sequence_features.py'), Path(__file__))}
report = dict(purpose='PREPARED_INPUTS_ONLY_NO_NEW_MODEL_FIT', features=FEATURES, previousFeatures=221,
              residualFeatures=FEATURES - 146, appendedFeatureNames=list(FEATURE_NAMES),
              groups=len(groups), candidateRows=total, reuse=dict(stats),
              newRoleGroups=len(new_groups), newRoleFamilies=sorted({g['row']['family'] for g in new_groups}),
              newRoleScenarios=dict(collections.Counter(g['row']['scenario'] for g in new_groups)),
              sourceHashes=sources, groupsSha256=sha(root / 'groups.jsonl'),
              vectorsSha256=sha(root / 'train-vectors.npz'), weightsSha256=sha(root / 'train-group-weights.npy'),
              previousFrozenModelSha256=sha(parent / 'feature-preparation.json'), trainingFamilies=sorted({f for g in groups for f in g['row'].get('contrastFamilies', [g['row']['family']])}),
              installedAssets=old_plan['installedAssets'], countsSha256=old_plan['countsSha256'],
              noNaturalFailuresUsedForSupervision=True, modelTrained=False, productionQualified=False)
with (root / 'feature-preparation.json').open('x') as stream:
    json.dump(report, stream, ensure_ascii=False, indent=2)
print(json.dumps({k: v for k, v in report.items() if k not in {'sourceHashes', 'installedAssets'}}), flush=True)
