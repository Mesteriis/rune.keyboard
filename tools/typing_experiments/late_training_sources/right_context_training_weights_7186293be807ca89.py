"""Offline weight ablation: equal confidence for all strong authored intents.

The frozen older policy prioritizes wrong-state repair three to one over raw
acquisition and correct-state retention. This separate policy assigns all three
strong intents weight three, leaving unresolved and protected-original controls
at one. It neither reads model scores nor changes examples/features/admission.
"""

VERSION = 1


def strong_supervision_weight(row):
    if (not isinstance(row, dict)
            or row.get('purpose') != 'AUTHORED_RIGHT_CONTEXT_TRAINING_ONLY'
            or row.get('split') != 'train' or row.get('language') != 'ru'
            or any(not isinstance(row.get(key), str) or not row[key]
                   for key in ('original', 'applied', 'expectedApplied'))):
        raise ValueError('STRONG_WEIGHT_TRAINING_ROW')
    kind = row.get('kind')
    if kind == 'unknown_original':
        if row['expectedApplied'] == row['original']:
            raise ValueError('STRONG_WEIGHT_UNKNOWN_TARGET')
        return 3.
    if kind not in {'correct_original', 'insufficient_right_evidence'}:
        raise ValueError('STRONG_WEIGHT_LABEL_KIND')
    if (row['expectedApplied'] != row['applied'] or
            (kind == 'correct_original' and row['original'] != row['applied'])):
        raise ValueError('STRONG_WEIGHT_RETENTION_LABEL')
    return 1.
