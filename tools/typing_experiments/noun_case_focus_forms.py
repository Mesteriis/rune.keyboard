"""Dictionary-only source forms for an accusative/instrumental spelling cohort.

The sentence's existing noun supplies the target. A fixed final-letter corruption
has equal keyboard cost to both dictionary forms. No model scores are consulted;
this helper neither establishes retrieval nor admits an automatic replacement.
"""
import re

from grammar_contrast_corpus import one_edit_cost


def accusative_contrast(word, lexicon):
    if not isinstance(word, str) or not re.fullmatch('[а-яё]{4,16}', word):
        return None
    suffixes = ('ой', 'ей') if word.endswith('у') else ('ей', 'ёй') if word.endswith('ю') else ()
    if not suffixes:
        return None
    target = lexicon.analyses(word)
    if not target or any(a.pos != 'NOUN' or a.case != 'accs' or a.number != 'sing' for a in target):
        return None
    target_lemmas = {a.lemma for a in target}
    if len(target_lemmas) != 1:
        return None
    choices = []
    for suffix in suffixes:
        instrumental = word[:-1] + suffix
        rival = lexicon.analyses(instrumental)
        typed = instrumental[:-1]
        if (not rival or any(a.pos != 'NOUN' or a.case != 'ablt' or a.number != 'sing' for a in rival)
                or {a.lemma for a in rival} != target_lemmas
                or lexicon.analyses(typed)):
            continue
        costs = one_edit_cost(typed, word), one_edit_cost(typed, instrumental)
        if costs == (1., 1.):
            choices.append(dict(word=word, instrumental=instrumental, typed=typed, editCosts=list(costs)))
    # Do not resolve dictionary/orthography ambiguity with a synthetic target label.
    return choices[0] if len(choices) == 1 else None
