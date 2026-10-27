"""Dictionary-only number contrasts for natural following-copula contexts.

The source word is a target, never a model proposal. Paradigm candidates are
independently rechecked against dictionary-only analyses before selecting a
shared corruption by fixed geometry. This does not establish retrieval/admission.
"""
import re
from grammar_contrast_corpus import shared_variants, one_edit_cost


def source_surface_refusal(surface, normalized_word):
    """Require an actual lowercase source token before making an adjective label.

    A normalized dictionary form cannot establish the role of a capitalized
    proper-name homograph. Such tokens need a separately reviewed cohort.
    """
    if not isinstance(surface, str) or not re.fullmatch('[а-яё]{3,20}', surface):
        return 'SOURCE_SURFACE_NOT_PLAIN_LOWERCASE'
    if surface != normalized_word:
        return 'SOURCE_SURFACE_CHANGED'
    return None


def predicate_contrast(word, lexicon, paradigm):
    if not isinstance(word, str) or not re.fullmatch('[а-яё]{3,20}', word):
        return None
    target = lexicon.analyses(word)
    if not target or any(a.pos != 'ADJS' or a.number not in {'sing', 'plur'} for a in target):
        return None
    lemmas, numbers = {a.lemma for a in target}, {a.number for a in target}
    if len(lemmas) != 1 or len(numbers) != 1:
        return None
    other_number = 'plur' if next(iter(numbers)) == 'sing' else 'sing'
    # Prefer masculine singular as a rival, then a stable lexical order, not scores.
    eligible = []
    for rival in sorted(set(paradigm)):
        if not re.fullmatch('[а-яё]{3,20}', rival):
            continue
        tags = lexicon.analyses(rival)
        if not tags or any(a.pos != 'ADJS' or a.number != other_number for a in tags) or {a.lemma for a in tags} != lemmas:
            continue
        eligible.append((not all(a.gender == 'masc' for a in tags), rival))
    for _, rival in sorted(eligible):
        variants = shared_variants(word, rival, lexicon, edit_profiles=True)
        if variants:
            typed = variants[0]
            return dict(word=word, rival=rival, typed=typed, family=next(iter(lemmas)),
                        editCosts=[one_edit_cost(typed, form) for form in (word, rival)])
    return None
