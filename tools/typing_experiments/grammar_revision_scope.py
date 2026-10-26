"""Offline scope for a learned infinitive revision; never grants admission.

Only a dictionary-unambiguous finite replacement can be reconsidered, and only
for an unambiguous infinitive of the same lemma after an existing infinitive cue.
The caller separately owns source protection, retrieval, score and admission.
"""
from grammar_context_features import FEATURE_NAMES, GrammarContextFeatures


class InfinitiveRevisionScope:
    def __init__(self, lexicon):
        self.lexicon = lexicon
        self.grammar = GrammarContextFeatures(lexicon)

    def refusal(self, context, previous, proposed):
        if previous == proposed:
            return 'UNCHANGED'
        previous_tags = self.lexicon.analyses(previous)
        proposed_tags = self.lexicon.analyses(proposed)
        if not previous_tags or any(a.pos != 'VERB' for a in previous_tags):
            return 'PREVIOUS_NOT_UNAMBIGUOUS_FINITE'
        if not proposed_tags or any(a.pos != 'INFN' for a in proposed_tags):
            return 'PROPOSAL_NOT_UNAMBIGUOUS_INFINITIVE'
        if not ({a.lemma for a in previous_tags} & {a.lemma for a in proposed_tags}):
            return 'DIFFERENT_LEMMA'
        features = dict(zip(FEATURE_NAMES, self.grammar.extract(context, previous, proposed)))
        if not features['infinitive_supported']:
            return 'NO_INFINITIVE_CUE'
        return None


def revision_candidate(scope, *, context, original, previous, proposed, generation,
                       joint_search, admission):
    """Return a scope refusal or None; all certificates must be explicit."""
    if (type(generation.get('isValidWord')) is not bool or 'protectedReason' not in generation
            or type(admission.get(proposed)) is not bool):
        return 'MISSING_SOURCE_EVIDENCE'
    if generation['isValidWord'] or generation['protectedReason'] is not None:
        return 'ORIGINAL_PROTECTED'
    if joint_search.get('completion') != 'COMPLETE':
        return 'SEARCH_INCOMPLETE'
    candidates = joint_search.get('alternatives', [])
    words = [c.get('text') for c in candidates]
    if (not 1 <= len(words) <= 64 or any(not isinstance(w, str) or not w for w in words)
            or len(set(words)) != len(words)
            or proposed not in words or previous == original or proposed == original):
        return 'NO_RETRIEVED_REVISION'
    if not admission[proposed]:
        return 'SOURCE_ADMISSION_REFUSED'
    return scope.refusal(context, previous, proposed)
