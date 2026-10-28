"""Full-vector math check of the original frozen CatBoost references.

Requires original private build receipts/exports; does not replace their three
original test modules or reproduce candidate generation/training.
"""

def _require(condition, code):
    if not condition:
        raise ValueError(code)
import argparse
import historical_model_sources as source_audit
from pathlib import Path
import hashlib, json, sys
import numpy as np
from catboost import CatBoostClassifier, CatBoostRanker
root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / 'tools/typing_experiments'))
import train
from test_models import tree_score
import rank_refinement as rank
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--historical-build', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
archive = args.historical_build.resolve()
destination = args.output
if destination.exists():
    raise ValueError('FRESH_NUMERIC_PARITY_OUTPUT_REQUIRED')
source_audit.audit(historical_build=archive)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def require_reference(path, expected):
    if sha(path) != expected:
        raise ValueError('HISTORICAL_REFERENCE_IDENTITY:' + path.name)
require_reference(archive / 'typing-experiments/catboost-reference.cbm', 'f79649eab727b90ae6da22e8c873a12d2f8ac9c72c0e5db6cda68a8660a25891')
require_reference(root / 'tools/typing_experiments/baseline/ru-ranker.bin', 'bc7542fa35ab615718ee636bd530868441101a4cb89d86aef26b3af1038d8c43')
require_reference(archive / 'typing-refinement/ranker/pairwise.cbm', '2970cbe699916c45b516e3fc42fc08eda443adc8c425869b5eb82a20c1ee5d23')
require_reference(archive / 'typing-refinement/ranker/pairwise.bin', 'f3ac83997946b97b57f410f0955a9a479a72453f4c68ed4f473c1afded583648')
verified = {}
for name in ['morphology-public-export-v3', 'typing-refinement/candidates-v2']:
    receipt = json.loads((archive / name / 'receipt.json').read_text())
    oldbase = next(iter(receipt['files'])).split('/build/' + name + '/')[0]
    for raw, digest in receipt['files'].items():
        path = archive / raw.removeprefix(oldbase + '/build/')
        _require(sha(path) == digest, 'HISTORICAL_NUMERIC_INPUT_IDENTITY')
        verified[str(path.relative_to(archive))] = digest
legacy = archive / 'morphology-public-export-v3'
rows = [json.loads(s) for s in (legacy / 'rows.jsonl').read_text().splitlines()]
obs = [json.loads(s) for s in (legacy / 'observations.jsonl').read_text().splitlines()]
corpus = root / 'tools/eval/smart-typing-0.3/qualification-v2/corpus'
cm = json.loads((corpus / 'manifest.json').read_text())
_require(cm['containsPersonalMessages'] is False, 'HISTORICAL_NUMERIC_INPUT_IDENTITY')
_require(sha(corpus / 'spelling-ru.jsonl') == cm['files']['spelling-ru.jsonl'], 'HISTORICAL_NUMERIC_INPUT_IDENTITY')
source = {r['id']: r for r in map(json.loads, (corpus / 'spelling-ru.jsonl').read_text().splitlines())}
_require(len(rows) == len(obs), 'HISTORICAL_NUMERIC_INPUT_IDENTITY')
public = []
for i, (r, o) in enumerate(zip(rows, obs)):
    _require(o['index'] == i and o['generation']['original'] == r['typed'], 'HISTORICAL_NUMERIC_INPUT_IDENTITY')
    if r['id'] in source:
        _require(r == source[r['id']], 'HISTORICAL_NUMERIC_INPUT_IDENTITY')
        public.append((r, o))
fit = {r['template'] for r, o in public if r['split'] == 'calibration'}
holdout = {r['template'] for r, o in public if r['split'] == 'holdout'}
_require(fit and holdout and (not fit & holdout), 'HISTORICAL_NUMERIC_INPUT_IDENTITY')
vectors = np.asarray([train.features(r['prefix'], r['typed'], c) for r, o in public for c in o['generation']['alternatives']])
_require(len(vectors) > 0, 'HISTORICAL_NUMERIC_INPUT_IDENTITY')
modelpath = archive / 'typing-experiments/catboost-reference.cbm'
model = CatBoostClassifier().load_model(str(modelpath))
reference = model.predict(vectors, prediction_type='RawFormulaVal')
blob = (root / 'tools/typing_experiments/baseline/ru-ranker.bin').read_bytes()
actual = np.asarray([tree_score(blob, v) for v in vectors])
error = float(np.abs(reference - actual).max())
_require(error < 1e-05, 'HISTORICAL_TREE_PARITY')
report = {'baseline': {'publicRows': len(public), 'vectors': len(vectors), 'maxAbsoluteError': error, 'referenceSha256': sha(modelpath), 'exportSha256': hashlib.sha256(blob).hexdigest()}}
data = archive / 'typing-refinement/data'
manifest = json.loads((data / 'manifest.json').read_text())
_require(sha(data / 'manifest.json') == '20b32e840b890aab726fabea30c6409fce058d0c9ba3dd64d603aaaa24475ce7', 'HISTORICAL_NUMERIC_INPUT_IDENTITY')
binding = json.loads((archive / 'typing-refinement/verified-observations/manifest.json').read_text())
_require(binding['dataManifestSha256'] == sha(data / 'manifest.json'), 'HISTORICAL_NUMERIC_INPUT_IDENTITY')
_require(binding['exportReceiptSha256'] == sha(archive / 'typing-refinement/candidates-v2/receipt.json'), 'HISTORICAL_NUMERIC_INPUT_IDENTITY')
exportrows = [json.loads(s) for s in (archive / 'typing-refinement/candidates-v2/rows.jsonl').read_text().splitlines()]
exportobs = [json.loads(s) for s in (archive / 'typing-refinement/candidates-v2/observations.jsonl').read_text().splitlines()]
byid = {r['id']: (r, o) for r, o in zip(exportrows, exportobs)}
for part in ['train', 'dev']:
    p = archive / 'typing-refinement/verified-observations' / f'{part}.jsonl'
    _require(sha(p) == binding['partitions'][part], 'HISTORICAL_NUMERIC_INPUT_IDENTITY')
    rp = data / f'{part}-rows.jsonl'
    _require(sha(rp) == manifest['files'][rp.name], 'HISTORICAL_NUMERIC_INPUT_IDENTITY')
    original = [json.loads(s) for s in rp.read_text().splitlines()]
    records = [json.loads(s) for s in p.read_text().splitlines()]
    _require([x['row'] for x in records] == original, 'HISTORICAL_NUMERIC_INPUT_IDENTITY')
    _require(all(((x['row'], x['observation']) == byid[x['row']['id']] for x in records)), 'HISTORICAL_NUMERIC_INPUT_IDENTITY')
    groups = rank.load_groups(p)
    if part == 'train':
        _require(len(groups) == 4942, 'HISTORICAL_NUMERIC_INPUT_IDENTITY')
        continue
    vectors = np.asarray([rank.features(r['prefix'], r['typed'], c) for r, cs, _ in groups for c in cs])
    modelpath = archive / 'typing-refinement/ranker/pairwise.cbm'
    model = CatBoostRanker().load_model(str(modelpath))
    expected = model.predict(vectors)
    blob = (archive / 'typing-refinement/ranker/pairwise.bin').read_bytes()
    actual = np.asarray([rank.tree_score(blob, v) for v in vectors])
    error = float(np.abs(expected - actual).max())
    _require(error < 1e-05, 'HISTORICAL_TREE_PARITY')
    report['refinement'] = {'devGroups': len(groups), 'trainGroups': 4942, 'vectors': len(vectors), 'maxAbsoluteError': error, 'referenceSha256': sha(modelpath), 'exportSha256': hashlib.sha256(blob).hexdigest()}
report['verifiedExportFiles'] = verified
report['scope'] = 'Numeric full-vector parity; separate source recovery is required, not candidate-generation reproduction or training.'
with destination.open('x') as stream:
    stream.write(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k in ['baseline', 'refinement']}, indent=2))
