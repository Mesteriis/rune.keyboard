"""Experimental source-v3 agreement over completed continuation evidence.

All source-v2 ownership, pool, protection, comparison and target certificates
remain mandatory. Only its final grammatical interpretation is replaced.
This is offline source admission, never editor authority or qualification.
"""
from right_context_continuation_features import (
    FEATURE_NAMES, RightContextContinuationFeatures, scan_continuation,
)
from right_context_grammar_features import _agreement
from right_context_role_features import preceding_clause_words
from right_context_source_scope import RightContextSourceScope
from right_context_subject_evidence import SubjectEvidenceLexicon

_COPULAS = frozenset(('буду', 'будешь', 'будет', 'будем', 'будете', 'будут',
                      'был', 'была', 'было', 'были'))
_REPLACED_AGREEMENT_REFUSALS = frozenset((
    None, 'CONTRADICTORY_RIGHT_NUMBER_CUE',
    'NO_SUPPORTED_RIGHT_NUMBER_CUE',
))


class ContinuationSourceScope:
    VERSION = 3

    def __init__(self, lexicon):
        self.lexicon = lexicon
        self.legacy = RightContextSourceScope(lexicon)
        self.subject_lexicon = SubjectEvidenceLexicon(lexicon)
        self.continuation = RightContextContinuationFeatures(lexicon)

    def _evidence(self, left_context, right_context, candidate):
        scan = scan_continuation(right_context)
        values = dict(zip(FEATURE_NAMES, self.continuation.extract(left_context, right_context, candidate), strict=True))
        return scan, values

    def _continuation_refusal(self, left_context, right_context, candidate):
        scan, values = self._evidence(left_context, right_context, candidate)
        if scan.ending in {'INVALID_BOUNDARY', 'NO_SEPARATOR', 'CHAR_LIMIT', 'WORD_LIMIT'}:
            return 'CONTINUATION_BOUNDARY_UNPROVEN'
        if values['continuation_finite_after_subject']:
            return 'FOLLOWING_FINITE_ROLE_UNRESOLVED'
        first_copula = bool(scan.words) and scan.words[0] in _COPULAS and any(
            a.pos == 'VERB' for a in self.lexicon.analyses(scan.words[0]))
        independent = first_copula or values['continuation_copula_after_subject'] or values['adjacent_left_copula_available']
        if independent:
            return None
        if values['continuation_reciprocal'] or values['continuation_possible_reciprocal']:
            return 'RECIPROCAL_ROLE_UNRESOLVED'
        if scan.pending_comma or values['continuation_pending_nominal_link']:
            return 'NOMINAL_LINK_INCOMPLETE'
        if scan.ending != 'STRONG_BOUNDARY':
            return 'NOMINAL_CONTINUATION_INCOMPLETE'
        return None

    def precondition_refusal(self, *, left_context, **arguments):
        refused = self.legacy.precondition_refusal(**arguments)
        if refused:
            return refused
        return self._continuation_refusal(left_context, arguments['right_context'], arguments['original'])

    def refusal(self, *, left_context, **arguments):
        # In v2 these number refusals occur only AFTER every common
        # certificate passes. Never replace a different veto with grammar.
        refused = self.legacy.refusal(**arguments)
        if refused not in _REPLACED_AGREEMENT_REFUSALS:
            return refused
        right_context = arguments['right_context']
        candidate = arguments['proposed']
        pending = self._continuation_refusal(left_context, right_context, candidate)
        if pending:
            return pending
        scan, values = self._evidence(left_context, right_context, candidate)
        predicates = tuple(self.lexicon.analyses(candidate))
        cues = []
        if values['adjacent_left_copula_available']:
            word = preceding_clause_words(left_context)[-1]
            cues.append(tuple(a for a in self.lexicon.analyses(word) if a.pos == 'VERB'))
        # Immediate right copula, or the first following finite verb in the
        # same comma-free segment. Ordinary finite verbs cannot supply a cue.
        for index, word in enumerate(scan.words):
            if scan.comma_before[index] or word in {'а', 'но'}:
                break
            finite = tuple(a for a in self.subject_lexicon.analyses(word) if a.pos == 'VERB')
            if finite:
                if word in _COPULAS:
                    cues.append(finite)
                break
        if cues:
            for cue in cues:
                number, number_conflict, _, gender_conflict = _agreement(predicates, cue)
                if number_conflict:
                    return 'CONTRADICTORY_FINITE_COPULA_NUMBER'
                if gender_conflict:
                    return 'CONTRADICTORY_FINITE_COPULA_GENDER'
                if not number:
                    return 'NO_SUPPORTED_FINITE_COPULA_NUMBER'
            return None
        # Closed, potentially coordinated postposed subjects permit more than
        # one agreement pattern. Do not universally force plural ("или" is
        # especially ambiguous), or borrow singular from the first noun alone.
        linked = (values['continuation_additive_link'] or values['continuation_alternative_link']
                  or values['continuation_comma_nominals'])
        if linked and any(a.number == 'plur' for a in predicates):
            return None
        # Unlinked/nearest-subject readings retain the v2 grammatical checks.
        return refused
