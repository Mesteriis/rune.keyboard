"""Replay recorded context-model training vectors; do not train or qualify models."""
import argparse
import functools
import hashlib
import json
from pathlib import Path
import sys

if not __debug__:
    raise RuntimeError('CONTEXT_REPLAY_REQUIRES_ASSERTIONS')
ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
output = args.output.resolve()
if Path.cwd().resolve() != ROOT or not output.is_relative_to(ROOT / 'build') or output.exists():
    raise ValueError('CONTEXT_REPLAY_OUTPUT_OR_WORKDIR')

import numpy as np
sys.path.insert(0, 'tools/typing_experiments')
import rank_refinement as rank
import neural_refinement as neural
from word_context_features import WordContextFeatures
from grammar_context_features import GrammarContextFeatures
from right_context_grammar_features import RightContextGrammarFeatures
from right_context_revision_features import revision_features
from right_context_role_features import RightContextRoleFeatures, role_revision_features
from right_context_continuation_features import RightContextContinuationFeatures, extend_continuation_features
sys.path.insert(0, 'tools/morphology')
from ranker import PymorphyLexicon

ASSETS = ROOT / 'app/src/main/assets/smarttyping/experiments'
COUNTS = [ROOT / 'build/context-ranking-20261025/counts-v3/model-counts.jsonl',
          ROOT / 'build/context-feature-ranker-20261026/tatoeba-train-counts.jsonl']
NAMES = ('v1', 'v2', 'v3', 'v4', 'v5', 'v6', 'v7', 'v8')
ALIASES = {'v6': 'v5', 'v8': 'v7'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_record(name):
    directory = ROOT / ('build/right-context-training-20261027' if name == 'v1'
                        else 'build/right-context-training-' + name + '-20261027')
    frozen = json.loads((directory / 'frozen-model.json').read_bytes())
    plan = json.loads((directory / 'plan.json').read_bytes())
    assert frozen['qualified'] is False
    for key, filename in (('planSha256', 'plan.json'), ('groupsSha256', 'groups.jsonl'),
                          ('vectorsSha256', 'train-vectors.npz')):
        assert sha(directory / filename) == frozen[key]
    assert plan['sourceHashes'] == frozen['modelFeatureSources']
    assert all(sha(ROOT / name) == digest for name, digest in plan['sourceHashes'].items())
    assert all(sha(ASSETS / name) == digest for name, digest in plan['installedAssets'].items())
    assert [sha(path) for path in COUNTS] == plan['countsSha256']
    return directory, frozen, plan


def replay(name, directory, frozen, lexicon):
    assert lexicon.receipt() == json.loads((directory / 'morphology-receipt.json').read_bytes())
    groups = [json.loads(line) for line in (directory / 'groups.jsonl').read_text().splitlines()]
    saved = np.load(directory / 'train-vectors.npz', allow_pickle=False)
    expected = saved['features']
    width = frozen['featureCount']
    assert expected.shape == (frozen['candidateRows'], width) and len(groups) == frozen['trainingGroups']
    assert width == (163 if name in ('v1', 'v2', 'v3') else 178 if name in ('v4', 'v5') else 202)
    tables = [WordContextFeatures.load(path) for path in COUNTS]
    grammar = GrammarContextFeatures(lexicon)
    right = RightContextGrammarFeatures(lexicon)
    role = RightContextRoleFeatures(lexicon) if width >= 178 else None
    continuation = RightContextContinuationFeatures(lexicon) if width == 202 else None
    character = neural.load_model(ASSETS / 'ru-ranking-context.bin')

    @functools.lru_cache(maxsize=100000)
    def base(context, original, serialized):
        candidate = json.loads(serialized)
        return tuple(rank.features(context, original, candidate)
                     + [value for table in tables for value in table.extract(context, original, candidate['text'])]
                     + [neural.context_score(character, context, candidate['text'])]
                     + grammar.extract(context, original, candidate['text']))

    index = mismatched = nonfinite = 0
    maximum = 0.0
    for gid, group in enumerate(groups):
        row = group['row']
        context = row['leftContext'][-128:]
        for candidate in group['candidates']:
            prior = base(context, row['original'], json.dumps(candidate, sort_keys=True))
            if width == 163:
                values = revision_features(prior, right, row['rightContext'], row['applied'], candidate['text'])
            else:
                values = role_revision_features(prior, right, role, context, row['rightContext'], row['applied'], candidate['text'])
                if width == 202:
                    values = extend_continuation_features(values, continuation, context, row['rightContext'], candidate['text'])
            values = np.asarray(values, dtype=np.float32)
            assert values.shape == (width,)
            delta = np.abs(values - expected[index])
            nonfinite += int(not np.isfinite(values).all() or not np.isfinite(delta).all())
            mismatched += int(not np.array_equal(values, expected[index]))
            maximum = max(maximum, float(np.max(delta)))
            index += 1
        if (gid + 1) % 5000 == 0:
            print('model', name, 'groups', gid + 1, 'rows', index, 'mismatched', mismatched, flush=True)
    assert index == len(expected) and lexicon.receipt() == json.loads((directory / 'morphology-receipt.json').read_bytes())
    return dict(model=name, groups=len(groups), rows=index, features=width, mismatchedRows=mismatched,
                maximumDifference=maximum, nonfinite=nonfinite, replayed=True)


lexicon = PymorphyLexicon(cache_size=16384)
results = {}
for name in NAMES:
    directory, frozen, plan = load_record(name)
    if name in ALIASES:
        parent_directory, parent_frozen, _ = load_record(ALIASES[name])
        assert frozen['groupsSha256'] == parent_frozen['groupsSha256']
        assert frozen['vectorsSha256'] == parent_frozen['vectorsSha256']
        assert all(frozen[key] == parent_frozen[key] for key in ('featureCount', 'candidateRows', 'trainingGroups'))
        assert lexicon.receipt() == json.loads((directory / 'morphology-receipt.json').read_bytes())
        prior = results[ALIASES[name]]
        results[name] = dict(prior, model=name, replayed=False, identicalInputsTo=ALIASES[name])
    else:
        results[name] = replay(name, directory, frozen, lexicon)
    assert load_record(name) == (directory, frozen, plan)
    print('completed', name, 'mismatched', results[name]['mismatchedRows'], flush=True)
receipt = dict(scope='historical-training-vectors-only', qualification=False, models=list(results.values()))
with output.open('x') as stream:
    stream.write(json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False) + '\n')
if any(item['mismatchedRows'] or item['nonfinite'] for item in results.values()):
    raise SystemExit(1)
