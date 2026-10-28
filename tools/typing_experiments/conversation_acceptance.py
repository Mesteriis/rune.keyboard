"""Offline proposal acceptance; precision is a measured ratio, not model confidence."""
import math


def candidate_gate(metrics, *, required_precision, minimum_new_correct=100):
    if not math.isfinite(required_precision) or not 0 < required_precision <= 1:
        raise ValueError('INVALID_REQUIRED_PRECISION')
    if type(minimum_new_correct) is not int or minimum_new_correct < 1:
        raise ValueError('INVALID_MINIMUM_VOLUME')
    counts = [metrics[name] for name in ('newCorrect', 'newWrong', 'controlChanges', 'priorCorrectLosses')]
    if any(type(value) is not int or value < 0 for value in counts):
        raise ValueError('INVALID_METRIC_COUNTS')
    if type(metrics['netCorrect']) is not int:
        raise ValueError('INVALID_NET_CORRECT_COUNT')
    correct, wrong, controls, losses = counts
    return (correct >= minimum_new_correct
            and correct / (correct + wrong) >= required_precision
            and controls == 0 and losses == 0 and metrics['netCorrect'] > 0)
