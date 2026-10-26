"""Calibrate contextual proposals with explicit precision and retention constraints.

This consumes calibration scores only. A stricter calibration ratio is a safety
margin, not a confidence probability or a guarantee about a future holdout.
"""
import math


def _validate(records):
    ids = set()
    for row in records:
        if not isinstance(row.get('id'), str) or row['id'] in ids:
            raise ValueError('CALIBRATION_ROW_IDENTITY')
        ids.add(row['id'])
        if (any(not isinstance(row.get(k), str) or not row[k]
                for k in ('typed', 'expected', 'baseline')) or type(row.get('control')) is not bool):
            raise ValueError('CALIBRATION_ROW_SCHEMA')
        if row['control'] and row['expected'] != row['typed']:
            raise ValueError('CALIBRATION_CONTROL_SCHEMA')
        for name in ('reference', 'experimental'):
            value = row.get(name, {})
            if (not isinstance(value.get('candidate'), str) or not value['candidate']
                    or any(type(value.get(k)) not in (float, int) or not math.isfinite(value[k])
                           for k in ('score', 'margin')) or value['margin'] < 0):
                raise ValueError('CALIBRATION_SCORE_SCHEMA')


def _policy(policy):
    if (any(type(policy.get(k)) not in (int, float) or not math.isfinite(policy[k])
            for k in ('minimumScore', 'minimumMargin')) or policy['minimumMargin'] <= 0):
        raise ValueError('CALIBRATION_POLICY_SCHEMA')


def _final(row, name, policy):
    value = row[name]
    return (value['candidate'] if value['score'] >= policy['minimumScore']
            and value['margin'] >= policy['minimumMargin'] else row['baseline'])


def _metrics(records, policy, reference_policy):
    result = dict(newCorrect=0, newWrong=0, priorCorrectLosses=0, controlChanges=0,
                  installedCorrectLosses=0, installedCorrectGains=0, netCorrectVsInstalled=0)
    for row in records:
        after = _final(row, 'experimental', policy)
        before = _final(row, 'reference', reference_policy)
        correct = after == row['expected']
        reference_correct = before == row['expected']
        if row['baseline'] == row['typed'] and after != row['typed']:
            good = correct and not row['control']
            result['newCorrect'] += good
            result['newWrong'] += not good
        result['priorCorrectLosses'] += row['baseline'] == row['expected'] and not correct
        result['controlChanges'] += row['control'] and after != row['typed']
        result['installedCorrectLosses'] += reference_correct and not correct
        result['installedCorrectGains'] += not reference_correct and correct
        result['netCorrectVsInstalled'] += int(correct) - int(reference_correct)
    total = result['newCorrect'] + result['newWrong']
    result['precision'] = result['newCorrect'] / total if total else None
    return result


def proposal_metrics(records, policy, reference_policy):
    _validate(records)
    _policy(policy)
    _policy(reference_policy)
    return _metrics(records, policy, reference_policy)


def _requirements(required_precision, minimum_new_correct):
    if (type(required_precision) not in (float, int) or not math.isfinite(required_precision)
            or not 0 < required_precision <= 1):
        raise ValueError('INVALID_REQUIRED_PRECISION')
    if type(minimum_new_correct) is not int or minimum_new_correct < 1:
        raise ValueError('INVALID_MINIMUM_VOLUME')


def accepted(metrics, *, required_precision, minimum_new_correct=100):
    _requirements(required_precision, minimum_new_correct)
    keys = ('newCorrect', 'newWrong', 'priorCorrectLosses', 'controlChanges',
            'installedCorrectLosses', 'installedCorrectGains')
    if any(type(metrics.get(k)) is not int or metrics[k] < 0 for k in keys):
        raise ValueError('INVALID_METRIC_COUNTS')
    net = metrics.get('netCorrectVsInstalled')
    if type(net) is not int or net != metrics['installedCorrectGains'] - metrics['installedCorrectLosses']:
        raise ValueError('INVALID_NET_COUNT')
    good, bad = metrics['newCorrect'], metrics['newWrong']
    # Compute from counts, never trust a rounded/reported precision field.
    return (good >= minimum_new_correct and good / (good + bad) >= required_precision
            and all(metrics[k] == 0 for k in ('priorCorrectLosses', 'controlChanges', 'installedCorrectLosses'))
            and net > 0)


def _quantiles(values, points):
    ordered = sorted(values)
    result = set()
    for i in range(points):
        position = (len(ordered) - 1) * i / (points - 1)
        low = int(position)
        fraction = position - low
        result.add(ordered[low] + fraction * (ordered[min(low + 1, len(ordered) - 1)] - ordered[low]))
    return sorted(result)


def select_policy(records, reference_policy, *, required_precision, minimum_new_correct=100, grid_points=33):
    """Return None when no calibration policy meets every constraint; no fallback."""
    _requirements(required_precision, minimum_new_correct)
    _validate(records)
    _policy(reference_policy)
    if type(grid_points) is not int or not 2 <= grid_points <= 65:
        raise ValueError('INVALID_GRID_SIZE')
    if not records:
        return None
    best = None
    for score in _quantiles([r['experimental']['score'] for r in records], grid_points):
        for margin in _quantiles([r['experimental']['margin'] for r in records], grid_points):
            if margin <= 0:
                continue
            policy = dict(minimumScore=score, minimumMargin=margin)
            metrics = _metrics(records, policy, reference_policy)
            if not accepted(metrics, required_precision=required_precision, minimum_new_correct=minimum_new_correct):
                continue
            key = (metrics['netCorrectVsInstalled'], metrics['newCorrect'], -metrics['newWrong'], score, margin)
            if best is None or key > best[0]:
                best = key, dict(**policy, calibrationMetrics=metrics)
    return best[1] if best else None
