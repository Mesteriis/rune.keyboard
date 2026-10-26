"""Offline scope for revising an admitted short-predicate number replacement.

Completed right-context evidence is not editor ownership. Complete retrieval,
explicit prior/proposal admission and positive packed lemma IDs are independent
certificates. Every refusal retains the observed previous result.
"""
from right_context_grammar_features import FEATURE_NAMES, RightContextGrammarFeatures


class RightContextRevisionScope:
    VERSION = 2

    def __init__(self, lexicon, packed_lemmas):
        self.lexicon = lexicon
        self.packed_lemmas = packed_lemmas
        self.features = RightContextGrammarFeatures(lexicon)

    def _predicate(self, word):
        tags = self.lexicon.analyses(word)
        if (not tags or any(a.pos != 'ADJS' or a.number not in {'sing', 'plur'} for a in tags)
                or len({a.lemma for a in tags}) != 1 or len({a.number for a in tags}) != 1):
            return None
        return tags

    def precondition_refusal(self, *, right_context, original, previous, generation,
                             joint_search, previous_admitted):
        if previous_admitted is not True or previous == original:
            return 'NO_ADMITTED_PREVIOUS_REPLACEMENT'
        if (type(generation.get('isValidWord')) is not bool or 'protectedReason' not in generation
                or generation.get('original') != original):
            return 'MISSING_ORIGINAL_EVIDENCE'
        if generation['isValidWord'] or generation['protectedReason'] is not None or self.lexicon.analyses(original):
            return 'ORIGINAL_PROTECTED'
        if joint_search.get('completion') != 'COMPLETE':
            return 'SEARCH_INCOMPLETE'
        candidates = joint_search.get('alternatives')
        if (not isinstance(candidates, list) or not 1 <= len(candidates) <= 64
                or any(not isinstance(c, dict) or not isinstance(c.get('text'), str) or not c['text']
                       or c.get('language') != 'ru' or type(c.get('unitDistance')) is not int
                       or not 1 <= c['unitDistance'] <= 3 for c in candidates)):
            return 'INVALID_RETRIEVED_POOL'
        words = [c['text'] for c in candidates]
        if len(set(words)) != len(words) or previous not in words or original in words:
            return 'NO_RETRIEVED_PREVIOUS'
        if self._predicate(previous) is None:
            return 'PREVIOUS_NOT_UNAMBIGUOUS_SHORT_PREDICATE'
        lemma = self.packed_lemmas.get(previous)
        if type(lemma) is not int or lemma <= 0:
            return 'PACKED_LEMMA_UNAVAILABLE'
        features = dict(zip(FEATURE_NAMES, self.features.extract(right_context, previous)))
        if not (features['right_copula_number_conflict'] or features['right_subject_number_conflict']):
            return 'NO_COMPLETED_RIGHT_NUMBER_CONFLICT'
        return None

    def refusal(self, *, right_context, original, previous, proposed, generation,
                joint_search, previous_admitted, admission):
        refused = self.precondition_refusal(right_context=right_context, original=original, previous=previous,
            generation=generation, joint_search=joint_search, previous_admitted=previous_admitted)
        if refused:
            return refused
        if proposed == previous:
            return 'UNCHANGED'
        if proposed == original or proposed not in [c['text'] for c in joint_search['alternatives']]:
            return 'NO_RETRIEVED_REVISION'
        if type(admission.get(proposed)) is not bool:
            return 'MISSING_PROPOSAL_ADMISSION'
        if not admission[proposed]:
            return 'PROPOSAL_ADMISSION_REFUSED'
        before, after = self._predicate(previous), self._predicate(proposed)
        if after is None:
            return 'PROPOSAL_NOT_UNAMBIGUOUS_SHORT_PREDICATE'
        if {a.lemma for a in before} != {a.lemma for a in after}:
            return 'DIFFERENT_DICTIONARY_LEMMA'
        old, new = self.packed_lemmas.get(previous), self.packed_lemmas.get(proposed)
        if type(new) is not int or new <= 0:
            return 'PACKED_LEMMA_UNAVAILABLE'
        if old != new:
            return 'DIFFERENT_PACKED_LEMMA'
        if {a.number for a in before} == {a.number for a in after}:
            return 'NUMBER_UNCHANGED'
        left = dict(zip(FEATURE_NAMES, self.features.extract(right_context, previous)))
        right = dict(zip(FEATURE_NAMES, self.features.extract(right_context, proposed)))
        if right['right_copula_number_conflict'] or right['right_subject_number_conflict']:
            return 'CONTRADICTORY_RIGHT_NUMBER_CUE'
        if right['right_copula_gender_conflict'] or right['right_subject_gender_conflict']:
            return 'CONTRADICTORY_RIGHT_GENDER_CUE'
        supported = any(left[f'right_{cue}_number_conflict'] and right[f'right_{cue}_number_supported']
                        for cue in ['copula', 'subject'])
        return None if supported else 'NO_MATCHING_COMPLETED_RIGHT_CUE'
