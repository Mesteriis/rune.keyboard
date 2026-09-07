#!/usr/bin/env python3
"""Independent fixed-policy holdout evaluator; cannot select or adjust policy thresholds."""
import argparse
import json
from pathlib import Path


def validate_input(row, observation):
    if observation.get('status') != 'COMPLETE' or any(row.get(key) != observation.get(key)
            for key in ('id', 'typed', 'language', 'split')) or \
            observation.get('prefix') != row.get('prefix', ''):
        raise ValueError('REPLAY_IDENTITY')


def metrics(rows, observations):
    replaced = correct = protected_false = correct_false = undo_failures = original_failures = other_changes = 0
    for row, obs in zip(rows, observations, strict=True):
        validate_input(row, obs)
        changed = obs['boundaryChangedBeyondInsertedSpace'] or obs['inputChangedByTyping']
        alternatives = obs['fullTokenGeneration']['alternatives']
        if alternatives and not any(c['role'] == 'ORIGINAL' and c['text'] == row['typed']
                for c in obs['candidateView']['candidates']): original_failures += 1
        if changed:
            finite = any(c.get('kind') == 'COMMON_CONFUSION' for c in alternatives)
            replaced += finite
            other_changes += not finite
            prefix = row.get('prefix', '')
            expected = (prefix + ' ' if prefix else '') + (row.get('expectedSpelling') or row['typed']) + ' '
            correct += finite and row['cohort'] == 'typo' and not row['noAuto'] and obs['afterBoundary']['text'] == expected
            protected_false += row['cohort'] == 'protected' or row['noAuto']
            correct_false += row['cohort'] == 'correct'
            undo_failures += not obs['restoredBeforeBoundaryExactly']
    return {'rows': len(rows), 'replacements': replaced, 'correctReplacements': correct,
            'pointPrecision': correct / replaced if replaced else None, 'otherAutomaticChanges': other_changes,
            'protectedFalseChanges': protected_false, 'correctFalseChanges': correct_false,
            'undoFailures': undo_failures, 'originalRetentionFailures': original_failures,
            'pass': bool(replaced and correct * 100 >= replaced * 99 and
                         not (protected_false or correct_false or undo_failures or original_failures))}


def evaluate(config, rows, observations, artifacts):
    if config.get('policy') != 'common-confusions-v1' or config.get('generalLocalEnabled') is not False:
        raise ValueError('UNSUPPORTED_POLICY')
    if config['artifacts'] != artifacts: raise ValueError('ARTIFACT_DRIFT')
    if not rows or any(r['split'] != 'holdout' for r in rows): raise ValueError('HOLDOUT_ONLY')
    if any(r['language'] not in ('en', 'ru', 'es') for r in rows): raise ValueError('HOLDOUT_LANGUAGE')
    if set(config['calibrationIds']) & {r['id'] for r in rows}: raise ValueError('SPLIT_OVERLAP')
    if len(rows) != len(observations) or any(r['id'] != o['id'] or o['split'] != 'holdout'
            or o['currentQualificationWithoutModel'] for r, o in zip(rows, observations)):
        raise ValueError('HOLDOUT_REPLAY_IDENTITY')
    for row, observation in zip(rows, observations, strict=True): validate_input(row, observation)
    languages = {lang: metrics(
                [r for r in rows if r['language'] == lang], [o for o in observations if o['language'] == lang])
                for lang in ('en', 'ru', 'es')}
    for language, result in languages.items():
        if any(result[key] for key in ('protectedFalseChanges', 'correctFalseChanges',
                'undoFailures', 'originalRetentionFailures')) or result['replacements'] and not result['pass']:
            raise ValueError('HOLDOUT_GATE_FAILED:' + language)
        result['qualification'] = 'QUALIFIED' if result['pass'] else 'NO_COVERAGE'
    return {'split': 'holdout', 'holdoutExecuted': True, 'thresholdsFittedOnHoldout': False,
            'generalLocalEnabled': False, 'observedGatePassed': True,
            'allLanguagesQualified': all(r['pass'] for r in languages.values()), 'languages': languages}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('config', 'rows', 'observations', 'artifacts', 'output'): p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    read = lambda path: [json.loads(line) for line in path.read_text().splitlines()]
    result = evaluate(json.loads(a.config.read_text()), read(a.rows), read(a.observations), json.loads(a.artifacts.read_text()))
    with a.output.open('x') as f: json.dump(result, f, indent=2)
