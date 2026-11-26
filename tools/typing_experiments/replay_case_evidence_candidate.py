#!/usr/bin/env python3
"""Compare an isolated canonical-case ambiguity overlay; never package or qualify it."""
import argparse
import base64
from collections import Counter
from itertools import zip_longest
import json
import os
from pathlib import Path
import re

from replay_joint_correction import replay, controller_records
from chat_case_review import PURPOSE
import chat_guard_extended_compare as extended_compare

ROOT = Path(__file__).resolve().parents[2]
MARKER = '            CanonicalCaseLexicon { language, key -> cases.getValue(language).lookup(key) },'
SCREEN_PURPOSE = 'DISCLOSED_LOWERCASE_EVIDENCE_SCREEN_NOT_QUALIFICATION'


def overlay(source, words):
    if not words or words != sorted(set(words)) or any(not re.fullmatch('[а-яё]{2,32}', word) for word in words):
        raise ValueError('CASE_CANDIDATE_WORDS')
    if source.count(MARKER) != 1:
        raise ValueError('CASE_CANDIDATE_SOURCE')
    literals = ', '.join('"' + word + '"' for word in words)
    replacement = '''            CanonicalCaseLexicon { language, key ->
                val original = cases.getValue(language).lookup(key)
                if (language == KeyboardLanguage.RUSSIAN && key in setOf(''' + literals + '''))
                    original?.copy(unambiguous = false) else original
            },'''
    return source.replace(MARKER, replacement)


def summarize(rows, baseline, candidate, review):
    if review.get('purpose') != PURPOSE:
        raise ValueError('CASE_CANDIDATE_REVIEW')
    cases = {c['id']: c for c in review['cases']}
    if len(cases) != len(review['cases']):
        raise ValueError('CASE_CANDIDATE_REVIEW_IDS')
    counts = Counter()
    found = set()
    for index, (row, oldline, newline) in enumerate(zip_longest(rows, baseline, candidate)):
        if row is None or oldline is None or newline is None:
            raise ValueError('CASE_CANDIDATE_ROW_COUNT')
        old, new = json.loads(oldline), json.loads(newline)
        if (old.get('id') != row['id'] or new.get('id') != f'joint-replay-{index:08d}'
                or old.get('index') != index or new.get('index') != index
                or old.get('status') != 'COMPLETE' or new.get('status') != 'COMPLETE'
                or any(old.get(k) != row[k] or new.get(k) != row[k]
                       for k in ('split', 'language', 'prefix', 'typed'))):
            raise ValueError('CASE_CANDIDATE_ROW_IDENTITY')
        before = old['beforeBoundary']['text']
        if new['beforeBoundary']['text'] != before or not before.casefold().endswith(row['typed'].casefold()):
            raise ValueError('CASE_CANDIDATE_TYPING')
        left = old['afterBoundary']['text']
        right = new['afterBoundary']['text']
        for obs, after in ((old, left), (new, right)):
            if (not after.endswith(' ') or type(obs.get('boundaryChangedBeyondInsertedSpace')) is not bool
                    or obs['boundaryChangedBeyondInsertedSpace'] != (after != before + ' ')):
                raise ValueError('CASE_CANDIDATE_BOUNDARY')
        if left != right:
            counts['differentBoundaryRows'] += 1
            counts['different_' + row['cohort']] += 1
        if row['cohort'] == 'correct':
            counts['baselineControlChanges'] += left != before + ' '
            counts['candidateControlChanges'] += right != before + ' '
        if row['cohort'] == 'typo':
            expected = (before[:-len(row['typed'])] + row['expectedSpelling'] + ' ').casefold()
            counts['syntheticTypoGain'] += left.casefold() != expected and right.casefold() == expected
            counts['syntheticTypoLoss'] += left.casefold() == expected and right.casefold() != expected
        if new['boundaryChangedBeyondInsertedSpace'] and new.get('restoredBeforeBoundaryExactly') is not True:
            counts['candidateUndoFailures'] += 1
        if row['id'] in cases:
            case = cases[row['id']]
            if case['typed'] != row['typed']:
                raise ValueError('CASE_CANDIDATE_REVIEW_ROW')
            found.add(row['id'])
            label = case['label']
            counts['review_' + label] += 1
            counts['review_' + label + '_unchangedFromBaseline'] += left == right
            if label == 'lowercase_preserve':
                counts['review_lowercase_preserved'] += right == before + ' '
        counts['rows'] += 1
    if found != cases.keys():
        raise ValueError('CASE_CANDIDATE_REVIEW_COVERAGE')
    return dict(sorted(counts.items()))


def summarize_name_contrasts(rows, baseline, candidate):
    counts = Counter()
    articles = set()
    for index, (row, oldline, newline) in enumerate(zip_longest(rows, baseline, candidate)):
        if row is None or oldline is None or newline is None:
            raise ValueError('NAME_COMPARE_COUNT')
        old, new = json.loads(oldline), json.loads(newline)
        if (row.get('cohort') != 'name_contrast' or row.get('purpose') != 'DISCLOSED_NAME_CONTRAST_NOT_QUALIFICATION'
                or row.get('split') != 'calibration' or row.get('language') != 'ru'
                or not isinstance(row.get('article'), str) or not row['article'].isdecimal()
                or old.get('id') != row['id'] or new.get('id') != f'joint-replay-{index:08d}'
                or old.get('index') != index or new.get('index') != index
                or old.get('status') != 'COMPLETE' or new.get('status') != 'COMPLETE'
                or any(old.get(k) != row[k] or new.get(k) != row[k] for k in ('split', 'language', 'prefix', 'typed'))):
            raise ValueError('NAME_COMPARE_IDENTITY')
        typed, expected = row['typed'], row['expectedSpelling']
        if not typed or typed.lower() != typed or not expected.istitle() or expected.lower() != typed:
            raise ValueError('NAME_COMPARE_CASE')
        before = old['beforeBoundary']['text']
        if new['beforeBoundary']['text'] != before or not before.casefold().endswith(typed.casefold()):
            raise ValueError('NAME_COMPARE_INPUT')
        left, right = old['afterBoundary']['text'], new['afterBoundary']['text']
        for obs, after in ((old, left), (new, right)):
            if (not after.endswith(' ') or type(obs.get('boundaryChangedBeyondInsertedSpace')) is not bool
                    or obs['boundaryChangedBeyondInsertedSpace'] != (after != before + ' ')):
                raise ValueError('NAME_COMPARE_BOUNDARY')
        expected_output = before[:-len(typed)] + expected + ' '
        old_match, new_match = left == expected_output, right == expected_output
        counts['baselineSourceCaseMatches'] += old_match
        counts['candidateSourceCaseMatches'] += new_match
        counts['lostSourceCaseMatches'] += old_match and not new_match
        counts['gainedSourceCaseMatches'] += new_match and not old_match
        counts['differentBoundaryRows'] += left != right
        if new['boundaryChangedBeyondInsertedSpace'] and new.get('restoredBeforeBoundaryExactly') is not True:
            counts['candidateUndoFailures'] += 1
        counts['rows'] += 1
        articles.add(row['article'])
    if not counts['rows']:
        raise ValueError('NAME_COMPARE_EMPTY')
    counts['articles'] = len(articles)
    return dict(sorted(counts.items()))


def summarize_context_collision(rows, baseline, candidate):
    if len(rows) != 2 or {r.get('sense') for r in rows} != {'common', 'name'}:
        raise ValueError('COLLISION_SCOPE')
    if len({(r.get('language'), r.get('split'), r.get('prefix'), r.get('typed')) for r in rows}) != 1:
        raise ValueError('COLLISION_INPUTS_DIFFER')
    counts = Counter()
    before_set, baseline_outputs, candidate_outputs = set(), set(), set()
    for index, (row, oldline, newline) in enumerate(zip_longest(rows, baseline, candidate)):
        if row is None or oldline is None or newline is None:
            raise ValueError('COLLISION_COUNT')
        old, new = json.loads(oldline), json.loads(newline)
        if (row.get('purpose') != 'DISCLOSED_CONTEXT_COLLISION_NOT_QUALIFICATION' or row.get('cohort') != 'case_collision'
                or row.get('language') != 'ru' or row.get('split') != 'calibration'
                or old.get('id') != row['id'] or new.get('id') != f'joint-replay-{index:08d}'
                or old.get('index') != index or new.get('index') != index
                or old.get('status') != 'COMPLETE' or new.get('status') != 'COMPLETE'
                or any(old.get(k) != row[k] or new.get(k) != row[k] for k in ('split', 'language', 'prefix', 'typed'))):
            raise ValueError('COLLISION_IDENTITY')
        token = row['typed']
        expected = row['expectedSpelling']
        if not token or token.lower() != token or expected != (token if row['sense'] == 'common' else token.title()):
            raise ValueError('COLLISION_LABEL')
        before = old['beforeBoundary']['text']
        if new['beforeBoundary']['text'] != before or not before.casefold().endswith(token.casefold()):
            raise ValueError('COLLISION_INPUT')
        left, right = old['afterBoundary']['text'], new['afterBoundary']['text']
        for obs, after in ((old, left), (new, right)):
            if (not after.endswith(' ') or type(obs.get('boundaryChangedBeyondInsertedSpace')) is not bool
                    or obs['boundaryChangedBeyondInsertedSpace'] != (after != before + ' ')):
                raise ValueError('COLLISION_BOUNDARY')
        expected_output = before[:-len(token)] + expected + ' '
        counts['baseline_' + row['sense'] + '_matches'] += left == expected_output
        counts['candidate_' + row['sense'] + '_matches'] += right == expected_output
        before_set.add(before)
        baseline_outputs.add(left)
        candidate_outputs.add(right)
        counts['rows'] += 1
    if len(before_set) != 1 or len(baseline_outputs) != 1 or len(candidate_outputs) != 1:
        raise ValueError('COLLISION_UNEXPECTED_NONDETERMINISM')
    counts['distinctInputs'] = len(before_set)
    counts['distinctBaselineOutputs'] = len(baseline_outputs)
    counts['distinctCandidateOutputs'] = len(candidate_outputs)
    return dict(sorted(counts.items()))


def run(rows_path, baseline_receipt_path, baseline_observations, screen_path, review_path, output, java, comparison="review"):
    if comparison not in ("review", "parity", "contrast", "collision"):
        raise ValueError("CASE_CANDIDATE_COMPARISON")
    rows_path, baseline_receipt_path, baseline_observations, screen_path, review_path, output, java = map(
        lambda p: Path(p).resolve(), (rows_path, baseline_receipt_path, baseline_observations, screen_path, review_path, output, java))
    if output.exists() or not output.is_relative_to(ROOT / 'build'):
        raise ValueError('CASE_CANDIDATE_OUTPUT')
    if any(os.environ.get(k) for k in ('JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', '_JAVA_OPTIONS')):
        raise ValueError('CASE_CANDIDATE_JAVA_OPTIONS')
    baseline = json.loads(baseline_receipt_path.read_text())
    screen = json.loads(screen_path.read_text())
    review = json.loads(review_path.read_text())
    if (baseline.get('status') != 'COMPLETE' or baseline.get('exitCode') != 0 or baseline.get('mode') != 'current-product'
            or baseline.get('rowsSha256') != replay.sha256(rows_path)
            or baseline.get('observationsSha256') != replay.sha256(baseline_observations)):
        raise ValueError('CASE_CANDIDATE_BASELINE')
    replay.verify_bound_files(baseline)
    bound = screen.get('bindings', {})
    paths_for_screen = {'review': review_path,
        'source': ROOT / 'tools/typing_experiments/public_sources/tatoeba-ru-cc0-20261024/rus_sentences_CC0.tsv.bz2',
        'case': ROOT / 'app/src/main/assets/smarttyping/lexicon/case/ru.case',
        'ledger': ROOT / 'tools/typing_experiments/holdout-ledger.json',
        'tool': ROOT / 'tools/typing_experiments/screen_case_lowercase_evidence.py',
        'ledgerTool': ROOT / 'tools/typing_experiments/holdout_ledger.py',
        'identityTool': ROOT / 'tools/typing_experiments/source_identities.py',
        'splitTool': ROOT / 'tools/typing_experiments/conversation_split_checks.py'}
    if (screen.get('purpose') != SCREEN_PURPOSE or screen.get('independentQualification') is not False
            or any(bound.get(k) != replay.sha256(v) for k, v in paths_for_screen.items())):
        raise ValueError('CASE_CANDIDATE_SCREEN')
    evidence = screen['result']['lowercaseEvidence']
    if any(type(item.get('lowerArticles')) is not int or item['lowerArticles'] < 1 for item in evidence):
        raise ValueError('CASE_CANDIDATE_EVIDENCE')
    words = sorted({item['token'] for item in evidence})
    rows = replay.read_jsonl(rows_path)
    controller = controller_records(rows)
    sources, jars, android = replay.compile_inputs(java)
    paths = list(dict.fromkeys([*sources, *jars, android, java, *sorted(p for p in replay.ASSETS.rglob('*') if p.is_file()),
        rows_path, baseline_receipt_path, baseline_observations, screen_path, review_path, Path(__file__),
        Path(replay.__file__), Path(extended_compare.__file__), *paths_for_screen.values()]))
    bindings = {replay.path_key(p): replay.sha256(p) for p in paths}
    modified = overlay(replay.HARNESS.read_text(), words)
    output.mkdir(parents=True, mode=0o700)
    harness = output / 'FinalProductSpellingReplay.kt'
    harness.write_text(modified)
    enc = lambda s: base64.b64encode(s.encode()).decode('ascii')
    with (output / 'inputs.tsv').open('x', encoding='ascii') as stream:
        for index, row in enumerate(controller):
            stream.write('\t'.join([str(index), enc(row['id']), row['split'], row['language'],
                                    enc(row['prefix']), enc(row['typed'])]) + '\n')
    jar, compile_command = replay.compile_harness(output, java, [harness if p == replay.HARNESS else p for p in sources], jars, android)
    observed = output / 'candidate-observations.jsonl'
    run_command = replay.run_harness(output, java, jars, android, jar, output / 'inputs.tsv', observed, 'current-product')
    with baseline_observations.open(encoding='utf-8') as left, observed.open(encoding='utf-8') as right:
        if comparison == 'review':
            counts = summarize(rows, left, right, review)
        elif comparison == 'contrast':
            counts = summarize_name_contrasts(rows, left, right)
        elif comparison == 'collision':
            counts = summarize_context_collision(rows, left, right)
        else:
            comparison_result = extended_compare.compare(rows, (json.loads(line) for line in left),
                                                        (json.loads(line) for line in right))
            counts = comparison_result['counts']
    replay.verify_bound_files({'files': bindings})
    replay.verify_bound_files(baseline)
    receipt = {'purpose': 'DISCLOSED_CASE_AMBIGUITY_OVERLAY_NOT_QUALIFICATION', 'independentQualification': False,
        'comparison': comparison, 'counts': counts, 'candidateWords': len(words), 'baselineSha256': replay.sha256(baseline_observations),
        'candidateSha256': replay.sha256(observed), 'harnessSha256': replay.sha256(harness), 'jarSha256': replay.sha256(jar),
        'bindings': bindings, 'compileCommand': compile_command, 'runCommand': run_command,
        'caveat': 'In-memory post-hoc overlay, no packaged asset or independent qualification.'}
    with (output / 'receipt.json').open('x') as stream:
        json.dump(receipt, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write('\n')
    return receipt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('rows', 'baseline-receipt', 'baseline-observations', 'screen', 'review', 'output', 'java'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--comparison', choices=('review', 'parity', 'contrast', 'collision'), default='review')
    args = p.parse_args()
    print(json.dumps(run(args.rows, args.baseline_receipt, args.baseline_observations,
                         args.screen, args.review, args.output, args.java, args.comparison)['counts']))


if __name__ == '__main__':
    os.umask(0o077)
    main()
