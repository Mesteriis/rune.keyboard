#!/usr/bin/env python3
"""Full current-controller diagnostic on revealed holdout; frozen numeric payloads only."""
from pathlib import Path
import base64
from collections import Counter
import hashlib
import importlib.util
import json
import subprocess
import sys
import time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
REPO = OUT.parents[3]
ORIGINAL = ROOT / 'canonical-controller-postfix'
CORPUS = REPO / 'tools/eval/smart-typing-0.3'
LEGACY = CORPUS / 'pipeline/results/2026-09-03-product-holdout'

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n')

def jsonl(name, rows):
    (OUT / name).write_text(''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n' for r in rows))

def load_lines(path):
    return [json.loads(line) for line in path.open()]

def main():
    assert not (OUT / 'execution-receipt.json').exists(), 'Preserve completed evidence'
    started = time.monotonic()
    original = json.loads((ORIGINAL / 'execution-receipt.json').read_text())
    bound = dict(original['inputHashes'])
    bound[str(ORIGINAL / 'execution-receipt.json')] = sha(ORIGINAL / 'execution-receipt.json')
    bound.update({str(ORIGINAL / name): digest for name, digest in original['artifacts'].items()})
    # This run is authorized for one explicit production source delta after the
    # prior canonical fix. Preserve all previous artifacts; bind the newly compiled
    # planner separately, with every other current input required unchanged.
    changed_planner = str(REPO / 'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/punctuation/MechanicalPunctuationPlanner.kt')
    planner_transition = {'path': changed_planner, 'beforeSha256': bound[changed_planner],
        'currentSha256': sha(Path(changed_planner))}
    for name, digest in bound.items():
        if name != changed_planner:
            assert sha(Path(name)) == digest, ('Unexpected current-source or prior-artifact drift', name)
    bound[changed_planner] = planner_transition['currentSha256']
    write('mechanical-source-transition.json', {'authorizedOnlyProductionDelta': planner_transition,
        'priorCanonicalReceiptSha256': sha(ORIGINAL / 'execution-receipt.json'),
        'sameLabelsAndExactFreshScoreAdmissionRequired': True,
        'historicalVerifierNotModifiedOrUsedAsCurrentQualification': True})
    fresh = ROOT / 'native-scores'
    run = json.loads((fresh / 'run-input.json').read_text())
    complete = json.loads((fresh / 'complete.json').read_text())
    assert all(complete[key] == value for key, value in run.items())
    assert complete['scope'] == 'current-native-numeric-compatibility-replay'
    assert complete['responses'] == complete['requests'] == 2940 and complete['runtimeErrors'] == 14
    assert complete['thresholdFittingPerformed'] is False and complete['canonicalCaseProvider'] == 'EMPTY'
    assert sha(fresh / 'scores.jsonl') == complete['scoresSha256'] == 'c0b93073e00f074cbb88949163bfcc35c10fc408f167b0971739590761377af7'
    for name, digest in complete['inputs'].items():
        assert sha(REPO / name) == digest, ('Fresh scoring input drift', name)
        bound[str(REPO / name)] = digest
    for path in (fresh / 'run-input.json', fresh / 'complete.json', fresh / 'scores.jsonl'):
        bound[str(path)] = sha(path)
    spec = importlib.util.spec_from_file_location('bound_evaluator', CORPUS / 'evaluate.py')
    ev = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ev)
    corpus_manifest = json.loads((CORPUS / 'manifest.json').read_text())
    rows = []
    for name in ('spelling-ru.jsonl', 'spelling-en.jsonl', 'spelling-es.jsonl', 'protected-tokens.jsonl'):
        path = CORPUS / name
        assert sha(path) == corpus_manifest['files'][name]
        bound[str(path)] = sha(path)
        rows += [r for r in load_lines(path) if r['task'] == 'spelling' and r['split'] == 'holdout']
    assert len(rows) == len({r['id'] for r in rows}) == 6000
    assert Counter((r['language'], r['cohort']) for r in rows) == {
        (lang, cohort): count for lang in ('en', 'ru', 'es')
        for cohort, count in (('typo', 1000), ('correct', 700), ('protected', 300))}
    # Read legacy metadata/report only. No historical score cache is read or executed.
    archive_manifest = json.loads((LEGACY / 'manifest.json').read_text())
    for name in ('candidate-provenance.json', 'report.json', 'report-provenance.json'):
        path = LEGACY / name
        assert sha(path) == archive_manifest['files'][name]
        bound[str(path)] = sha(path)
    bound[str(LEGACY / 'manifest.json')] = sha(LEGACY / 'manifest.json')
    legacy_report = json.loads((LEGACY / 'report.json').read_text())
    legacy_provenance = json.loads((LEGACY / 'report-provenance.json').read_text())
    assert sha(LEGACY / 'report.json') == legacy_provenance['reportSha256']
    old_candidate_receipt = json.loads((LEGACY / 'candidate-provenance.json').read_text())
    comparison = json.loads((ROOT / 'holdout/comparison.json').read_text())
    assert comparison['historicalReceiptSha256'] == sha(LEGACY / 'candidate-provenance.json')
    cal = json.loads((ROOT / 'calibration/provenance.json').read_text())
    assert sha(ROOT / 'calibration/provenance.json') == comparison['currentCalibrationReceiptSha256']
    assert sha(ROOT / 'calibration/generator.jar') == comparison['currentBinarySha256'] == cal['binary']
    # The scored ordinary export predates the explicit source fix. Preserve its source
    # binding as historical evidence; do not pretend it was compiled from changed sources.
    # Current compiled inputs are independently bound by the fresh post-fix canonical receipt.
    source_changes = {}
    changed_generator = 'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/lexicon/CandidateGenerator.kt'
    for name, digest in cal['sources'].items():
        current_digest = sha(REPO / name)
        if name == changed_generator:
            source_changes[name] = {'scoredExportSourceSha256': digest, 'currentCompiledSourceSha256': current_digest}
        else:
            assert current_digest == digest, ('Unexpected ordinary export source drift', name)
        bound[str(REPO / name)] = current_digest
    write('scored-export-source-transition.json', {'sourceChanges': source_changes,
        'historicalExportProvenanceSha256': sha(ROOT / 'calibration/provenance.json'),
        'currentCanonicalReceiptSha256': sha(ORIGINAL / 'execution-receipt.json'),
        'newLivePayloadsMustMatchScoredRequestsExactly': True,
        'historicalVerifierNotModifiedOrBypassedAsQualification': True})
    for name, key in [('inputs.tsv', 'inputs'), ('actual.tsv', 'actual'), ('candidates.jsonl', 'candidates')]:
        path = ROOT / 'holdout' / name
        assert sha(path) == old_candidate_receipt[key]
        bound[str(path)] = sha(path)
    generated = load_lines(ROOT / 'holdout/candidates.jsonl')
    assert [g['id'] for g in generated] == [r['id'] for r in rows]
    requests = [dict(id=r['id'], split='holdout', prefix=r['prefix'] + ' ',
        candidates=[g['original']] + [c['text'] for c in g['alternatives']])
        for r, g in zip(rows, generated) if g['alternatives']]
    assert len(requests) == 2940 and ev.digest(requests) == complete['identity']['corpusSha256']
    cache = load_lines(fresh / 'scores.jsonl')
    assert cache[0] == {'cacheIdentity': complete['identity']}
    scores = {r['id']: r for r in cache[1:]}
    assert len(scores) == len(cache) - 1 == len(requests)
    assert set(scores) == {r['id'] for r in requests}
    for request in requests:
        ev.validate_response(request, scores[request['id']])
    assert sum('error' in r for r in scores.values()) == 14
    request_by_id = {r['id']: r for r in requests}
    jsonl('frozen-inputs.jsonl', rows)
    jsonl('verified-scored-requests.jsonl', requests)
    jsonl('fresh-responses.jsonl', cache)
    write('score-binding.json', {'verified': True, 'freshRunSha256': sha(fresh / 'run-input.json'),
        'freshCompleteSha256': sha(fresh / 'complete.json'), 'freshScoresSha256': sha(fresh / 'scores.jsonl'),
        'requestDigest': ev.digest(requests), 'identity': complete['identity'], 'requests': len(requests),
        'errors': [r for r in scores.values() if 'error' in r], 'historicalScoreCacheRead': False,
        'matchingControllerPayloadStillRequired': True})
    enc = lambda value: base64.b64encode(value.encode()).decode('ascii')
    with (OUT / 'inputs.tsv').open('w', encoding='ascii') as stream:
        for index, row in enumerate(rows):
            request = request_by_id.get(row['id']); response = scores.get(row['id'])
            fields = [str(index), enc(row['id']), row['language'], enc(row['prefix']), enc(row['typed'])]
            fields += ([enc(request['prefix']), ','.join(map(enc, request['candidates'])),
                        ','.join(map(str, range(len(request['candidates']))))] if request else ['NONE'] * 3)
            fields += ['ERROR' if response and 'error' in response else 'OK' if response else 'NONE',
                response.get('error', 'NONE') if response else 'NONE',
                ';'.join(f'{s["id"]},{s["sumLogProbability"]},{s["scoredTokenCount"]}' for s in response['scores'])
                if response and 'scores' in response else 'NONE']
            stream.write('\t'.join(fields) + '\n')
    commands = json.loads((ORIGINAL / 'commands.json').read_text())
    compile_cmd = commands['compile'][:]
    compile_cmd[compile_cmd.index('-d') + 1] = str(OUT / 'product-controller.jar')
    compile_cmd[-1] = str(OUT / 'ProductControllerDiagnostic.kt')
    runtime_cmd = commands['execute'][:]
    runtime_cmd[runtime_cmd.index('-cp') + 1] = runtime_cmd[runtime_cmd.index('-cp') + 1].replace(
        str(ORIGINAL / 'canonical-controller.jar'), str(OUT / 'product-controller.jar'))
    runtime_cmd[-3] = 'io.github.mesteriis.rune.keyboard.smarttyping.session.ProductControllerDiagnostic'
    runtime_cmd[-2] = str(OUT / 'inputs.tsv')
    write('commands.json', {'compile': compile_cmd, 'execute': runtime_cmd,
        'runtimeClasspath': runtime_cmd[runtime_cmd.index('-cp') + 1]})
    for path in [OUT / 'ProductControllerDiagnostic.kt', Path(__file__), OUT / 'inputs.tsv',
                 OUT / 'frozen-inputs.jsonl', OUT / 'verified-scored-requests.jsonl', OUT / 'fresh-responses.jsonl',
                 ROOT / 'calibration/generator.jar']:
        bound[str(path)] = sha(path)
    write('input-binding.json', {'hashes': bound, 'sourceHeadBefore': subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(), 'noQualificationOverride': True})
    print('FRESH_CACHE_AND_EXACT_REQUEST_IDENTITY_VERIFIED', flush=True)
    with (OUT / 'compile.log').open('wb') as log:
        subprocess.run(compile_cmd, stdout=log, stderr=log, timeout=180, check=True)
    print('ACTUAL_CURRENT_PRODUCT_HOST_COMPILE_PASS', flush=True)
    with (OUT / 'actual.jsonl').open('wb') as data, (OUT / 'run.log').open('wb') as log:
        subprocess.run(runtime_cmd, stdout=data, stderr=log, timeout=600, check=True)
    outputs = load_lines(OUT / 'actual.jsonl')
    assert len(outputs) == 6000 and [o['id'] for o in outputs] == [r['id'] for r in rows]
    evidence = []
    for row, observation in zip(rows, outputs):
        successful = observation['status'] == 'COMPLETE'
        auto = observation.get('autoEdit')
        generation = (auto or {}).get('correctionGeneration')
        canonical = bool(generation and any(c['kind'] == 'CANONICAL_CASE' for c in generation['alternatives']))
        boundary_changed = observation.get('boundaryChangedBeyondInsertedSpace', False)
        final = observation.get('afterBoundary', {}).get('text')
        original = row['prefix'] + ' ' + row['typed']
        full_changed = successful and final != original + ' '
        expected = row['prefix'] + ' ' + row['expectedSpelling'] + ' ' if row['cohort'] == 'typo' else None
        correct = bool(row['cohort'] == 'typo' and not row['noAuto'] and final == expected)
        label = dict(negative=row['cohort'] != 'typo', fullFinalTextChanged=full_changed,
            boundaryAutoEdit=bool(auto), boundaryChanged=boundary_changed, canonicalAutoEdit=bool(auto) and canonical,
            spellingAutoEdit=bool(auto) and generation is not None and not canonical,
            mechanicalTypingChange=observation.get('inputChangedByTyping', False),
            mechanicalBoundaryAutoEdit=bool(auto) and generation is None,
            correctFinalReplacement=correct, expectedFinalText=expected,
            boundaryUndoExact=observation.get('restoredBeforeBoundaryExactly', False))
        evidence.append({'input': row, 'observation': observation, 'evaluation': label})
    jsonl('row-evidence.jsonl', evidence)
    def metrics(items, key):
        changed = [r for r in items if r['evaluation'][key]]
        correct = sum(r['evaluation']['correctFinalReplacement'] for r in changed)
        negative = sum(r['evaluation']['negative'] for r in items)
        false_changes = sum(r['evaluation']['negative'] for r in changed)
        return dict(rows=len(items), automaticReplacements=len(changed), correctReplacements=correct,
            incorrectReplacements=len(changed)-correct, negativeRows=negative,
            precision=ev.rate(correct, len(changed)), falseChange=ev.rate(false_changes, negative),
            coverage=ev.rate(len(changed), len(items)), abstention=ev.rate(len(items)-len(changed), len(items)),
            exactBoundaryUndoAmongChanged=sum(r['evaluation']['boundaryUndoExact'] for r in changed))
    def summarize(items):
        return {'rows': len(items), 'statusCounts': dict(Counter(r['observation']['status'] for r in items)),
            'modelAdmissionCounts': dict(Counter(r['observation'].get('modelAdmission', 'ROW_ERROR') for r in items)),
            'allFinalTextChanges': metrics(items, 'fullFinalTextChanged'),
            'allBoundaryAutoEdits': metrics(items, 'boundaryAutoEdit'),
            'ordinarySpellingBoundaryAutoEdits': metrics(items, 'spellingAutoEdit'),
            'canonicalBoundaryAutoEdits': metrics(items, 'canonicalAutoEdit'),
            'mechanicalTypingChanges': sum(r['evaluation']['mechanicalTypingChange'] for r in items),
            'mechanicalBoundaryAutoEdits': sum(r['evaluation']['mechanicalBoundaryAutoEdit'] for r in items),
            'allRowsExactBeforeBoundaryRestore': sum(r['evaluation']['boundaryUndoExact'] for r in items)}
    summary = {'scope': 'actual-current-full-product-controller-diagnostic-on-revealed-frozen-holdout',
        'releaseQualified': False, 'thresholdFittingPerformed': False, 'labelsChanged': False,
        'modelCalls': 0, 'oldScoreCacheReads': 0, 'qualificationOverride': False,
        'sourceSettings': 'CURRENT / KeyboardSettings.DEFAULT / HIGH_CONFIDENCE / fixed default95',
        'languages': {lang: summarize([r for r in evidence if r['input']['language'] == lang]) for lang in ('en','ru','es')},
        'overall': summarize(evidence), 'legacyFrozenModelAssisted': {
            lang: legacy_report['languages'][lang]['modelAssisted'] for lang in ('en','ru','es')},
        'legacyReportBinding': {'sha256': sha(LEGACY / 'report.json'), 'path': str(LEGACY / 'report.json')},
        'refusedOrFailedModelAdmissions': [{'id': r['input']['id'],
            'admission': r['observation'].get('modelAdmission'), 'mismatches': r['observation'].get('payloadMismatches'),
            'freshCacheStatus': r['observation'].get('freshCacheStatus'), 'error': r['observation'].get('freshCacheError')}
            for r in evidence if r['observation'].get('modelAdmission', '').startswith(('REFUSED', 'MATCHED_SCORING_ERROR'))],
        'harnessErrors': [{'id': r['input']['id'], 'error': r['observation'].get('error')} for r in evidence
                          if r['observation']['status'] != 'COMPLETE'],
        'ordinaryPreferredWithoutModelVetoed': [r for r in evidence
            if r['observation'].get('ordinaryRankingAfterModel') is not None
            and not r['observation']['ordinaryRankingAfterModel']['usedModel']
            and r['observation']['ordinaryRankingAfterModel']['preferredId'] > 0
            and not r['evaluation']['boundaryAutoEdit']],
        'limits': ['Current source diagnostic of already revealed holdout; no new qualification or threshold fitting.',
            'Independent in-memory TypingEdit executor, JVM BreakIterator, no real Android InputConnection or device execution.',
            'Letters-layer Shift OFF text actions; no keyboard-view/symbol-layer transitions or asynchronous availability timing.',
            'Fresh scores admitted only on exact live prefix, continuation order, and candidate-ID equality.',
            'Native SCORING_FAILED is delivered as UNAVAILABLE with empty scores; preserves failure and prohibits a numeric ranking.',
            '95% Wilson intervals are descriptive row intervals; frozen candidate-set repetitions are not independent user samples.',
            'Full final-text metrics include mechanical changes before the boundary; Undo metric restores pre-boundary state, not earlier mechanical changes.']}
    write('summary.json', summary)
    assert all(sha(Path(p)) == digest for p, digest in bound.items()), 'Execution input drift'
    write('execution-receipt.json', {'schemaVersion': 1, 'complete': True, 'freshControllerExecution': True,
        'rows': 6000, 'inputHashes': bound, 'sourceAssetToolchainCorpusCacheHashesUnchanged': True,
        'originalCanonicalEvidenceUnchanged': True, 'sourceHeadAfter': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
        'modelCalls': 0, 'oldScoreCacheReads': 0, 'elapsedHostSeconds': time.monotonic()-started,
        'runtimeClasspath': runtime_cmd[runtime_cmd.index('-cp')+1],
        'artifacts': {p.name: sha(p) for p in OUT.iterdir() if p.is_file()}, 'limits': summary['limits']})
    print(json.dumps({lang: {'admission': summary['languages'][lang]['modelAdmissionCounts'],
        'full': summary['languages'][lang]['allFinalTextChanges'],
        'spelling': summary['languages'][lang]['ordinarySpellingBoundaryAutoEdits']}
        for lang in ('en','ru','es')}, indent=2), flush=True)

if __name__ == '__main__':
    main()
