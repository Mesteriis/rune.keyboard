#!/usr/bin/env python3
"""Scratch actual-source observer. No model/cache input, policy fitting, or corpus edits."""
from pathlib import Path
import base64
from collections import Counter
import hashlib
import json
import os
import platform
import subprocess
import sys
import time

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[3]
PROD = REPO / 'app/src/main/java/io/github/mesteriis/rune/keyboard'
JAVA = Path('/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/java').resolve()
ANDROID = Path('/opt/homebrew/share/android-commandlinetools/platforms/android-37.0/android.jar')
MANIFEST = REPO / 'tools/lexicon/smart-typing-0.3/weighted-qualification/manifests/reproduction-toolchain.json'
CORPUS = REPO / 'tools/eval/smart-typing-0.3'
SOURCE_NAMES = ['ime/model/KeyboardState.kt', 'ime/model/EditorContext.kt', 'ime/editor/DoubleSpacePeriod.kt',
    'settings/KeyboardSettings.kt', 'intelligence/ipc/ScoringContract.kt']
SOURCE_NAMES += [f'smarttyping/correction/{name}.kt' for name in (
    'TokenUnicode', 'ProtectedTokenPolicy', 'CasePattern', 'KeyboardDistance', 'WeightedDamerauLevenshtein',
    'CandidateRanker', 'CalibratedSpellingPolicy', 'SpellingQualification')]
SOURCE_NAMES += [f'smarttyping/lexicon/{name}.kt' for name in (
    'LanguageRouter', 'CandidateLexicon', 'CanonicalCaseLexicon', 'CandidateGenerator', 'PackedCandidateLexicon',
    'PackedLexiconData', 'PackedLexiconManifest', 'FrozenPackedLexicons', 'TopCandidateSelection',
    'PackedTopSeven', 'PrefixDistance', 'CanonicalCaseData', 'FrozenCanonicalCaseLexicons', 'LocalCandidateWorker')]
SOURCE_NAMES += [f'smarttyping/session/{name}.kt' for name in (
    'TypingSessionController', 'TypingSessionState', 'ComposingSegment', 'SessionTextContext', 'UndoableTextEdit')]
SOURCE_NAMES += [f'smarttyping/punctuation/{name}.kt' for name in (
    'MechanicalPunctuationPlan', 'MechanicalPunctuationPlanner', 'ContextualPunctuationEngine', 'ContextualPunctuationPolicy')]
SOURCE_NAMES += ['smarttyping/ui/CandidateUiItem.kt', 'smarttyping/ui/SmartTypingViewState.kt',
    'smarttyping/telemetry/SmartTypingTrace.kt']

def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n')

def lines(path, rows):
    path.write_text(''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n' for r in rows))

def main():
    assert not (OUT / 'execution-receipt.json').exists(), 'Preserve completed evidence'
    source_files = [PROD / s for s in SOURCE_NAMES] + [OUT / 'CanonicalControllerDiagnostic.kt']
    corpus_files = [CORPUS / n for n in ('manifest.json', 'spelling-en.jsonl', 'spelling-ru.jsonl',
                                         'spelling-es.jsonl', 'protected-tokens.jsonl')]
    manifest = json.loads((CORPUS / 'manifest.json').read_text())
    for path in corpus_files[1:]:
        assert sha(path) == manifest['files'][path.name], path
    rows = []
    for path in corpus_files[1:]:
        for line in path.open():
            row = json.loads(line)
            if row['task'] == 'spelling' and row['split'] == 'holdout' and row['cohort'] in ('correct', 'protected'):
                rows.append(row)
    assert len(rows) == 3000 and len({r['id'] for r in rows}) == 3000
    assert Counter((r['language'], r['cohort']) for r in rows) == {
        (lang, cohort): count for lang in ('en', 'ru', 'es') for cohort, count in (('correct', 700), ('protected', 300))}
    controls = [dict(id=f'public-control-{lang}-{typed}', language=lang, prefix=prefix, typed=typed,
                     diagnosticClass='public-control-no-frozen-label')
                for lang, prefix, typed in [('en', 'we', 'will'), ('en', 'we', 'may'), ('en', 'a', 'brown'),
                    ('en', '', 'paris'), ('en', '', 'london'), ('ru', '', 'москва'), ('es', '', 'juan')]]
    lines(OUT / 'frozen-negative-inputs.jsonl', rows)
    lines(OUT / 'public-controls.jsonl', controls)
    all_rows = rows + controls
    enc = lambda text: base64.b64encode(text.encode()).decode('ascii')
    (OUT / 'inputs.tsv').write_text(''.join(f'{i}\t{enc(r["id"])}\t{r["language"]}\t{enc(r["prefix"])}\t{enc(r["typed"])}\n'
                                           for i, r in enumerate(all_rows)), encoding='ascii')
    toolchain = json.loads(MANIFEST.read_text())
    jars = []
    for item in toolchain['jars']:
        found = list((Path('/Users/avm/.gradle/caches/modules-2/files-2.1') / item['group'] / item['artifact'] /
                     item['version']).glob('*/*.jar'))
        assert len(found) == 1 and sha(found[0]) == item['sha256']
        jars.append(found[0])
    java_version = subprocess.run([str(JAVA), '-version'], capture_output=True, text=True, check=True).stderr
    assert 'version "17.' in java_version
    assets = [REPO / 'app/src/main/assets/smarttyping/lexicon' / name
              for lang in ('en', 'ru', 'es') for name in
              (f'{lang}.trie', f'{lang}.trie.lengths', f'frequency/{lang}.ranks', f'case/{lang}.case')]
    bind_files = source_files + assets + corpus_files + [Path(__file__), MANIFEST, JAVA, ANDROID] + jars
    hashes_before = {str(p): sha(p) for p in bind_files}
    binary = OUT / 'canonical-controller.jar'
    compile_cp = os.pathsep.join(map(str, [*jars[1:3], ANDROID]))
    runtime_cp = os.pathsep.join(map(str, [binary, *jars[1:3], ANDROID]))
    compile_cmd = [str(JAVA), '-XX:ActiveProcessorCount=2', '-Xmx768m', '-cp', os.pathsep.join(map(str, jars)),
        'org.jetbrains.kotlin.cli.jvm.K2JVMCompiler', '-no-stdlib', '-no-reflect', '-jvm-target', '17',
        '-classpath', compile_cp, '-d', str(binary), *map(str, source_files)]
    runtime_cmd = [str(JAVA), '-XX:ActiveProcessorCount=2', '-Xmx768m', '-cp', runtime_cp,
        'io.github.mesteriis.rune.keyboard.smarttyping.session.CanonicalControllerDiagnostic',
        str(OUT / 'inputs.tsv'), str(REPO / 'app/src/main/assets')]
    write(OUT / 'commands.json', {'compile': compile_cmd, 'execute': runtime_cmd, 'runtimeClasspath': runtime_cp})
    write(OUT / 'input-binding.json', {'hashesBefore': hashes_before, 'javaVersion': java_version,
        'platform': platform.platform(), 'headBefore': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()})
    started = time.monotonic()
    with (OUT / 'compile.log').open('wb') as log:
        subprocess.run(compile_cmd, stdout=log, stderr=log, timeout=180, check=True)
    print('CURRENT_SOURCE_HOST_COMPILE_PASS', flush=True)
    with (OUT / 'actual.jsonl').open('wb') as output, (OUT / 'run.log').open('wb') as log:
        subprocess.run(runtime_cmd, stdout=output, stderr=log, timeout=600, check=True)
    outputs = [json.loads(line) for line in (OUT / 'actual.jsonl').open()]
    assert len(outputs) == len(all_rows)
    assert [(r['id'], r['typed'], r['prefix'], r['language']) for r in outputs] == [
        (r['id'], r['typed'], r['prefix'], r['language']) for r in all_rows]
    joined = [{'input': row, 'observation': obs} for row, obs in zip(all_rows, outputs)]
    lines(OUT / 'row-evidence.jsonl', joined)
    def counts(items):
        obs = [o for _, o in items]
        canonical = lambda o: any(c['kind'] == 'CANONICAL_CASE' for c in (o.get('actualRequestGeneration') or {}).get('alternatives', []))
        auto = lambda o: o.get('autoEdit') is not None
        return dict(rows=len(obs), statuses=dict(Counter(o['status'] for o in obs)),
            actualCanonicalCandidateRows=sum(canonical(o) for o in obs), autoEditRows=sum(auto(o) for o in obs),
            canonicalAutoEditRows=sum(auto(o) and canonical(o) for o in obs),
            boundaryChangedRows=sum(o.get('boundaryChangedBeyondInsertedSpace', False) for o in obs),
            inputChangedByTypingRows=sum(o.get('inputChangedByTyping', False) for o in obs),
            beforeBoundaryRestoredRows=sum(o.get('restoredBeforeBoundaryExactly', False) for o in obs),
            autoEditRestoredRows=sum(auto(o) and o.get('restoredBeforeBoundaryExactly', False) for o in obs),
            noRequestRows=sum(o.get('requestToken') is None for o in obs))
    frozen_pairs = list(zip(rows, outputs[:len(rows)]))
    summary = {'scope': 'actual-current-kotlin-generator-controller-canonical-diagnostic',
        'frozenNegativeLabelsUnchanged': True, 'modelCalls': 0, 'modelCacheReads': 0,
        'qualificationOverride': False, 'policyTuning': False, 'realInputConnection': False,
        'mechanicalPunctuation': True, 'timedDoubleSpaceGesture': False,
        'defaultAutocorrectionMode': 'HIGH_CONFIDENCE', 'spellingConfidencePolicy': 'current-source-fixed-default95',
        'frozenNegativeCounts': counts(frozen_pairs),
        'groups': {f'{lang}/{cohort}': counts([(r, o) for r, o in frozen_pairs if r['language'] == lang and r['cohort'] == cohort])
                   for lang in ('en', 'ru', 'es') for cohort in ('correct', 'protected')},
        'frozenAutoEdits': [{'id': r['id'], 'typed': r['typed'], 'prefix': r['prefix'], 'language': r['language'],
            'cohort': r['cohort'], 'autoEdit': o.get('autoEdit'), 'afterBoundary': o.get('afterBoundary'),
            'restoredBeforeBoundaryExactly': o.get('restoredBeforeBoundaryExactly'),
            'generation': o.get('actualRequestGeneration')} for r, o in frozen_pairs if o.get('autoEdit')],
        'publicControls': joined[len(rows):],
        'errors': [{'id': o['id'], 'error': o.get('error')} for o in outputs if o['status'] != 'COMPLETE'],
        'limitations': ['Host JVM BreakIterator, not Android ICU; no real InputConnection or Android runtime execution.',
            'Independent in-memory editor only; coalesced successful command acknowledgements, no editor IPC failure or reentrancy simulation.',
            'Characters supplied through controller text entry on letters layer with Shift OFF; no key-view or symbol-layer event dispatch.',
            'A ready synchronous latest local generation is accepted immediately before the space boundary; no asynchronous scheduling/latency claim.',
            'No model ranking. Ordinary spelling candidates retain the current qualification veto. This is narrow canonical evidence, not release quality qualification.',
            'Frozen repeated candidate-set-sensitivity rows are retained; row counts are not independent word or user samples.']}
    write(OUT / 'summary.json', summary)
    hashes_after = {str(p): sha(p) for p in bind_files}
    assert hashes_before == hashes_after, 'Execution input drift'
    receipt = {'schemaVersion': 1, 'complete': True, 'freshExecution': True,
        'elapsedSeconds': time.monotonic() - started, 'rows': len(outputs),
        'sourceAssetCorpusToolchainHashesUnchanged': True, 'inputHashes': hashes_before,
        'javaVersion': java_version, 'pythonVersion': sys.version, 'platform': platform.platform(),
        'headAfter': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
        'runtimeClasspath': runtime_cp, 'artifacts': {p.name: sha(p) for p in OUT.iterdir() if p.is_file()},
        'actualProductionAssetReaders': ['PackedLexiconData.validate', 'CanonicalCaseData.validate'],
        'canonicalFilesystemAdapterChecks': 'FrozenCanonicalCaseLexicons size/SHA256 then actual CanonicalCaseData.validate',
        'scopeLimits': summary['limitations']}
    write(OUT / 'execution-receipt.json', receipt)
    print(json.dumps({'frozenNegativeCounts': summary['frozenNegativeCounts'], 'errors': summary['errors'],
                      'receipt': str(OUT / 'execution-receipt.json')}, indent=2), flush=True)

if __name__ == '__main__':
    main()
