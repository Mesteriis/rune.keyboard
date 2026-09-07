#!/usr/bin/env python3
"""Calibration-only selection. Current release selects the reviewed finite table, never broad ranking.

No new numeric threshold is selected: the previous general-local independent holdout
failed 99% in every language. Revealed holdout cannot be reused for threshold selection.
"""
import argparse
import json
from pathlib import Path
from evaluate_local_holdout import metrics


def select(rows, observations, artifacts):
    if not rows or any(r['split'] != 'calibration' for r in rows):
        raise ValueError('CALIBRATION_ONLY')
    if len(rows) != len(observations) or any(r['id'] != o['id'] or o['split'] != 'calibration'
            or o['status'] != 'COMPLETE' for r, o in zip(rows, observations)):
        raise ValueError('CALIBRATION_REPLAY_IDENTITY')
    if any(o['currentQualificationWithoutModel'] for o in observations):
        raise ValueError('GENERAL_LOCAL_MUST_REMAIN_DISABLED')
    calibration_metrics = {lang: metrics([r for r in rows if r['language'] == lang],
        [o for o in observations if o['language'] == lang]) for lang in ('en', 'ru', 'es')}
    for result in calibration_metrics.values():
        if any(result[key] for key in ('protectedFalseChanges', 'correctFalseChanges', 'undoFailures',
                                      'originalRetentionFailures')) or result['replacements'] and not result['pass']:
            raise ValueError('CALIBRATION_SAFETY_GATE')
    return {'schemaVersion': 1, 'policy': 'common-confusions-v1', 'generalLocalEnabled': False,
            'minimumPrecisionPercent': 99, 'holdoutExecuted': False, 'artifacts': artifacts,
            'calibrationIds': [r['id'] for r in rows],
            'calibrationMetrics': calibration_metrics,
            'reason': 'Frozen broad-rule holdout failed 99%; no new broad thresholds fitted.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('rows', 'observations', 'artifacts', 'output'): p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    read = lambda path: [json.loads(line) for line in path.read_text().splitlines()]
    with a.output.open('x') as f:
        json.dump(select(read(a.rows), read(a.observations), json.loads(a.artifacts.read_text())), f, indent=2)
