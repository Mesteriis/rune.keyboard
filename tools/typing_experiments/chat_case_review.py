#!/usr/bin/env python3
"""Audit post-hoc capitalization labels, never independent qualification."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from chat_control_review import verify_exclusions
from holdout_ledger import load_ledger
from typing_quality_slices import evaluate, read

PURPOSE = 'POSTHOC_DISCLOSED_CASE_REGRESSION_NOT_QUALIFICATION'
LABELS = frozenset(('lowercase_preserve', 'proper_name', 'ambiguous'))


def audit(rows, observations, review):
    evaluate(rows, observations)
    if review.get('schema') != 1 or review.get('purpose') != PURPOSE:
        raise ValueError('CASE_REVIEW_SCOPE')
    cases = review.get('cases')
    if not isinstance(cases, list) or not cases or len({c['id'] for c in cases}) != len(cases):
        raise ValueError('CASE_REVIEW_IDS')
    indexed = {r['id']: (r, o) for r, o in zip(rows, observations, strict=True)}
    case_changes = set()
    for row, obs in zip(rows, observations, strict=True):
        if row.get('edit_kind') != 'control' or not obs['boundaryChangedBeyondInsertedSpace']:
            continue
        before = obs['beforeBoundary']['text']
        after = obs['afterBoundary']['text']
        if after.casefold() == (before + ' ').casefold():
            case_changes.add(row['id'])
    if {c['id'] for c in cases} != case_changes:
        raise ValueError('CASE_REVIEW_COVERAGE')
    counts = Counter()
    for case in cases:
        if set(case) != {'id', 'typed', 'baseline', 'label'} or case['label'] not in LABELS:
            raise ValueError('CASE_REVIEW_SCHEMA')
        row, obs = indexed[case['id']]
        typed = case['typed']
        if (row.get('edit_kind') != 'control' or row.get('cohort') != 'correct'
                or row.get('noAuto') is not True or row.get('typed') != typed
                or row.get('expectedSpelling') != typed):
            raise ValueError('CASE_REVIEW_ROW')
        before = obs['beforeBoundary']['text']
        if not typed or not before.endswith(typed):
            raise ValueError('CASE_REVIEW_PREFIX')
        prefix = before[:-len(typed)]
        if obs['afterBoundary']['text'] != prefix + case['baseline'] + ' ':
            raise ValueError('CASE_REVIEW_BASELINE')
        counts[case['label']] += 1
    return {'purpose': PURPOSE, 'counts': dict(sorted(counts.items())),
            'independentQualification': False}


def compare(rows, observations, review):
    """Compare disclosed lowercase controls and apparent-name source-case contrasts."""
    evaluate(rows, observations)
    if review.get('schema') != 1 or review.get('purpose') != PURPOSE:
        raise ValueError('CASE_REVIEW_SCOPE')
    cases = review.get('cases')
    if not isinstance(cases, list) or not cases or len({c['id'] for c in cases}) != len(cases):
        raise ValueError('CASE_REVIEW_IDS')
    indexed = {r['id']: (r, o) for r, o in zip(rows, observations, strict=True)}
    failures = []
    checked = 0
    name_failures = []
    name_checked = 0
    ambiguous = 0
    for case in cases:
        if set(case) != {'id', 'typed', 'baseline', 'label'} or case['label'] not in LABELS:
            raise ValueError('CASE_REVIEW_SCHEMA')
        if case['id'] not in indexed:
            raise ValueError('CASE_REVIEW_MISSING')
        row, obs = indexed[case['id']]
        if (row.get('edit_kind') != 'control' or row.get('cohort') != 'correct'
                or row.get('noAuto') is not True or row.get('typed') != case['typed']
                or row.get('expectedSpelling') != case['typed']):
            raise ValueError('CASE_REVIEW_ROW')
        before = obs['beforeBoundary']['text']
        if not case['typed'] or not before.endswith(case['typed']):
            raise ValueError('CASE_REVIEW_PREFIX')
        if (not isinstance(case['baseline'], str) or case['baseline'] == case['typed']
                or case['baseline'].casefold() != case['typed'].casefold()):
            raise ValueError('CASE_REVIEW_BASELINE')
        if case['label'] == 'lowercase_preserve':
            checked += 1
            if obs['afterBoundary']['text'] != before + ' ':
                failures.append(case['id'])
        elif case['label'] == 'proper_name':
            name_checked += 1
            prefix = before[:-len(case['typed'])]
            if obs['afterBoundary']['text'] != prefix + case['baseline'] + ' ':
                name_failures.append(case['id'])
        else:
            ambiguous += 1
    if not checked:
        raise ValueError('CASE_REVIEW_EMPTY_PRESERVE')
    return {'purpose': PURPOSE, 'checked': checked, 'preserved': checked - len(failures),
            'failureIds': sorted(failures), 'apparentNameChecked': name_checked,
            'apparentNameSourceCaseMatched': name_checked - len(name_failures),
            'apparentNameFailureIds': sorted(name_failures), 'ambiguousExcluded': ambiguous,
            'independentQualification': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('rows', 'observations', 'review', 'ledger', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--mode', choices=('baseline', 'compare'), default='baseline')
    args = p.parse_args()
    paths = {name: getattr(args, name) for name in ('rows', 'observations', 'review', 'ledger')}
    def digest(path):
        with path.open('rb') as f:
            return hashlib.file_digest(f, 'sha256').hexdigest()
    hashes = {name: digest(path) for name, path in paths.items()}
    rows, observations = read(args.rows), read(args.observations)
    review = json.loads(args.review.read_text())
    verify_exclusions(rows, review, load_ledger(args.ledger))
    result = (audit if args.mode == 'baseline' else compare)(rows, observations, review)
    if any(digest(path) != hashes[name] for name, path in paths.items()):
        raise ValueError('CASE_REVIEW_INPUT_DRIFT')
    result['inputs'] = hashes
    result['auditSha256'] = digest(Path(__file__))
    with args.output.open('x') as f:
        json.dump(result, f, ensure_ascii=False, sort_keys=True, indent=2)
        f.write('\n')
    print(json.dumps(result.get('counts', {'checked': result.get('checked'), 'preserved': result.get('preserved')})))


if __name__ == '__main__':
    main()
