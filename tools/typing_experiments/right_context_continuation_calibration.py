"""First-action calibration on actual continuation events, including punctuation.

Separate from the frozen word-count-only protocol. Every accepted step must be
an exact event of the recorded suffix; later success cannot hide an early edit.
"""
import math

from contextual_policy_calibration import _quantiles
from right_context_continuation_features import continuation_prefixes
from right_context_timeline_calibration import first_action

VERSION = 1


def validate_paths(paths):
    seen = set()
    for row in paths:
        if (not isinstance(row.get('id'), str) or row['id'] in seen
                or any(not isinstance(row.get(k), str) or not row[k] for k in ('original', 'previous', 'expected'))
                or type(row.get('control')) is not bool or not isinstance(row.get('steps'), list)
                or not isinstance(row.get('rightContext'), str)):
            raise ValueError('CONTINUATION_PATH_SCHEMA')
        seen.add(row['id'])
        events = {len(prefix): (len(scan.words), prefix) for scan, prefix in continuation_prefixes(row['rightContext'])}
        last = 0
        for step in row['steps']:
            length = step.get('prefixLength')
            if (type(length) is not int or length <= last or length not in events
                    or type(step.get('completedWords')) is not int
                    or (step['completedWords'], step.get('rightContext')) != events[length]
                    or step.get('sourceCertified') is not True
                    or not isinstance(step.get('proposed'), str) or not step['proposed']
                    or step['proposed'] in {row['original'], row['previous']}
                    or any(type(step.get(k)) not in (int, float) or not math.isfinite(step[k]) for k in ('score', 'margin'))
                    or step['margin'] < 0):
                raise ValueError('CONTINUATION_PATH_STEP')
            last = length


def _metrics(paths, policy):
    first_action({'steps': []}, policy)  # Validate even an empty cohort.
    result = dict(newCorrect=0, newWrong=0, priorCorrectLosses=0, controlChanges=0,
                  installedCorrectLosses=0, installedCorrectGains=0, netCorrectVsInstalled=0,
                  acquisitions=0, revisions=0, firstBoundaryActions={})
    for row in paths:
        action = first_action(row, policy)
        before = row['previous']
        after = action['proposed'] if action else before
        changed = after != before
        good = after == row['expected']
        was_good = before == row['expected']
        result['newCorrect'] += int(changed and good and not row['control'])
        result['newWrong'] += int(changed and (not good or row['control']))
        result['priorCorrectLosses'] += int(was_good and not good)
        result['installedCorrectLosses'] += int(was_good and not good)
        result['installedCorrectGains'] += int(not was_good and good)
        result['controlChanges'] += int(row['control'] and changed)
        if action:
            result['acquisitions' if before == row['original'] else 'revisions'] += 1
            key = str(action['completedWords'])
            result['firstBoundaryActions'][key] = result['firstBoundaryActions'].get(key, 0) + 1
    result['netCorrectVsInstalled'] = result['installedCorrectGains'] - result['installedCorrectLosses']
    total = result['newCorrect'] + result['newWrong']
    result['precision'] = result['newCorrect'] / total if total else None
    return result


def path_metrics(paths, policy):
    validate_paths(paths)
    return _metrics(paths, policy)


def select_path_policy(paths, *, required_precision, minimum_correct=100, grid_points=33):
    validate_paths(paths)
    if (type(required_precision) not in (int, float) or not math.isfinite(required_precision)
            or not 0 < required_precision <= 1 or type(minimum_correct) is not int or minimum_correct < 1
            or type(grid_points) is not int or not 2 <= grid_points <= 65):
        raise ValueError('CONTINUATION_PATH_REQUIREMENTS')
    steps = [step for row in paths for step in row['steps']]
    if not steps:
        return None
    best = None
    for score in _quantiles([step['score'] for step in steps], grid_points):
        for margin in _quantiles([step['margin'] for step in steps], grid_points):
            if margin <= 0:
                continue
            policy = dict(minimumScore=score, minimumMargin=margin)
            metrics = _metrics(paths, policy)
            if (metrics['newCorrect'] < minimum_correct or metrics['precision'] < required_precision
                    or any(metrics[k] for k in ('priorCorrectLosses', 'installedCorrectLosses', 'controlChanges'))):
                continue
            key = (metrics['netCorrectVsInstalled'], metrics['newCorrect'], -metrics['newWrong'], score, margin)
            if best is None or key > best[0]:
                best = key, dict(**policy, calibrationMetrics=metrics)
    return best[1] if best else None
