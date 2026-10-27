"""Authored prefix training derived only from an existing authored corpus.

Natural calibration/holdout sentences are never accepted. A nominal-only early
prefix retains the counterfactual applied word; explicit clause closure or a
completed agreement cue supplies a later target. These labels describe authored
intent, not a generally valid syntactic admission rule.
"""
import hashlib
import json

from right_context_continuation_features import continuation_prefixes

VERSION = 1
_NOMINAL_SCENARIOS = frozenset(('right_pronoun', 'right_subject_noun', 'right_plural_pronoun'))
_PARTNERS = {'он': 'она', 'она': 'он', 'оно': 'оно', 'мальчик': 'девочка',
             'девочка': 'мальчик', 'письмо': 'сообщение'}
_RECIPROCALS = {'верный': ' друг другу.', 'честный': ' друг с другом.',
                'вежливый': ' друг с другом.', 'щедрый': ' друг к другу.',
                'злой': ' друг на друга.'}


def generate(parent_rows, lexicon):
    rows = {}
    identities = {}

    def add(parent, suffix, target, scenario, *, left=None, decisive=None):
        for scan, prefix in continuation_prefixes(suffix):
            row = dict(parent)
            row.pop('id')
            row['leftContext'] = parent['leftContext'] if left is None else left
            row['rightContext'] = prefix
            row['scenario'] = scenario
            row['parentTrainingId'] = parent['id']
            row['continuationCorpusVersion'] = VERSION
            row['decisivePrefixLength'] = decisive
            resolved = decisive is not None and len(prefix) >= decisive
            if parent['kind'] == 'correct_original':
                row['kind'] = 'correct_original'
                row['expectedApplied'] = parent['original']
            else:
                row['kind'] = 'unknown_original' if resolved else 'insufficient_right_evidence'
                row['expectedApplied'] = target if resolved else parent['applied']
            # Contradictory labels for the same actual model inputs fail closed,
            # even when the authored provenance/scenario differs.
            key = (row['leftContext'], prefix, row['original'], row['applied'])
            previous = identities.setdefault(key, row['expectedApplied'])
            if previous != row['expectedApplied']:
                raise ValueError('CONTRADICTORY_CONTINUATION_TRAINING_LABEL')
            row['id'] = 'right-continuation-' + hashlib.sha256(
                json.dumps(row, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:24]
            rows[row['id']] = row

    for parent in parent_rows:
        if (parent.get('purpose') != 'AUTHORED_RIGHT_CONTEXT_TRAINING_ONLY'
                or parent.get('split') != 'train'
                or parent.get('kind') not in {'unknown_original', 'correct_original', 'insufficient_right_evidence'}):
            raise ValueError('AUTHORED_CONTINUATION_PARENT_REQUIRED')
        if parent.get('scenario') not in _NOMINAL_SCENARIOS:
            # Unchanged old authored rows retain their source identities.
            rows[parent['id']] = dict(parent)
            continue
        if parent['leftContext']:
            raise ValueError('NOMINAL_PARENT_CONTEXT_CHANGED')
        subject = parent['rightContext'].strip(' \t')
        if not subject or any(not ('а' <= c <= 'я' or c == 'ё') for c in subject):
            raise ValueError('NOMINAL_PARENT_SUBJECT_CHANGED')
        target = parent['expectedApplied']
        suffix = ' ' + subject + ' .'
        add(parent, suffix, target, 'nominal_wait_then_closure', decisive=len(suffix))
        # A later ordinary finite verb exposes another possible role. Retain the
        # prior output rather than invent an adverb absent from the real pool.
        finite = 'работают' if subject == 'они' else 'работает'
        add(parent, ' ' + subject + ' ' + finite + '.', target, 'nominal_then_finite_unresolved')
        if parent['kind'] != 'correct_original':
            predicates = [a for a in lexicon.analyses(target) if a.pos == 'ADJS']
            forms = {(a.number, a.gender) for a in predicates}
            if len(forms) != 1:
                raise ValueError('CONTINUATION_TARGET_AGREEMENT_AMBIGUOUS')
            number, gender = next(iter(forms))
            copula = 'были' if number == 'plur' else {'masc': 'был', 'femn': 'была', 'neut': 'было'}[gender]
            suffix = ' ' + subject + ' ' + copula + ' '
            add(parent, suffix, target, 'nominal_wait_then_copula', decisive=len(suffix))
        if subject in _PARTNERS:
            plural = parent['candidateForms'][1]
            if not any(a.pos == 'ADJS' and a.number == 'plur' for a in lexicon.analyses(plural)):
                raise ValueError('CONTINUATION_PLURAL_FORM_REQUIRED')
            for separator, scenario in [(' и ', 'additive'), (', ', 'comma_list')]:
                suffix = ' ' + subject + separator + _PARTNERS[subject] + '.'
                add(parent, suffix, plural, scenario + '_wait_then_closure', decisive=len(suffix))
                add(parent, suffix, plural, scenario + '_left_plural_copula', left='были ', decisive=len(' ' + subject + separator[0]))
            add(parent, ' ' + subject + ' или ' + _PARTNERS[subject] + '.', target, 'alternative_role_unresolved')
        if subject == 'он' and parent['family'] in _RECIPROCALS:
            suffix = _RECIPROCALS[parent['family']]
            plural = parent['candidateForms'][1]
            add(parent, suffix, plural, 'reciprocal_without_left_subject_unresolved')
            add(parent, suffix, plural, 'reciprocal_with_left_plural_copula', left='были ', decisive=len(' друг '))
    if not rows or len(rows) != len({row['id'] for row in rows.values()}):
        raise ValueError('EMPTY_OR_DUPLICATE_CONTINUATION_CORPUS')
    return list(rows.values())
