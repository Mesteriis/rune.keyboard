"""Versioned experimental evidence from already typed, completed following words.

Separate from the installed 146-feature scorer. No label, expected target,
lookahead text, candidate generation, correction admission or editor authority.
"""
import re
import unicodedata

VERSION = 1
FEATURE_NAMES = (
    'dictionary_available', 'candidate_predicate_available', 'completed_right_words',
    'right_dictionary_available', 'right_copula_available',
    'right_copula_number_supported', 'right_copula_number_conflict',
    'right_copula_gender_supported', 'right_copula_gender_conflict',
    'right_subject_available', 'right_subject_number_supported', 'right_subject_number_conflict',
    'right_subject_gender_supported', 'right_subject_gender_conflict',
    'right_cue_ambiguous', 'candidate_predicate_ambiguous',
)
_WORD = re.compile('[а-яё]{1,32}\\Z')
_COPULAS = frozenset(('буду', 'будешь', 'будет', 'будем', 'будете', 'будут',
                      'был', 'была', 'было', 'были'))
_PREDICATES = frozenset(('ADJS', 'PRTS'))


def completed_following_words(right_context):
    """Exact suffix after candidate; require separator and a visible word boundary.

    Stop at punctuation/newline/identifier boundaries; never scan later clauses.
    The current unfinished token contributes no evidence. Bounds apply before
    normalization and no character outside the first 128 is consulted.
    """
    text = unicodedata.normalize('NFC', right_context[:128]).lower()
    if not text or text[0] not in ' \t':
        return ()
    words = []
    position = 0
    while position < len(text) and len(words) < 8:
        while position < len(text) and text[position] in ' \t':
            position += 1
        start = position
        while position < len(text) and ('а' <= text[position] <= 'я' or text[position] == 'ё'):
            position += 1
        word = text[start:position]
        if not _WORD.fullmatch(word) or position == len(text):
            break
        boundary = text[position]
        if boundary not in ' \t.,!?;:\n\r':
            break
        words.append(word)
        if boundary not in ' \t':
            break
    return tuple(words)


def _agreement(predicates, cues):
    number = any(a.number is not None and a.number == b.number for a in predicates for b in cues)
    number_known = bool(predicates) and bool(cues) and all(a.number is not None for a in predicates + cues)
    gender_pairs = [(a, b) for a in predicates for b in cues
                    if a.number == b.number == 'sing' and a.gender is not None and b.gender is not None]
    gender = any(a.gender == b.gender for a, b in gender_pairs)
    gender_known = bool(predicates) and bool(cues) and all(
        a.number == 'sing' and a.gender is not None for a in predicates + cues)
    return number, number_known and not number, gender, gender_known and not gender


def _ambiguous(variants):
    return len({(a.number, a.gender) for a in variants}) > 1


class RightContextGrammarFeatures:
    def __init__(self, lexicon):
        self.lexicon = lexicon

    def extract(self, right_context, candidate):
        word = unicodedata.normalize('NFC', candidate).lower() if len(candidate) <= 64 else ''
        analyses = tuple(self.lexicon.analyses(word)) if _WORD.fullmatch(word) else ()
        predicates = tuple(a for a in analyses if a.pos in _PREDICATES)
        words = completed_following_words(right_context)
        first = tuple(self.lexicon.analyses(words[0])) if words else ()
        copula = tuple(a for a in first if a.pos == 'VERB') if words and words[0] in _COPULAS else ()
        # Only immediate subjects, optionally immediately after the copula.
        subject_tags = tuple(self.lexicon.analyses(words[1])) if copula and len(words) > 1 else first if not copula else ()
        subject = tuple(a for a in subject_tags if a.pos in {'NOUN', 'NPRO'} and a.case == 'nomn')
        values = (bool(analyses), bool(predicates), len(words) / 8, bool(first), bool(copula))
        values += _agreement(predicates, copula)
        values += (bool(subject),) + _agreement(predicates, subject)
        values += (_ambiguous(copula) or _ambiguous(subject), _ambiguous(predicates))
        return tuple(float(value) for value in values)
