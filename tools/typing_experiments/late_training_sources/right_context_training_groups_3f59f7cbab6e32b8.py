"""Bind authored right-context training rows to real, label-blind candidate queries.

Applied forms are explicit counterfactual training contrasts, not observed
production outcomes. Labels can select a retrieved candidate; never insert one.
"""
from collections import Counter
import hashlib
import json


def query(row):
    prefix = row['leftContext'].rstrip(' \t')
    typed = row['original']
    identity = json.dumps([prefix, typed], ensure_ascii=False, separators=(',', ':')).encode()
    return dict(id='right-query-' + hashlib.sha256(identity).hexdigest()[:24], prefix=prefix, typed=typed)


def select_groups(rows, observations):
    if len({r['id'] for r in rows}) != len(rows):
        raise ValueError('RIGHT_TRAINING_ROW_IDENTITY')
    queries = {query(r)['id']: query(r) for r in rows}
    indexed = {}
    for observed in observations:
        key = observed.get('id')
        if key in indexed or key not in queries:
            raise ValueError('RIGHT_QUERY_IDENTITY')
        q = queries[key]
        if observed.get('status') != 'COMPLETE' or any(observed.get(k) != q[k] for k in ('prefix', 'typed')):
            raise ValueError('RIGHT_QUERY_REPLAY_IDENTITY')
        indexed[key] = observed
    if set(indexed) != set(queries):
        raise ValueError('RIGHT_QUERY_COVERAGE')
    groups, skipped = [], Counter()
    for row in rows:
        if row.get('purpose') != 'AUTHORED_RIGHT_CONTEXT_TRAINING_ONLY' or row.get('split') != 'train':
            raise ValueError('RIGHT_TRAINING_ONLY')
        kind = row.get('kind')
        if kind not in {'unknown_original', 'correct_original', 'insufficient_right_evidence'}:
            raise ValueError('RIGHT_LABEL_KIND')
        if kind != 'unknown_original' and row['expectedApplied'] != row['applied']:
            raise ValueError('RIGHT_RETENTION_LABEL')
        if kind == 'correct_original' and row['applied'] != row['original']:
            raise ValueError('RIGHT_CORRECT_ORIGINAL')
        q = query(row); observed = indexed[q['id']]
        if observed.get('inputChangedByTyping'):
            skipped['input_changed'] += 1
            continue
        generation = observed.get('fullTokenGeneration') or {}
        if type(generation.get('isValidWord')) is not bool or 'protectedReason' not in generation:
            raise ValueError('RIGHT_GENERATION_SCHEMA')
        if kind != 'correct_original' and (generation['isValidWord'] or generation['protectedReason'] is not None):
            skipped['original_protected'] += 1
            continue
        pool = observed.get('jointSearch') or {}
        source = 'joint'
        if kind == 'correct_original' and (pool.get('completion') != 'COMPLETE' or not pool.get('alternatives')):
            pool = observed.get('manualSearchGeneration') or {}
            source = 'manual-retention'
        if pool.get('completion') != 'COMPLETE' or not pool.get('alternatives'):
            skipped['incomplete_pool'] += 1
            continue
        original = dict(text=row['original'], unitDistance=0, frequencyRank=2147483647,
                        editCost=0.0, isFallback=False)
        candidates = [original] + pool['alternatives']
        if len(candidates) > 65 or any(not isinstance(c.get('text'), str) for c in candidates):
            raise ValueError('RIGHT_CANDIDATE_POOL')
        words = [c['text'].casefold() for c in candidates]
        if len(words) != len(set(words)):
            raise ValueError('RIGHT_CANDIDATE_POOL')
        if row['applied'].casefold() not in words:
            skipped['missing_applied'] += 1
            continue
        if row['expectedApplied'].casefold() not in words:
            skipped['missing_target'] += 1
            continue
        if kind != 'correct_original' and not set(row['candidateForms']) <= set(words):
            skipped['missing_contrast'] += 1
            continue
        groups.append(dict(row=row, candidates=candidates, target=words.index(row['expectedApplied'].casefold()),
                           queryId=q['id'], source=source, counterfactualApplied=True,
                           sourceAdmission=observed.get('jointSourceAdmission', {})))
    return groups, dict(skipped)
