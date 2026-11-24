#!/usr/bin/env python3
"""Compare observations exactly, with an opt-in bound for baseline score diagnostics."""
from __future__ import annotations

import argparse
import hashlib
import gzip
import json
import os
from pathlib import Path
import re
import sys

MAX_LINE_BYTES = 1024 * 1024
MAX_TOTAL_BYTES = 256 * 1024 * 1024

TIMING_FIELDS = frozenset({'fullTokenGenerationNanos', 'hostStageNanos'})
REQUIRED_FIELDS = frozenset({'index', 'id', 'language', 'split', 'prefix', 'typed', 'status',
    'beforeBoundary', 'afterBoundary', 'afterBackspace', 'boundaryCommands', 'backspaceCommands',
    'stateAfterBoundary', 'stateAfterBackspace'})

# Two binary64 ULPs at 1.0, limited to diagnostic model scores. Product
# decisions and the two runs' determinism remain exact.
BASELINE_SCORE_ABS_TOLERANCE = 4.440892098500626e-16
SCORE_PATH = re.compile(r'^/(?:jointModelScores|rescueModelScores)/[0-9]+$|'
                        r'^/compactScores/[0-9]+/(?:combinedScore|contextScore)$')


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ValueError('DUPLICATE_JSON_KEY:' + key)
        result[key] = value
    return result


def invalid_constant(value):
    raise ValueError('NONFINITE_JSON:' + value)


def read_projection(path):
    rows, identities = [], set()
    path = Path(path)
    opener = gzip.open if path.suffix == '.gz' else open
    total = 0
    with opener(path, 'rb') as stream:
        for index, raw in enumerate(iter(lambda: stream.readline(MAX_LINE_BYTES + 1), b'')):
            total += len(raw)
            if len(raw) > MAX_LINE_BYTES or total > MAX_TOTAL_BYTES:
                raise ValueError('OBSERVATION_SIZE_LIMIT')
            row = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object, parse_constant=invalid_constant)
            if not isinstance(row, dict) or not REQUIRED_FIELDS <= row.keys():
                raise ValueError(f'OBSERVATION_SHAPE:{index + 1}')
            canonical(row)  # Also reject overflowed JSON exponents anywhere in the row.
            if row['status'] != 'COMPLETE': raise ValueError(f'OBSERVATION_INCOMPLETE:{index + 1}')
            if type(row['index']) is not int or row['index'] != index:
                raise ValueError(f'OBSERVATION_INDEX:{index + 1}')
            if not isinstance(row['id'], str) or not row['id'] or row['id'] in identities:
                raise ValueError(f'OBSERVATION_ID:{index + 1}')
            if row['language'] not in ('en', 'ru', 'es') or row['split'] not in ('train', 'calibration', 'holdout'):
                raise ValueError(f'OBSERVATION_SCOPE:{index + 1}')
            identities.add(row['id'])
            rows.append({key: value for key, value in row.items() if key not in TIMING_FIELDS})
    if not rows: raise ValueError('EMPTY_OBSERVATIONS')
    return rows


def projection_bytes(rows):
    return b''.join(canonical(row) + b'\n' for row in rows)


def changed_paths(before, after, path='', *, score_tolerance=0.0):
    # Explicitly compare types too: Python otherwise treats true and 1 as equal.
    if type(before) is not type(after): return [path or '/']
    if isinstance(before, dict):
        paths = []
        for key in sorted(before.keys() | after.keys()):
            child = path + '/' + key.replace('~', '~0').replace('/', '~1')
            paths.extend([child] if key not in before or key not in after
                         else changed_paths(before[key], after[key], child, score_tolerance=score_tolerance))
        return paths
    if isinstance(before, list):
        paths = []
        for index in range(max(len(before), len(after))):
            child = path + '/' + str(index)
            paths.extend([child] if index >= min(len(before), len(after))
                         else changed_paths(before[index], after[index], child, score_tolerance=score_tolerance))
        return paths
    if (score_tolerance and type(before) is float and SCORE_PATH.fullmatch(path)
            and abs(before - after) <= score_tolerance):
        return []
    return [] if before == after else [path or '/']


def compare(baseline, candidate, *, score_tolerance=0.0):
    if score_tolerance not in (0.0, BASELINE_SCORE_ABS_TOLERANCE):
        raise ValueError('REPLAY_SCORE_TOLERANCE')
    differences = []
    tolerated = 0
    for index in range(max(len(baseline), len(candidate))):
        old = baseline[index] if index < len(baseline) else None
        new = candidate[index] if index < len(candidate) else None
        paths = changed_paths(old, new, score_tolerance=score_tolerance)
        if score_tolerance:
            tolerated += len(changed_paths(old, new)) - len(paths)
        if paths: differences.append({'row': index + 1, 'baselineId': old['id'] if old else None,
            'candidateId': new['id'] if new else None, 'paths': paths})
    return {'schemaVersion': 1, 'excludedTopLevelFields': sorted(TIMING_FIELDS),
        'baselineRows': len(baseline), 'candidateRows': len(candidate),
        'baselineProjectionSha256': hashlib.sha256(projection_bytes(baseline)).hexdigest(),
        'candidateProjectionSha256': hashlib.sha256(projection_bytes(candidate)).hexdigest(),
        'differentRows': len(differences), 'differences': differences, 'passed': not differences,
        'scoreAbsoluteTolerance': score_tolerance, 'toleratedScoreDifferences': tolerated}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args(argv)
    report = compare(read_projection(args.baseline), read_projection(args.candidate))
    with args.report.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ('passed', 'differentRows', 'candidateRows',
        'candidateProjectionSha256')}, sort_keys=True))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    os.umask(0o077)
    try: sys.exit(main())
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(2)
