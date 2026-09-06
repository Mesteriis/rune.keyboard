#!/usr/bin/env python3
"""Calibration-only source-bound comparison. No scoring or policy mutation."""
import json
import sys
from pathlib import Path
import unicodedata

REPO = Path(__file__).resolve().parents[4]
PIPELINE = REPO / 'tools/eval/smart-typing-0.3/pipeline'
sys.path.insert(0, str(PIPELINE))
import short_policy_evaluation as policy
import original_applicability as applicability
b = policy.base
ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
OLD = REPO / 'build/smart-typing-0.3/final-product-replay-20260906-review-second-fix-v2/row-evidence.jsonl'
assert b.sha256(OLD) == '6a19850ed122dd782ecde33aaba8087d76c77a34962fda44c055c94f717cfa75'
assert not (ROOT / 'policy-freeze.json').exists() and not (ROOT / 'holdout-scores').exists()
export = b.load_export(ROOT)
report = policy.admit_calibration_report(ROOT, export)


def read_calibration(path):
    # Baseline includes both splits: filter immediately, before labels/metrics.
    selected = []
    with path.open() as stream:
        for line in stream:
            row = json.loads(line)
            if row['split'] != 'calibration':
                continue
            assert row['mode'] in ('ready', 'unavailable')
            selected.append(row)
    counts = b.Counter((r['mode'], r['input']['language'], r['input']['cohort']) for r in selected)
    expected = b.Counter({(mode, lang, cohort): count for mode in ('ready', 'unavailable')
        for lang in b.LANGUAGES for cohort, count in b.COHORT_COUNTS.items()})
    assert counts == expected and len({(r['mode'],r['input']['id']) for r in selected}) == 12000
    return selected


prior = read_calibration(OLD)
current = read_calibration(ROOT / 'row-evidence-calibration.jsonl')
old = {(r['mode'],r['input']['id']):r for r in prior}
assert all(r['input'] == old[(r['mode'],r['input']['id'])]['input'] for r in current)


def request(row):
    value = row['observation'].get('actualModelRequest')
    return None if value is None else {k:value[k] for k in ('prefix','candidateIds','continuations')}


def alternatives(row):
    return (row['observation'].get('actualRequestGeneration') or {}).get('alternatives', [])


def short(row):
    token = row['observation'].get('actualOriginal')
    return isinstance(token,str) and bool(token) and len(unicodedata.normalize('NFC', unicodedata.normalize('NFC',token).lower())) < 5


def view(row):
    obs = row['observation']
    return {'request':request(row), 'alternatives':alternatives(row),
        'finalText':obs['afterBoundary']['text'], 'evaluation':row['evaluation'],
        'modelAdmission':obs.get('modelAdmission'), 'autoEdit':obs.get('autoEdit')}


comparisons = []
for row in current:
    previous = old[(row['mode'],row['input']['id'])]
    req_old, req_new = request(previous), request(row)
    comparisons.append({'id':row['input']['id'], 'language':row['input']['language'],
        'mode':row['mode'], 'typed':row['input']['typed'], 'shortOwnedOriginal':short(row),
        'orderedRequestChanged':req_old != req_new,
        'requestTextSetChanged': (None if req_old is None else sorted(req_old['continuations'])) !=
                                (None if req_new is None else sorted(req_new['continuations'])),
        'generationAlternativesChanged':alternatives(previous) != alternatives(row),
        'finalTextChanged':previous['observation']['afterBoundary']['text'] != row['observation']['afterBoundary']['text'],
        'before':view(previous), 'after':view(row)})


def summary(selected):
    result = {}
    for lang in b.LANGUAGES:
        items = [r for r in selected if r['language'] == lang]
        ids = {r['id'] for r in items}
        result[lang] = {'rows':len(items), **{key:sum(r[key] for r in items) for key in
            ('orderedRequestChanged','requestTextSetChanged','generationAlternativesChanged','finalTextChanged')},
            'before':b.summarize_rows([r for r in prior if r['mode']=='ready' and r['input']['id'] in ids])['overall'],
            'after':b.summarize_rows([r for r in current if r['mode']=='ready' and r['input']['id'] in ids])['overall']}
    return result


ready = [r for r in comparisons if r['mode']=='ready']
groups = applicability.annotate(current)
assert len(groups)==6 and all(g['rows']==2000 for g in groups)
named = {token:[r for r in ready if r['typed']==token] for token in ('горп','ьему','сыо','Чее','oan','teh')}
paths = [Path(__file__), OLD, Path(policy.__file__), Path(b.__file__), Path(applicability.__file__),
    ROOT/'source-freeze.json', ROOT/'export-receipt.json', ROOT/'calibration-report.json',
    ROOT/'row-evidence-calibration.jsonl', ROOT/'calibration-scores/complete.json',
    ROOT/'calibration-scores/scores.jsonl', ROOT/'requests-calibration.jsonl',
    REPO/'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/correction/TokenUnicode.kt']
identities = {b.path_key(path):b.sha256(path) for path in paths}
result = {'scope':'calibration-only changed-candidate-policy review', 'policyChanged':True,
    'thresholdFittingPerformed':False, 'holdoutObservedForSelection':False, 'promotionApproved':False,
    'inputAndToolSha256':identities, 'sourceFreezeSha256':export['sourceFreezeSha256'],
    'allReadyRows':summary(ready),
    'shortOwnedOriginalRows':summary([r for r in ready if r['shortOwnedOriginal']]),
    'changedGenerationRows':summary([r for r in ready if r['generationAlternativesChanged']]),
    'changedRequestRows':summary([r for r in ready if r['orderedRequestChanged']]),
    'longOrNoOwnedWordChangedGenerations':[r['id'] for r in ready if not r['shortOwnedOriginal'] and r['generationAlternativesChanged']],
    'named':named, 'originalApplicability':groups,
    'rawOriginalGatesUnchanged':{lang:{'originalRetention':metrics['originalRetention'],
        'candidatePolicyPointGates':metrics['candidatePolicyPointGates']} for lang,metrics in report['summaries']['ready']['languages'].items()},
    'unavailable':b.summarize_rows([r for r in current if r['mode']=='unavailable'])}
b.write_jsonl(OUT/'comparison.jsonl', comparisons)
b.write_json(OUT/'summary.json', result)
b.write_json(OUT/'commands.json', {'argv':[sys.executable,str(Path(__file__).resolve())], 'modelCalls':0})
# Recheck every input/tool after the join; no mutation is admitted.
assert all(b.sha256(b.resolve_key(key)) == value for key,value in identities.items())
print(json.dumps({'overall':{k:{'rows':v['rows'],'changedRequests':v['orderedRequestChanged'],
    'changedGenerations':v['generationAlternativesChanged'],'changedFinal':v['finalTextChanged']} for k,v in result['allReadyRows'].items()},
    'shortRows':{k:v['rows'] for k,v in result['shortOwnedOriginalRows'].items()},
    'original':groups,'namedCounts':{k:len(v) for k,v in named.items()}},ensure_ascii=False,indent=2))
