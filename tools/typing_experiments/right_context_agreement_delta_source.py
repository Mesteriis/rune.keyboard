"""Source-v5: a grammar-neutral lemma change needs evidence beyond agreement.

The current source observes number/gender/role, not the lexical meaning of later
text. It cannot justify changing an already applied pure short adjective to a
different adjective with the exact same agreement readings. Raw acquisition,
same-family inflection and changes with different agreement remain available.
"""
import unicodedata

from right_context_surface_source import SurfaceAwareContinuationSource


class AgreementDeltaSource:
    VERSION = 5

    def __init__(self, lexicon):
        self.lexicon = lexicon
        self.previous = SurfaceAwareContinuationSource(lexicon)

    def precondition_refusal(self, *, left_context, **arguments):
        return self.previous.precondition_refusal(left_context=left_context, **arguments)

    def refusal(self, *, left_context, **arguments):
        refused = self.previous.refusal(left_context=left_context, **arguments)
        if refused:
            return refused
        fold = lambda word: unicodedata.normalize('NFC', word).casefold()
        if fold(arguments['previous']) == fold(arguments['original']):
            return None
        previous = tuple(self.lexicon.analyses(arguments['previous']))
        proposed = tuple(self.lexicon.analyses(arguments['proposed']))
        if not previous or any(a.pos != 'ADJS' for a in previous):
            return None
        previous_lemmas = {a.lemma for a in previous}
        proposed_lemmas = {a.lemma for a in proposed}
        previous_agreement = {(a.number, a.gender) for a in previous}
        proposed_agreement = {(a.number, a.gender) for a in proposed}
        if previous_lemmas.isdisjoint(proposed_lemmas) and previous_agreement == proposed_agreement:
            return 'NO_NEW_AGREEMENT_FOR_LEMMA_CHANGE'
        return None
