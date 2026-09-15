#!/usr/bin/env python3
"""Source-bound host experiment; never promotes an Android autocorrection policy."""
from __future__ import annotations

import argparse
import base64
from collections import Counter
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import unicodedata

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PIPELINE = REPO / 'tools/eval/smart-typing-0.3/pipeline'
CORPUS = PIPELINE.parent / 'qualification-v2/corpus'


def require(value, code):
    if not value:
        raise ValueError(code)


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def write_json(path, value):
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        f.write('\n')


def read_jsonl(path):
    require(path.is_file() and path.stat().st_size <= 256_000_000, 'INPUT_SIZE')
    rows = []
    with path.open(encoding='utf-8') as f:
        for line in f:
            require(len(line) <= 1_000_000, 'LINE_SIZE')
            if line.strip():
                rows.append(json.loads(line))
                require(len(rows) <= 20_000, 'ROW_LIMIT')
    return rows


def write_jsonl(path, rows):
    with path.open('x', encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n')


def output_directory(value):
    root = Path(value).resolve()
    require(root.is_relative_to(REPO / 'build') and not root.exists(), 'FRESH_BUILD_OUTPUT_REQUIRED')
    ignored = subprocess.run(['git', 'check-ignore', '-q', str(root)], cwd=REPO, capture_output=True)
    require(ignored.returncode == 0, 'OUTPUT_MUST_BE_GIT_IGNORED')
    root.mkdir(parents=True, mode=0o700)
    return root


def normalized(word):
    return unicodedata.normalize('NFC', word).lower()


def validate_rows(rows):
    require(isinstance(rows, list) and 0 < len(rows) <= 20_000, 'ROWS_REQUIRED')
    ids = set()
    for row in rows:
        require(isinstance(row, dict), 'ROW_OBJECT')
        require(isinstance(row.get('id'), str) and 0 < len(row['id']) <= 128 and row['id'] not in ids, 'ROW_ID')
        ids.add(row['id'])
        require(row.get('language') == 'ru' and row.get('split') in ('calibration', 'holdout', 'diagnostic'), 'ROW_PARTITION')
        require(isinstance(row.get('typed'), str) and 0 < len(row['typed']) <= 128, 'TOKEN_SIZE')
        require(isinstance(row.get('prefix'), str) and len(row['prefix']) <= 8192, 'PREFIX_SIZE')
        require(row.get('cohort') in ('typo', 'correct', 'protected', 'unlabeled') and type(row.get('noAuto')) is bool, 'ROW_LABEL')
        if row['cohort'] == 'typo':
            require(isinstance(row.get('expectedSpelling'), str) and 0 < len(row['expectedSpelling']) <= 128, 'EXPECTED_SPELLING')


def verify_observations(rows, observations):
    require(len(rows) == len(observations), 'OBSERVATION_COUNT')
    for i, (row, observation) in enumerate(zip(rows, observations, strict=True)):
        require(isinstance(observation, dict) and type(observation.get('index')) is int and observation['index'] == i, 'OBSERVATION_ORDER')
        require(isinstance(observation.get('generation'), dict) and observation['generation'].get('original') == row['typed'], 'OBSERVATION_ORIGINAL')
        require(observation.get('baseline') is None or isinstance(observation['baseline'], str), 'BASELINE_TYPE')


def metrics(rows, predictions):
    require(len(rows) == len(predictions), 'PREDICTION_COUNT')
    counts = Counter(rows=len(rows))
    for row, prediction in zip(rows, predictions, strict=True):
        require(prediction is None or isinstance(prediction, str), 'PREDICTION_TYPE')
        changed = prediction is not None and normalized(prediction) != normalized(row['typed'])
        counts['changes' if changed else 'abstentions'] += 1
        negative = row['cohort'] != 'typo' or row['noAuto']
        counts['negativeRows' if negative else 'typoRows'] += 1
        if changed:
            correct = not negative and normalized(prediction) == normalized(row['expectedSpelling'])
            counts['correctChanges' if correct else 'falseChanges'] += 1
            if negative:
                counts['negativeChanges'] += 1
            if row['cohort'] == 'protected':
                counts['protectedChanges'] += 1
    result = {key: counts[key] for key in ('rows', 'changes', 'abstentions', 'correctChanges', 'falseChanges',
        'negativeRows', 'negativeChanges', 'typoRows', 'protectedChanges')}
    result.update(precision=counts['correctChanges'] / counts['changes'] if counts['changes'] else None,
        typoRecall=counts['correctChanges'] / counts['typoRows'] if counts['typoRows'] else None,
        negativeFalseChangeRate=counts['negativeChanges'] / counts['negativeRows'] if counts['negativeRows'] else None)
    return result


def bindings(paths):
    return {str(p.resolve()): sha(p) for p in paths}


def verify_bindings(files):
    require(isinstance(files, dict) and files, 'EMPTY_BINDINGS')
    for name, digest in files.items():
        require(Path(name).is_file() and sha(name) == digest, 'BOUND_FILE_CHANGED')


def verify_export(source, receipt):
    require(receipt.get('schemaVersion') == 1 and receipt.get('scope') == 'host-production-candidate-proposals', 'EXPORT_SCHEMA')
    files = receipt.get('files')
    require(isinstance(files, dict), 'EXPORT_FILES')
    for name in ('rows.jsonl', 'observations.jsonl', 'inputs.tsv', 'source-freeze.json'):
        actual = (source / name).resolve(strict=True)
        require(actual.is_relative_to(source) and str(actual) in files
                and sha(actual) == files[str(actual)], 'CONSUMED_INPUT_NOT_BOUND')
    verify_bindings(receipt['sources']); verify_bindings(files)


def final_proposal(decision, baseline):
    if decision.word is not None:
        return decision.word, False
    # No evidence falls back to the existing policy. An evaluated keep-original
    # decision (insufficient margin) remains no-change, even if baseline differs.
    unavailable = decision.reason in {'no_context', 'no_context_evidence', 'no_candidates',
        'incomplete_local_search', 'incomplete_generation', 'unsupported_original'}
    return (baseline, True) if unavailable else (None, False)


def load_replay():
    spec = importlib.util.spec_from_file_location('morphology_production_replay', PIPELINE / 'final_product_replay.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def export(args):
    root = output_directory(args.output)
    if args.rows:
        rows_path = Path(args.rows).resolve(strict=True)
        rows = read_jsonl(rows_path)
        input_sources = [rows_path]
    else:
        manifest_path = CORPUS / 'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        input_sources = [manifest_path]
        for name, digest in manifest['files'].items():
            path = CORPUS / name
            require(path.resolve().is_relative_to(CORPUS.resolve()) and sha(path) == digest, 'CORPUS_IDENTITY')
            input_sources.append(path)
        rows = read_jsonl(CORPUS / 'spelling-ru.jsonl')
        rows += [r for r in read_jsonl(CORPUS / 'protected-tokens.jsonl') if r['language'] == 'ru']
        require(len(rows) == 4000, 'FROZEN_RU_ROW_COUNT')
    validate_rows(rows)
    replay = load_replay()
    java = Path(args.java).resolve(strict=True)
    sources, jars, android = replay.compile_inputs(java)
    sources = [p for p in sources if p != replay.HARNESS] + [HERE / 'ProductionCandidates.kt']
    source_bindings = bindings([*input_sources, *sources, *jars, android, java, *replay.asset_paths(),
        HERE / 'evaluate.py', PIPELINE / 'final_product_replay.py', replay.SOURCE_MANIFEST, replay.TOOLCHAIN])
    write_json(root / 'source-freeze.json', source_bindings)
    write_jsonl(root / 'rows.jsonl', rows)
    inputs = root / 'inputs.tsv'
    with inputs.open('x', encoding='ascii') as f:
        for i, row in enumerate(rows):
            encoded = base64.b64encode(row['typed'].encode()).decode('ascii')
            f.write(f'{i}\t{encoded}\n')
    jar, compile_command = replay.compile_harness(root, java, sources, jars, android)
    command = [str(java), '-XX:ActiveProcessorCount=2', '-Xmx768m', '-cp',
        os.pathsep.join(map(str, [jar, jars[1], jars[2], android])),
        'io.github.mesteriis.rune.keyboard.smarttyping.lexicon.ProductionCandidates', str(inputs), str(replay.ASSETS)]
    started = time.perf_counter()
    with (root / 'observations.jsonl').open('xb') as out, (root / 'generation.log').open('xb') as log:
        subprocess.run(command, stdout=out, stderr=log, timeout=1200, check=True)
    elapsed = time.perf_counter() - started
    verify_observations(rows, read_jsonl(root / 'observations.jsonl'))
    verify_bindings(source_bindings)
    write_json(root / 'receipt.json', dict(schemaVersion=1, scope='host-production-candidate-proposals',
        productionQualified=False, androidPerformanceMeasured=False, rows=len(rows), elapsedSeconds=elapsed,
        commands=[compile_command, command], sources=source_bindings,
        files=bindings([root / n for n in ('rows.jsonl', 'inputs.tsv', 'observations.jsonl', 'source-freeze.json', 'compile.log', 'generation.log')])))
    print(json.dumps({'exportedRows': len(rows), 'seconds': round(elapsed, 3)}))


def clean_reference(row):
    if row['noAuto'] or row['cohort'] not in ('correct', 'typo'):
        return None
    word = row.get('expectedSpelling', row['typed'])
    return (row['prefix'].strip() + ' ' + word).strip()


def latency(values):
    values = sorted(values)
    if not values:
        return {'count': 0, 'medianMs': None, 'p95Ms': None, 'maxMs': None}
    require(all(math.isfinite(v) and v >= 0 for v in values), 'LATENCY_VALUE')
    return dict(count=len(values), medianMs=values[len(values)//2],
        p95Ms=values[min(len(values)-1, math.ceil(len(values)*.95)-1)], maxMs=max(values))


def compare(args):
    from ranker import PymorphyLexicon, decide
    from telegram_style import StyleModel, build_model

    source = Path(args.export).resolve(strict=True)
    receipt = json.loads((source / 'receipt.json').read_text())
    verify_export(source, receipt)
    rows = read_jsonl(source / 'rows.jsonl'); validate_rows(rows)
    observations = read_jsonl(source / 'observations.jsonl'); verify_observations(rows, observations)
    root = output_directory(args.output)
    freeze = bindings([HERE / n for n in ('ranker.py', 'telegram_style.py', 'evaluate.py', 'requirements.lock')])
    style = None
    style_source = 'none'
    if args.style_model:
        model_path = Path(args.style_model).resolve(strict=True)
        require(model_path.stat().st_size <= 64_000_000, 'STYLE_MODEL_SIZE')
        payload = json.loads(model_path.read_text())
        style = StyleModel(payload)
        freeze.update(bindings([model_path])); style_source = 'explicit-local-model'
    elif args.train_public_style:
        training = [clean_reference(r) for r in rows if r['split'] == 'calibration']
        training = sorted(set(t for t in training if t))
        require(training, 'NO_PUBLIC_TRAINING_ROWS')
        validation = {clean_reference(r) for r in rows if r['split'] == 'holdout'}
        require(not set(training).intersection(validation), 'EXACT_TRAIN_VALIDATION_OVERLAP')
        payload = build_model(training)
        write_json(root / 'style-model.json', payload)
        style = StyleModel(payload); style_source = 'public-calibration-only'
    started = time.perf_counter()
    lexicon = PymorphyLexicon()
    lexicon.analyses('слово')  # Public warm-up forces the lazy dictionary load.
    load_ms = (time.perf_counter() - started) * 1000
    dictionary = lexicon.receipt()
    write_json(root / 'policy-freeze.json', dict(sourceBindings=freeze, dictionary=dictionary,
        styleSource=style_source, thresholdsFittedOnHoldout=False))
    predictions = {name: [] for name in ('baseline', 'morphology', 'morphology_style')}
    timings = {name: [] for name in ('morphology', 'morphology_style')}
    # Separate bounded caches prevent the first variant from paying the other's cold lookup cost.
    style_lexicon = PymorphyLexicon() if style else None
    style_load_ms = None
    if style_lexicon is not None:
        started = time.perf_counter()
        style_lexicon.analyses('слово')
        style_load_ms = (time.perf_counter() - started) * 1000
    details = []
    for row, observation in zip(rows, observations, strict=True):
        generation = observation['generation']
        baseline = observation['baseline']
        predictions['baseline'].append(baseline)
        result = {'id': row['id'], 'baseline': baseline}
        for name in ('morphology', 'morphology_style'):
            if name == 'morphology_style' and style is None:
                predictions[name].append(None)
                continue
            start = time.perf_counter()
            decision = decide(generation, row['prefix'], lexicon if name == 'morphology' else style_lexicon,
                style=None if name == 'morphology' else style)
            timings[name].append((time.perf_counter() - start) * 1000)
            proposal, fallback = final_proposal(decision, baseline)
            predictions[name].append(proposal)
            result[name] = dict(word=proposal, reason=decision.reason,
                fallbackToBaseline=fallback, scores=decision.scores)
        details.append(result)
    reports = {}
    for split in sorted({r['split'] for r in rows}):
        indices = [i for i,r in enumerate(rows) if r['split'] == split and r['cohort'] != 'unlabeled']
        reports[split] = {name: metrics([rows[i] for i in indices], [values[i] for i in indices])
            for name,values in predictions.items() if name != 'morphology_style' or style is not None}
    write_jsonl(root / 'decisions.jsonl', details)
    verify_bindings(freeze); verify_bindings(receipt['sources']); verify_bindings(receipt['files'])
    require(lexicon.receipt() == dictionary, 'DICTIONARY_CHANGED')
    report = dict(schemaVersion=1, scope='host-proposal-experiment', productionQualified=False,
        unseenGeneralizationEstablished=False, androidPerformanceMeasured=False,
        editorUndoMeasured=False, baseline='production-general-local-plus-common-confusion-proposals',
        fallback='baseline-only-when-context-evidence-unavailable; respect-evaluated-keep-original',
        styleSource=style_source, morphologyStyleExecuted=style is not None,
        dictionaryLoadMs=load_ms, styleDictionaryLoadMs=style_load_ms,
        timingScope='host-single-process; dictionary preloaded with public word; cold-then-bounded lookup caches; excludes generator unless stated',
        latencies={**{k:latency(v) for k,v in timings.items()},
            'productionGenerator':latency([o['generationMs'] for o in observations]),
            'productionBaseline':latency([o['baselineMs'] for o in observations])},
        reports=reports, sources=freeze, dictionary=dictionary,
        exportReceiptSha256=sha(source / 'receipt.json'), decisionsSha256=sha(root / 'decisions.jsonl'))
    write_json(root / 'report.json', report)
    print(json.dumps({'reports':reports, 'styleSource':style_source, 'productionQualified':False},ensure_ascii=False))


def main():
    os.umask(0o077)
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('export');p.add_argument('--rows',type=Path);p.add_argument('--output',required=True)
    p.add_argument('--java',default='/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/java')
    p.set_defaults(action=export)
    p=sub.add_parser('compare');p.add_argument('--export',required=True);p.add_argument('--output',required=True)
    group=p.add_mutually_exclusive_group();group.add_argument('--style-model');group.add_argument('--train-public-style',action='store_true')
    p.set_defaults(action=compare)
    args=parser.parse_args()
    try:
        args.action(args)
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        # Paths and message values are private; detailed raw child logs remain in ignored output.
        print('Morphology experiment failed: '+type(error).__name__,file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
