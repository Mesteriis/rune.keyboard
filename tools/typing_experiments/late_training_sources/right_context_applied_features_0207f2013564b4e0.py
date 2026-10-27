"""Observed applied-word role/lemma evidence, never a blanket revision ban.

Appends a new schema to the frozen 202 fields. Known-word status is independently
looked up, not copied from a target label. Role changes and lexical ambiguity
remain soft observations so a wrong noun/full-adjective replacement can still
be repaired when the context supports it.
"""
import math
from numbers import Real
import unicodedata

from right_context_continuation_features import FEATURES as PREVIOUS_FEATURES
from right_context_role_features import preceding_clause_words
from right_context_subject_evidence import SubjectEvidenceLexicon

VERSION = 1
FEATURE_NAMES = (
    'original_dictionary_available', 'candidate_is_original', 'applied_is_original',
    'applied_dictionary_available', 'applied_predicate_only', 'applied_has_noun',
    'applied_has_full_adjective', 'applied_has_adverb', 'applied_has_other_part',
    'applied_adjective_lemma_ambiguous', 'candidate_same_adjective_lemma',
    'candidate_different_adjective_lemma', 'candidate_has_noun', 'candidate_has_full_adjective',
    'left_modifier_available', 'left_modifier_case_supported', 'left_modifier_case_conflict',
    'left_pronoun_nominative', 'left_modifier_ambiguous',
)
FEATURES = PREVIOUS_FEATURES + len(FEATURE_NAMES)
_ADJECTIVES = frozenset(('ADJF', 'ADJS', 'PRTF', 'PRTS'))


def _word(word):
    if not isinstance(word, str) or not 1 <= len(word) <= 64:
        raise ValueError('APPLIED_WORD_SCHEMA')
    folded = unicodedata.normalize('NFC', word).casefold()
    if not 1 <= len(folded) <= 32 or any(not ('а' <= c <= 'я' or c == 'ё') for c in folded):
        raise ValueError('APPLIED_WORD_SCHEMA')
    return folded


class AppliedWordFeatures:
    def __init__(self, lexicon):
        self.lexicon = lexicon
        self.subject_lexicon = SubjectEvidenceLexicon(lexicon)

    def extract(self, left_context, original, applied, candidate):
        original, applied, candidate = map(_word, (original, applied, candidate))
        original_tags = tuple(self.lexicon.analyses(original))
        previous = tuple(self.lexicon.analyses(applied))
        target = tuple(self.lexicon.analyses(candidate))
        previous_lemmas = {a.lemma for a in previous if a.pos in _ADJECTIVES}
        candidate_lemmas = {a.lemma for a in target if a.pos in _ADJECTIVES}
        words = preceding_clause_words(left_context)
        left = ()
        bounded_left = unicodedata.normalize('NFC', left_context[-128:]).lower().rstrip(' \t')
        if words and bounded_left.endswith(words[-1]):
            left = tuple(self.subject_lexicon.analyses(words[-1]))
        modifiers = tuple(a for a in left if a.pos in {'ADJF', 'PRTF'})
        nominals = tuple(a for a in target if a.pos in {'NOUN', 'NPRO', 'ADJF', 'PRTF'})
        left_cases = {a.case for a in modifiers if a.case is not None}
        target_cases = {a.case for a in nominals if a.case is not None}
        case_known = bool(modifiers) and bool(nominals) and all(a.case is not None for a in modifiers + nominals)
        values = (bool(original_tags), candidate == original, applied == original,
                  bool(previous), bool(previous) and all(a.pos in {'ADJS', 'PRTS'} for a in previous),
                  any(a.pos == 'NOUN' for a in previous), any(a.pos in {'ADJF', 'PRTF'} for a in previous),
                  any(a.pos == 'ADVB' for a in previous),
                  any(a.pos not in {'ADJS', 'PRTS', 'NOUN', 'ADJF', 'PRTF', 'ADVB'} for a in previous),
                  len(previous_lemmas) > 1, bool(previous_lemmas & candidate_lemmas),
                  bool(previous_lemmas) and bool(candidate_lemmas) and not bool(previous_lemmas & candidate_lemmas),
                  any(a.pos == 'NOUN' for a in target), any(a.pos in {'ADJF', 'PRTF'} for a in target),
                  bool(modifiers), bool(left_cases & target_cases),
                  case_known and not bool(left_cases & target_cases),
                  any(a.pos == 'NPRO' and a.case == 'nomn' for a in left),
                  bool(modifiers) and (len(modifiers) != len(left) or
                      len({(a.case, a.number, a.gender) for a in modifiers}) > 1))
        return tuple(float(value) for value in values)


def extend_applied_features(previous, extractor, left_context, original, applied, candidate):
    values = tuple(previous)
    extra = extractor.extract(left_context, original, applied, candidate)
    if (len(values) != PREVIOUS_FEATURES or len(extra) != len(FEATURE_NAMES)
            or any(not isinstance(value, Real) or not math.isfinite(value) for value in values + tuple(extra))):
        raise ValueError('APPLIED_FEATURE_SCHEMA')
    return values + tuple(extra)
