from pathlib import Path
import collections
import functools
import hashlib
import json
import sys

import numpy as np
from catboost import CatBoostRanker, Pool

sys.path.insert(0, 'tools/typing_experiments')
sys.path.insert(0, 'tools/morphology')
import rank_refinement as rank
import neural_refinement as neural
from ranker import PymorphyLexicon
from word_context_features import WordContextFeatures
from grammar_context_features import GrammarContextFeatures
from right_context_grammar_features import RightContextGrammarFeatures
from right_context_role_features import RightContextRoleFeatures, role_revision_features
from right_context_continuation_features import (
    FEATURES, RightContextContinuationFeatures, extend_continuation_features,
)

root = Path(__file__).parent
parent = Path('build/right-context-training-v6-20261027')
assets = Path('app/src/main/assets/smarttyping/experiments')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
load = lambda p: json.loads(Path(p).read_text())


def write(name, value):
    with (root / name).open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


assert root.resolve().is_relative_to((Path.cwd() / 'build').resolve())
frozen = load(parent / 'frozen-model.json')
parent_plan = load(parent / 'plan.json')
assert all(sha(p) == h for p, h in frozen['modelFeatureSources'].items())
assert all(sha(assets / p) == h for p, h in parent_plan['installedAssets'].items())
selection = load(root / 'selection.json')
assert sha(root / 'groups.jsonl') == selection['groupsSha256']
assert all(sha(p) == h for p, h in selection['sourceHashes'].items())
groups = [json.loads(line) for line in (root / 'groups.jsonl').read_text().splitlines()]
families = sorted({f for g in groups for f in g['row'].get('contrastFamilies', [g['row']['family']])})
assert families == frozen['trainingFamilies']
counts = [Path('build/context-ranking-20261025/counts-v3/model-counts.jsonl'),
          Path('build/context-feature-ranker-20261026/tatoeba-train-counts.jsonl')]
assert [sha(p) for p in counts] == parent_plan['countsSha256']
sources = dict(frozen['modelFeatureSources']) | selection['sourceHashes'] | {
    str(p): sha(p) for p in [Path('tools/typing_experiments/right_context_continuation_features.py'), Path(__file__)]}
plan = dict(stage='frozen-before-prefix-fit', purpose='EXPERIMENTAL_TRAINING_ONLY',
            features=FEATURES, layout='178 frozen role fields + 24 completed-continuation fields',
            iterations=128, depth=6, learningRate=.05, seed=25102026, loss='PairLogitPairwise',
            groups=len(groups), groupsSha256=sha(root / 'groups.jsonl'), families=len(families),
            parentModelSha256=frozen['modelSha256'], counterfactualApplied=True,
            qualification=parent_plan['qualification'], sourceHashes=sources,
            countsSha256=parent_plan['countsSha256'], installedAssets=parent_plan['installedAssets'],
            naturalSentencesOrDisclosedFailuresUsedForTraining=False,
            productionSourceOrTimelineIntegrated=False, holdoutScoresRead=False)
write('plan.json', plan)
lexicon = PymorphyLexicon(cache_size=16384)
assert lexicon.receipt() == load(parent / 'morphology-receipt.json')
write('morphology-receipt.json', lexicon.receipt())
tables = [WordContextFeatures.load(path) for path in counts]
grammar = GrammarContextFeatures(lexicon)
right = RightContextGrammarFeatures(lexicon)
role = RightContextRoleFeatures(lexicon)
continuation = RightContextContinuationFeatures(lexicon)
character = neural.load_model(assets / 'ru-ranking-context.bin')


@functools.lru_cache(maxsize=100000)
def base(context, original, serialized):
    c = json.loads(serialized)
    return tuple(rank.features(context, original, c)
                 + [v for table in tables for v in table.extract(context, original, c['text'])]
                 + [neural.context_score(character, context, c['text'])]
                 + grammar.extract(context, original, c['text']))


total = sum(len(g['candidates']) for g in groups)
# Preallocate to avoid retaining hundreds of thousands of Python float tuples.
x = np.empty((total, FEATURES), dtype=np.float32)
y = np.empty(total, dtype=np.int32)
ids = np.empty(total, dtype=np.int32)
offset = 0
for gid, group in enumerate(groups):
    row = group['row']
    context = row['leftContext'][-128:]
    for index, candidate in enumerate(group['candidates']):
        b = base(context, row['original'], json.dumps(candidate, sort_keys=True))
        previous = role_revision_features(b, right, role, context, row['rightContext'], row['applied'], candidate['text'])
        values = extend_continuation_features(previous, continuation, context, row['rightContext'], candidate['text'])
        assert len(values) == FEATURES
        x[offset] = values
        y[offset] = int(index == group['target'])
        ids[offset] = gid
        offset += 1
    if gid % 1000 == 0:
        print('VECTORIZED', gid, flush=True)
assert offset == total and np.isfinite(x).all()
np.savez_compressed(root / 'train-vectors.npz', features=x, labels=y, group_ids=ids)
base.cache_clear()
model = CatBoostRanker(iterations=plan['iterations'], depth=plan['depth'],
                      learning_rate=plan['learningRate'], loss_function=plan['loss'],
                      random_seed=plan['seed'], thread_count=2, verbose=False, allow_writing_files=False)
model.fit(Pool(x, y, group_id=ids))
rank.export_tree(model, root / 'experimental-ranker.bin', FEATURES)
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
assert offset == total and error < 1e-5
assert all(sha(assets / p) == h for p, h in plan['installedAssets'].items())
write('training-diagnostic.json', dict(groups=len(groups), candidateRows=total,
      counts=dict(stats), scenarios=dict(scenarios), scalarVsCatBoostMaxAbsoluteDifference=error,
      trainingOnly=True, independentQualityMeasurement=False))
write('frozen-model.json', dict(stage='frozen-before-diagnostic-scoring', qualified=False,
      featureCount=FEATURES, modelBytes=len(blob), modelSha256=sha(root / 'experimental-ranker.bin'),
      planSha256=sha(root / 'plan.json'), groupsSha256=sha(root / 'groups.jsonl'),
      vectorsSha256=sha(root / 'train-vectors.npz'), selectionSha256=sha(root / 'selection.json'),
      modelFeatureSources=sources, trainingGroups=len(groups), candidateRows=total,
      trainingFamilies=families, installedAssetsUnchanged=True))
print(json.dumps(load(root / 'training-diagnostic.json')), flush=True)
print('MODEL_FROZEN', sha(root / 'experimental-ranker.bin'), flush=True)
