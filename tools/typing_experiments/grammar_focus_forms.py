"""Dictionary-verified source forms for a focused infinitive spelling cohort.

The natural source word supplies the target. The fixed shared corruption favors
the finite rival by keyboard cost; neither a model nor a label chooses the pair.
This helper does not claim candidate retrieval or editor admission.
"""
import re

from grammar_contrast_corpus import one_edit_cost


def infinitive_contrast(word, lexicon):
    if not isinstance(word, str) or not re.fullmatch('[а-яё]{4,16}', word):
        return None
    if word.endswith('иться'):
        finite, typed = word[:-4] + 'шься', word[:-4] + 'щься'
    elif word.endswith('ить'):
        finite, typed = word[:-2] + 'шь', word[:-2] + 'щь'
    else:
        return None
    target_tags, finite_tags = lexicon.analyses(word), lexicon.analyses(finite)
    if (not target_tags or any(a.pos != 'INFN' for a in target_tags)
            or not finite_tags or any(a.pos != 'VERB' for a in finite_tags)
            or not any(a.person == '2per' and a.number == 'sing' for a in finite_tags)
            or not ({a.lemma for a in target_tags} & {a.lemma for a in finite_tags})
            or lexicon.analyses(typed)):
        return None
    costs = one_edit_cost(typed, word), one_edit_cost(typed, finite)
    if costs != (1., .75):
        raise ValueError('FOCUSED_EDIT_COST_PROFILE')
    return dict(word=word, finite=finite, typed=typed, editCosts=list(costs))
