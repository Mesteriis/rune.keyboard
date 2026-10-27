"""Source-v6 adds a narrow contradictory modal/infinitive agreement veto.

Only adjacent completed past мочь/смочь + infinitive быть is recognized.
No skipped token, punctuation traversal, admission expansion, reranking or
editor authority. Every earlier source-v5 refusal retains priority.
"""
import re
import unicodedata

from right_context_agreement_delta_source import AgreementDeltaSource
from right_context_grammar_features import _agreement
from right_context_role_features import preceding_clause_words

_MODALS = frozenset(('мочь', 'смочь'))


def modal_copula_cue(left_context, lexicon):
    words = preceding_clause_words(left_context)
    if len(words) < 2 or words[-1] != 'быть':
        return ()
    tail = unicodedata.normalize('NFC', left_context[-128:]).casefold()
    match = re.search(re.escape(words[-2]) + r'[ \t]+быть[ \t]+\Z', tail)
    if match is None:
        return ()
    if len(left_context) > 128 and match.start() == 0:
        before = left_context[-129]
        if before.isalnum() or before == '_' or unicodedata.category(before).startswith('M'):
            return ()
    copula = tuple(lexicon.analyses('быть'))
    modal = tuple(lexicon.analyses(words[-2]))
    if (not copula or any(a.pos != 'INFN' or a.lemma != 'быть' for a in copula)
            or not modal or any(a.pos != 'VERB' or a.lemma not in _MODALS
                or getattr(a, 'tense', None) != 'past' or a.number not in {'sing', 'plur'} for a in modal)):
        return ()
    return modal


class ModalCopulaSource:
    VERSION = 6

    def __init__(self, lexicon):
        self.lexicon = lexicon
        self.previous = AgreementDeltaSource(lexicon)

    def precondition_refusal(self, *, left_context, **arguments):
        return self.previous.precondition_refusal(left_context=left_context, **arguments)

    def refusal(self, *, left_context, **arguments):
        refused = self.previous.refusal(left_context=left_context, **arguments)
        if refused:
            return refused
        cue = modal_copula_cue(left_context, self.lexicon)
        target = tuple(self.lexicon.analyses(arguments['proposed']))
        _, number_conflict, _, gender_conflict = _agreement(target, cue)
        if number_conflict:
            return 'CONTRADICTORY_MODAL_COPULA_NUMBER'
        if gender_conflict:
            return 'CONTRADICTORY_MODAL_COPULA_GENDER'
        return None
