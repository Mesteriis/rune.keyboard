"""Authored predicate repairs with oblique/homographic nominal complements.

Counterbalance instrumental-noun retention without a genitive-reading veto.
All targets are dictionary-derived inflections in existing training families.
Native complete-pool selection is still required; no natural failure text is
used and no declared contrast is injected into candidate generation.
"""
import hashlib
import itertools
import json

from grammar_contrast_corpus import shared_variants, one_edit_cost

PREDICATES = ('полезен', 'нужен', 'важен', 'верен')
COMPLEMENTS = ('аудитории', 'молодёжи', 'команде')
_FRAMES = {
    ('sing', 'masc'): 'он был ',
    ('sing', 'femn'): 'она была ',
    ('sing', 'neut'): 'это было ',
    ('plur', None): 'они были ',
}


def generate(lexicon, paradigms, *, predicates=PREDICATES, complements=COMPLEMENTS):
    for word in complements:
        if not any(a.pos == 'NOUN' and a.case == 'datv' for a in lexicon.analyses(word)):
            raise ValueError('OBLIQUE_COMPLEMENT_DICTIONARY')
    rows = {}; skipped = []
    for masculine in predicates:
        lemmas = {a.lemma for a in lexicon.analyses(masculine)
                  if a.pos == 'ADJS' and a.number == 'sing' and a.gender == 'masc'}
        if len(lemmas) != 1:
            raise ValueError('OBLIQUE_PREDICATE_DICTIONARY')
        family = next(iter(lemmas))
        forms = {}
        for role in _FRAMES:
            matching = {word for word in paradigms.get(masculine, ()) if any(
                a.pos == 'ADJS' and a.lemma == family and a.number == role[0]
                and (role[0] == 'plur' or a.gender == role[1])
                and not {'Supr', 'Cmp2'} & set(getattr(a, 'grammemes', ()))
                for a in lexicon.analyses(word))}
            if matching:
                forms[role] = min(matching, key=lambda word: (len(word), word))
            else:
                skipped.append(dict(family=family, role=list(role), reason='MISSING_SHORT_FORM'))
        for (left_role, first), (right_role, second) in itertools.combinations(forms.items(), 2):
            if first == second:
                raise ValueError('OBLIQUE_IDENTICAL_ROLE_FORMS')
            variants = shared_variants(first, second, lexicon, edit_profiles=True)
            if not variants:
                skipped.append(dict(family=family, forms=[first, second], reason='NO_SHARED_UNKNOWN'))
                continue

            def add(original, applied, target, left, right, kind, scenario):
                row = dict(purpose='AUTHORED_RIGHT_CONTEXT_TRAINING_ONLY', split='train', language='ru',
                    family=family, original=original, applied=applied, expectedApplied=target,
                    leftContext=left, rightContext=right, candidateForms=[first, second],
                    kind=kind, scenario=scenario, authoringProfile='oblique-predicate-v1')
                if kind != 'correct_original':
                    row['contrastEditCosts'] = [one_edit_cost(original, form) for form in (first, second)]
                row['id'] = 'right-oblique-' + hashlib.sha256(
                    json.dumps(row, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:24]
                rows[row['id']] = row

            for role, target in ((left_role, first), (right_role, second)):
                left = _FRAMES[role]
                for complement in complements:
                    suffix = ' ' + complement + '.'
                    for original in variants:
                        for applied in (original, first, second):
                            add(original, applied, target, left, suffix, 'unknown_original', 'predicate_oblique_complement')
                    for original in (first, second):
                        add(original, original, original, left, suffix, 'correct_original', 'predicate_oblique_complement')
                for original in variants:
                    for applied in (original, first, second):
                        add(original, applied, applied, left, ' ', 'insufficient_right_evidence', 'oblique_suffix_unfinished')
    if not rows:
        raise ValueError('EMPTY_OBLIQUE_CORPUS')
    return list(rows.values()), skipped
