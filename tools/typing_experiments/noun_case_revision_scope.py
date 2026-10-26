"""Offline noun-case revision scope; it never grants editor admission.

An existing singular instrumental noun replacement may be reconsidered as an
unambiguous singular accusative of the same lemma after a verb-object cue.
Scoring, complete retrieval, source protection and independent admission remain
separate certificates. This scope has not been enabled in the application.
"""
from grammar_context_features import FEATURE_NAMES, GrammarContextFeatures
from grammar_revision_scope import revision_candidate as _revision_candidate


class NounCaseRevisionScope:
    VERSION = 1

    def __init__(self, lexicon):
        self.lexicon = lexicon
        self.grammar = GrammarContextFeatures(lexicon)

    def refusal(self, context, previous, proposed):
        if previous == proposed:
            return 'UNCHANGED'
        left, right = self.lexicon.analyses(previous), self.lexicon.analyses(proposed)
        if not left or any(a.pos != 'NOUN' or a.case != 'ablt' or a.number != 'sing' for a in left):
            return 'PREVIOUS_NOT_UNAMBIGUOUS_INSTRUMENTAL'
        if not right or any(a.pos != 'NOUN' or a.case != 'accs' or a.number != 'sing' for a in right):
            return 'PROPOSAL_NOT_UNAMBIGUOUS_ACCUSATIVE'
        left_lemmas, right_lemmas = {a.lemma for a in left}, {a.lemma for a in right}
        if len(left_lemmas) != 1 or left_lemmas != right_lemmas:
            return 'DIFFERENT_OR_AMBIGUOUS_LEMMA'
        features = dict(zip(FEATURE_NAMES, self.grammar.extract(context, previous, proposed)))
        return None if features['accusative_object_supported'] else 'NO_ACCUSATIVE_CUE'


def revision_candidate(scope, *, context, original, previous, proposed, generation,
                       joint_search, admission):
    candidates = joint_search.get('alternatives', [])
    if not isinstance(candidates, list) or any(not isinstance(c, dict) for c in candidates):
        return 'NO_RETRIEVED_REVISION'
    if previous not in [c.get('text') for c in candidates]:
        return 'NO_RETRIEVED_REVISION'
    if scope.lexicon.analyses(original):
        return 'ORIGINAL_PROTECTED'
    return _revision_candidate(scope, context=context, original=original, previous=previous,
                               proposed=proposed, generation=generation,
                               joint_search=joint_search, admission=admission)
