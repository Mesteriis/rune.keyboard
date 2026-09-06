from pathlib import Path
import hashlib, json
from collections import Counter

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'build/smart-typing-0.3/final-product-replay-20260906-review-second-fix-v2/row-evidence.jsonl'
OUT = Path(__file__).resolve().parent
TARGETS = {'автокрекция': 'автокоррекция', 'арфография': 'орфография', 'сообшение': 'сообщение',
           'причём': 'причём', 'kubectl': 'kubectl', 'AIGate': 'AIGate', 'teh': 'the',
           'recieve': 'receive', 'adress': 'address', 'mensage': 'mensaje', 'correcion': 'corrección'}
rows = []
digest = hashlib.sha256()
with SOURCE.open('rb') as source:
    for line in source:
        digest.update(line)
        value = json.loads(line)
        source_input = value['input']
        typed = source_input['typed']
        if typed not in TARGETS:
            continue
        observed = value['observation']
        expected = TARGETS[typed]
        generation = observed['actualRequestGeneration']
        alternatives = [c['text'] for c in generation['alternatives']] if generation is not None else []
        shown = [c['text'] for c in observed['candidateView']['candidates']]
        after = observed['afterBoundary']['text']
        desired = source_input['prefix'] + ' ' + expected + ' '
        actual_auto = value['evaluation']['spellingAutoEdit']
        if actual_auto:
            outcome = 'automatic_target' if after == desired else 'incorrect_automatic_change'
        elif typed == expected and after == desired:
            outcome = 'preserved_target'
        elif expected in shown:
            outcome = 'suggestion_only'
        else:
            outcome = 'target_not_displayed'
        rows.append({'id': source_input['id'], 'language': source_input['language'],
                     'split': value['split'], 'mode': value['mode'], 'prefix': source_input['prefix'],
                     'typed': typed, 'target': expected, 'completion': generation['completion'] if generation is not None else None,
                     'states': generation['inspectedStates'] if generation is not None else None,
                     'verifiedTerminals': generation['verifiedTerminals'] if generation is not None else None,
                     'alternatives': alternatives, 'displayed': shown, 'afterBoundary': after,
                     'outcome': outcome, 'modelAdmission': observed['modelAdmission'],
                     'undoExact': value['evaluation']['undoExact'], 'evaluation': value['evaluation'],
                     'sourceLineSha256': hashlib.sha256(line).hexdigest()})
assert set(r['typed'] for r in rows) == set(TARGETS)
assert len(rows) == 34 and len({(r['id'], r['mode']) for r in rows}) == 34
assert all({r['mode'] for r in rows if r['id'] == row['id']} == {'ready', 'unavailable'} for row in rows)
assert all(r['split'] == 'calibration' for r in rows)
rows.sort(key=lambda r: (r['language'], r['typed'], r['mode'], r['id']))
(OUT / 'named-rows.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in rows))
report = {'source': str(SOURCE.relative_to(ROOT)), 'sourceSha256': digest.hexdigest(),
          'selection': 'Every row whose exact typed token is one of the eleven specification names; all languages and both model modes retained.',
          'rows': len(rows), 'uniqueExamples': len(rows)//2, 'allExamplesAreCalibration': True,
          'newScoringCalls': 0, 'newTypingReplayCalls': 0,
          'byMode': {m: dict(Counter(r['outcome'] for r in rows if r['mode'] == m)) for m in ['ready', 'unavailable']}}
(OUT / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
print(json.dumps(report, ensure_ascii=False))
