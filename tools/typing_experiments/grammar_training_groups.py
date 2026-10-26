"""Select authored contrast groups from complete production candidate evidence.

Labels select a target only after retrieval. They never create candidates or
override a known/protected original. This is preparation for training, not a gate.
"""
from collections import Counter


def select_groups(rows, observations):
    if len(rows) != len(observations) or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('CONTRAST_ROW_IDENTITY')
    groups, skipped = [], Counter()
    for row, observation in zip(rows, observations, strict=True):
        if (row.get('purpose') != 'AUTHORED_CONTRAST_TRAINING_ONLY' or row.get('split') != 'train'
                or any(observation.get(k) != row.get(k) for k in ('id', 'prefix', 'typed'))
                or observation.get('status') != 'COMPLETE'):
            raise ValueError('CONTRAST_REPLAY_IDENTITY')
        if type(row.get('noAuto')) is not bool or (row['noAuto'] and row['expectedSpelling'] != row['typed']):
            raise ValueError('CONTRAST_LABEL_SCHEMA')
        if observation.get('inputChangedByTyping'):
            skipped['input_changed'] += 1
            continue
        generation = observation.get('fullTokenGeneration') or {}
        if (type(generation.get('isValidWord')) is not bool or 'protectedReason' not in generation):
            raise ValueError('CONTRAST_GENERATION_SCHEMA')
        # prohibitsAutoReplace also covers an exhausted *baseline* search. The
        # contextual path has its own complete joint-search certificate instead.
        if not row['noAuto'] and (generation['isValidWord'] or generation['protectedReason'] is not None):
            skipped['protected_original'] += 1
            continue
        pool = observation.get('jointSearch') or {}
        source = 'joint'
        if row['noAuto'] and (pool.get('completion') != 'COMPLETE' or not pool.get('alternatives')):
            pool = observation.get('manualSearchGeneration') or {}
            source = 'manual-retention'
        if pool.get('completion') != 'COMPLETE' or not pool.get('alternatives'):
            skipped['incomplete_pool'] += 1
            continue
        original = dict(text=row['typed'], unitDistance=0, frequencyRank=2147483647,
                        editCost=0.0, isFallback=False)
        candidates = [original] + pool['alternatives']
        words = [c['text'].casefold() for c in candidates]
        if len(candidates) > 65 or len(words) != len(set(words)):
            raise ValueError('CONTRAST_CANDIDATE_POOL')
        target_word = row['expectedSpelling'].casefold()
        if target_word not in words:
            skipped['missing_target'] += 1
            continue
        # A contrast must really have both forms; no forced/fabricated rival.
        if not row['noAuto'] and not set(row['contrastCandidates']) <= set(words):
            skipped['missing_contrast'] += 1
            continue
        groups.append(dict(row=row, candidates=candidates, target=words.index(target_word),
                           source='authored-contrast-' + source))
    return groups, dict(skipped)
