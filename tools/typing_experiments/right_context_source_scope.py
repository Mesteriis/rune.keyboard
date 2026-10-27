"""Experimental following-context source certificates; never editor authority.

This independent source can reconsider a prior replacement or an unchanged typo.
It requires its own future quality qualification; legacy vetoes are not modified.
The caller must compare the original and the whole complete retrieved pool.
"""
import math
import re
from right_context_grammar_features import FEATURE_NAMES, RightContextGrammarFeatures

_WORD = re.compile('[а-яёА-ЯЁ]{3,32}\\Z')


class RightContextSourceScope:
    VERSION = 1

    def __init__(self, lexicon):
        self.lexicon = lexicon
        self.features = RightContextGrammarFeatures(lexicon)

    def precondition_refusal(self, *, right_context, original, previous, generation,
                             joint_search, previous_owned, original_selected):
        if previous_owned is not True:
            return 'PREVIOUS_OWNERSHIP_UNPROVEN'
        if type(original_selected) is not bool:
            return 'ORIGINAL_CHOICE_UNPROVEN'
        if original_selected:
            return 'EXPLICIT_ORIGINAL_CHOICE'
        if (not isinstance(original, str) or not _WORD.fullmatch(original)
                or not isinstance(previous, str) or not _WORD.fullmatch(previous)):
            return 'INVALID_WORD_INPUT'
        if (type(generation.get('isValidWord')) is not bool or 'protectedReason' not in generation
                or generation.get('original') != original):
            return 'MISSING_ORIGINAL_EVIDENCE'
        if generation['isValidWord'] or generation['protectedReason'] is not None or self.lexicon.analyses(original):
            return 'ORIGINAL_PROTECTED'
        if joint_search.get('completion') != 'COMPLETE':
            return 'SEARCH_INCOMPLETE'
        candidates = joint_search.get('alternatives')
        if (not isinstance(candidates, list) or not 1 <= len(candidates) <= 64
                or any(not isinstance(c, dict) or not isinstance(c.get('text'), str) or not _WORD.fullmatch(c['text'])
                       or c.get('language') != 'ru' or type(c.get('unitDistance')) is not int
                       or not 1 <= c['unitDistance'] <= 3 for c in candidates)):
            return 'INVALID_RETRIEVED_POOL'
        words = [c['text'] for c in candidates]
        if len(set(words)) != len(words) or original in words or (previous != original and previous not in words):
            return 'INVALID_PREVIOUS_OR_POOL'
        values = dict(zip(FEATURE_NAMES, self.features.extract(right_context, original)))
        if not (values['right_copula_available'] or values['right_subject_available']):
            return 'NO_COMPLETED_RIGHT_CUE'
        return None

    def refusal(self, *, right_context, original, previous, proposed, generation,
                joint_search, previous_owned, original_selected, external_veto_allowed, compared_words, certificates):
        refused = self.precondition_refusal(right_context=right_context, original=original, previous=previous,
            generation=generation, joint_search=joint_search, previous_owned=previous_owned, original_selected=original_selected)
        if refused:
            return refused
        if proposed == previous:
            return 'UNCHANGED'
        if proposed == original:
            return 'ORIGINAL_PREFERRED'
        if external_veto_allowed is not True:
            return 'EXTERNAL_VETO_OR_UNAVAILABLE'
        candidates = joint_search['alternatives']
        expected = [original] + [c['text'] for c in candidates]
        if list(compared_words) != expected:
            return 'INCOMPLETE_MODEL_COMPARISON'
        candidate = next((c for c in candidates if c['text'] == proposed), None)
        if candidate is None:
            return 'NO_RETRIEVED_PROPOSAL'
        cost = candidate.get('editCost')
        if (candidate.get('kind') != 'SPELLING' or candidate.get('isFallback') is not False
                or type(cost) not in (int, float) or not math.isfinite(cost) or not 0 <= cost <= 4):
            return 'INVALID_PROPOSAL_METADATA'
        certificate = certificates.get(proposed)
        keys = ['publicOriginalAllowed', 'originalMorphologyAvailable', 'originalMorphologyPresent',
                'targetMorphologyAvailable', 'targetMorphologyPresent']
        if not isinstance(certificate, dict) or any(type(certificate.get(k)) is not bool for k in keys):
            return 'MISSING_SOURCE_CERTIFICATE'
        if certificate['publicOriginalAllowed'] and certificate.get('publicOriginalRefusal') is not None:
            return 'INCONSISTENT_SOURCE_CERTIFICATE'
        if not certificate['originalMorphologyAvailable'] or not certificate['targetMorphologyAvailable']:
            return 'MORPHOLOGY_UNAVAILABLE'
        if not certificate['publicOriginalAllowed'] or certificate['originalMorphologyPresent']:
            return 'ORIGINAL_PROTECTED'
        lemma = certificate.get('targetLemmaId')
        if not certificate['targetMorphologyPresent'] or type(lemma) is not int or lemma <= 0:
            return 'TARGET_NOT_UNAMBIGUOUSLY_KNOWN'
        tags = self.lexicon.analyses(proposed)
        if (not tags or any(a.pos != 'ADJS' or a.number not in {'sing', 'plur'} for a in tags)
                or len({a.lemma for a in tags}) != 1 or len({a.number for a in tags}) != 1):
            return 'PROPOSAL_NOT_UNAMBIGUOUS_SHORT_PREDICATE'
        values = dict(zip(FEATURE_NAMES, self.features.extract(right_context, proposed)))
        if values['right_copula_number_conflict'] or values['right_subject_number_conflict']:
            return 'CONTRADICTORY_RIGHT_NUMBER_CUE'
        if values['right_copula_gender_conflict'] or values['right_subject_gender_conflict']:
            return 'CONTRADICTORY_RIGHT_GENDER_CUE'
        if not (values['right_copula_number_supported'] or values['right_subject_number_supported']):
            return 'NO_SUPPORTED_RIGHT_NUMBER_CUE'
        return None
