"""Calibrate the first accepted contextual action, not a future best/last answer.

Steps contain only source-certified proposals at completed following-word
boundaries. One source word can contribute at most one action and one gain.
"""
import math
from contextual_policy_calibration import _quantiles
from right_context_grammar_features import completed_following_words


def completed_prefixes(right_context):
    """Yield the earliest visible boundary for each completed following word.

    Keep the exact typed suffix, including punctuation. Never add a delimiter
    to an unfinished token or inspect characters beyond the feature window.
    """
    last = 0
    for end in range(1, min(len(right_context), 128) + 1):
        prefix = right_context[:end]
        count = len(completed_following_words(prefix))
        if count > last:
            yield count, prefix
            last = count


def validate_paths(paths):
    seen = set()
    for row in paths:
        if (not isinstance(row.get('id'), str) or row['id'] in seen
                or any(not isinstance(row.get(k), str) or not row[k] for k in ['original','previous','expected'])
                or type(row.get('control')) is not bool or not isinstance(row.get('steps'), list)):
            raise ValueError('RIGHT_PATH_SCHEMA')
        seen.add(row['id']);last = 0
        for step in row['steps']:
            boundary = step.get('completedWords')
            if (type(boundary) is not int or not last < boundary <= 8
                    or step.get('sourceCertified') is not True or not isinstance(step.get('proposed'), str)
                    or not step['proposed'] or step['proposed'] in {row['previous'],row['original']}
                    or any(type(step.get(k)) not in (int,float) or not math.isfinite(step[k]) for k in ['score','margin'])
                    or step['margin'] < 0):
                raise ValueError('RIGHT_PATH_STEP')
            last = boundary


def first_action(row, policy):
    if (any(type(policy.get(k)) not in (int,float) or not math.isfinite(policy[k])
            for k in ['minimumScore','minimumMargin']) or policy['minimumMargin'] <= 0):
        raise ValueError('RIGHT_PATH_POLICY')
    return next((step for step in row['steps'] if step['score'] >= policy['minimumScore']
                 and step['margin'] >= policy['minimumMargin']), None)


def path_metrics(paths, policy):
    validate_paths(paths)
    result = dict(newCorrect=0,newWrong=0,priorCorrectLosses=0,controlChanges=0,
                  installedCorrectLosses=0,installedCorrectGains=0,netCorrectVsInstalled=0,
                  acquisitions=0,revisions=0,firstBoundaryActions={})
    for row in paths:
        action = first_action(row,policy);before = row['previous'];after = action['proposed'] if action else before
        changed = after != before;good = after == row['expected'];was_good = before == row['expected']
        result['newCorrect'] += int(changed and good and not row['control'])
        result['newWrong'] += int(changed and (not good or row['control']))
        result['priorCorrectLosses'] += int(was_good and not good)
        result['installedCorrectLosses'] += int(was_good and not good)
        result['installedCorrectGains'] += int(not was_good and good)
        result['controlChanges'] += int(row['control'] and changed)
        if action:
            result['acquisitions' if before == row['original'] else 'revisions'] += 1
            key = str(action['completedWords']);result['firstBoundaryActions'][key] = result['firstBoundaryActions'].get(key,0)+1
    result['netCorrectVsInstalled'] = result['installedCorrectGains']-result['installedCorrectLosses']
    count = result['newCorrect']+result['newWrong'];result['precision'] = result['newCorrect']/count if count else None
    return result


def select_path_policy(paths, *, required_precision, minimum_correct=100, grid_points=33):
    validate_paths(paths)
    if (type(required_precision) not in (int,float) or not math.isfinite(required_precision) or not 0<required_precision<=1
            or type(minimum_correct) is not int or minimum_correct < 1 or type(grid_points) is not int or not 2<=grid_points<=65):
        raise ValueError('RIGHT_PATH_REQUIREMENTS')
    steps = [step for row in paths for step in row['steps']]
    if not steps:return None
    best = None
    for score in _quantiles([s['score'] for s in steps],grid_points):
        for margin in _quantiles([s['margin'] for s in steps],grid_points):
            if margin <= 0:continue
            policy = dict(minimumScore=score,minimumMargin=margin)
            metrics = path_metrics(paths,policy)
            if (metrics['newCorrect'] < minimum_correct or metrics['precision'] < required_precision
                    or any(metrics[k] for k in ['priorCorrectLosses','installedCorrectLosses','controlChanges'])):continue
            key = (metrics['netCorrectVsInstalled'],metrics['newCorrect'],-metrics['newWrong'],score,margin)
            if best is None or key>best[0]:best=key,dict(**policy,calibrationMetrics=metrics)
    return best[1] if best else None
