"""Experimental continuation evidence, separate from frozen 178-field models.

Only already completed words contribute morphology. Commas remain visible;
strong boundaries, identifiers and bounded windows stop traversal. These are
soft structural observations, not a syntactic parse or correction authority.
"""
from dataclasses import dataclass
import math
import unicodedata

from right_context_role_features import FEATURES as PREVIOUS_FEATURES, preceding_clause_words
from right_context_subject_evidence import SubjectEvidenceLexicon

VERSION = 1
FEATURE_NAMES = (
    'continuation_completed_words', 'continuation_clause_closed',
    'continuation_invalid_boundary', 'continuation_window_exhausted',
    'continuation_has_comma', 'continuation_pending_comma',
    'continuation_subject_available', 'continuation_additive_link',
    'continuation_alternative_link', 'continuation_comma_nominals',
    'continuation_pending_nominal_link', 'continuation_reciprocal',
    'continuation_possible_reciprocal', 'continuation_finite_after_subject',
    'continuation_copula_after_subject', 'continuation_finite_number_supported',
    'continuation_finite_number_conflict', 'continuation_finite_number_ambiguous',
    'adjacent_left_finite_available', 'adjacent_left_copula_available',
    'adjacent_left_number_supported', 'adjacent_left_number_conflict',
    'adjacent_left_number_ambiguous', 'candidate_adverb_reading',
)
FEATURES = PREVIOUS_FEATURES + len(FEATURE_NAMES)
_COPULAS = frozenset(('буду', 'будешь', 'будет', 'будем', 'будете', 'будут',
                      'был', 'была', 'было', 'были'))
_SPACE = ' \t'
_STRONG = '.!?;:\n\r'


@dataclass(frozen=True)
class Continuation:
    words: tuple[str, ...]
    comma_before: tuple[bool, ...]
    pending_comma: bool
    ending: str


def scan_continuation(right_context):
    """Read at most 128 code points / eight words, never a future boundary.

    A comma completes a word but may introduce a list, so scanning continues.
    An unfinished word is not emitted. A truncated window is never clause
    closure, even when a punctuation character exists just outside the window.
    """
    text = unicodedata.normalize('NFC', right_context[:128]).lower()
    words, commas = [], []
    pending_comma = False

    def result(ending):
        return Continuation(tuple(words), tuple(commas), pending_comma, ending)

    if not text or text[0] not in _SPACE:
        return result('NO_SEPARATOR')
    position = 0
    while position < len(text):
        while position < len(text) and text[position] in _SPACE + ',':
            pending_comma |= text[position] == ','
            position += 1
        if position == len(text):
            break
        if text[position] in _STRONG:
            return result('STRONG_BOUNDARY')
        if len(words) == 8:
            return result('WORD_LIMIT')
        start = position
        while position < len(text) and ('а' <= text[position] <= 'я' or text[position] == 'ё'):
            position += 1
        if not 1 <= position - start <= 32:
            return result('INVALID_BOUNDARY')
        if position == len(text):
            return result('CHAR_LIMIT' if len(right_context) > 128 else 'UNFINISHED_WORD')
        if text[position] not in _SPACE + ',' + _STRONG:
            return result('INVALID_BOUNDARY')
        words.append(text[start:position])
        commas.append(pending_comma)
        pending_comma = False
    return result('CHAR_LIMIT' if len(right_context) > 128 else 'OPEN')


def continuation_prefixes(right_context):
    """Emit actual evidence changes, including closure after the same words.

    Unlike the frozen v1 word-count timeline, a comma or sentence closure typed
    after a space is a new decision point. Repeated spaces and characters of an
    unfinished next word cannot repeatedly score identical evidence.
    """
    previous = None
    for end in range(1, min(len(right_context), 128) + 1):
        prefix = right_context[:end]
        scan = scan_continuation(prefix)
        ending = scan.ending if scan.ending in {
            'STRONG_BOUNDARY', 'INVALID_BOUNDARY', 'WORD_LIMIT', 'CHAR_LIMIT'} else 'OPEN'
        state = (scan.words, scan.comma_before, scan.pending_comma, ending)
        if scan.words and state != previous:
            yield scan, prefix
        previous = state


def _number_agreement(predicates, finite):
    numbers = {a.number for a in finite if a.number in {'sing', 'plur'}}
    candidates = {a.number for a in predicates if a.number in {'sing', 'plur'}}
    # Missing readings cannot establish a universal contradiction.
    known = bool(finite) and bool(predicates) and all(
        a.number in {'sing', 'plur'} for a in finite + predicates)
    return (bool(numbers & candidates), known and not bool(numbers & candidates), len(numbers) > 1)


class RightContextContinuationFeatures:
    def __init__(self, lexicon):
        self.lexicon = lexicon
        self.subject_lexicon = SubjectEvidenceLexicon(lexicon)

    def extract(self, left_context, right_context, candidate):
        scan = scan_continuation(right_context)
        words = scan.words
        tags = [tuple(self.subject_lexicon.analyses(word)) for word in words]
        nominal = [any(a.pos in {'NOUN', 'NPRO'} and a.case == 'nomn' for a in readings)
                   for readings in tags]
        # Preserve the existing immediate-subject scope; do not discover a
        # subject by searching arbitrary later words or crossing a new clause.
        subject = 1 if words and words[0] in _COPULAS and any(a.pos == 'VERB' for a in tags[0]) else 0
        has_subject = subject < len(words) and nominal[subject] and not scan.comma_before[subject]
        additive = alternative = comma_nominals = pending_link = False
        finite_after = ()
        following_copula = False
        if has_subject:
            position = subject + 1
            finite_scope = True
            while position < len(words):
                word = words[position]
                if word in {'а', 'но'}:
                    break
                # Record only adjacent nominal links; "или" never implies
                # plural agreement, and a comma alone never proves a list.
                if word in {'и', 'или', 'либо'} and nominal[position - 1]:
                    following = position + 1
                    if following == len(words):
                        pending_link = True
                    elif nominal[following] and not scan.comma_before[following]:
                        additive |= word == 'и'
                        alternative |= word in {'или', 'либо'}
                if scan.comma_before[position]:
                    comma_nominals |= nominal[position - 1] and nominal[position]
                    # Subsequent finite verbs may belong to a new clause.
                    finite_scope = False
                finite = tuple(a for a in tags[position] if a.pos == 'VERB') if finite_scope else ()
                if finite:
                    finite_after = finite
                    following_copula = word in _COPULAS
                    break
                position += 1
        reciprocal = False
        if words and words[0] == 'друг':
            # One completed optional preposition, then an oblique reading of
            # the same noun: другу / друга / другом / друге. This remains a
            # possible role, not proof that "друг" cannot mean a friend.
            target = 2 if len(words) > 1 and any(a.pos == 'PREP' for a in tags[1]) else 1
            if target < len(words) and not any(scan.comma_before[:target + 1]):
                reciprocal = any(a.pos == 'NOUN' and a.lemma == 'друг'
                                 and a.case in {'gent', 'datv', 'accs', 'ablt', 'loct'}
                                 for a in tags[target])
        possible_reciprocal = bool(words) and words[0] == 'друг' and not reciprocal
        left_words = preceding_clause_words(left_context)
        left = ()
        if left_words and left_context.rstrip(_SPACE).lower().endswith(left_words[-1]):
            left = tuple(a for a in self.lexicon.analyses(left_words[-1]) if a.pos == 'VERB')
        candidate_word = unicodedata.normalize('NFC', candidate).lower() if len(candidate) <= 64 else ''
        candidate_tags = tuple(self.lexicon.analyses(candidate_word)) if (
            1 <= len(candidate_word) <= 32 and all('а' <= c <= 'я' or c == 'ё' for c in candidate_word)) else ()
        predicates = tuple(a for a in candidate_tags if a.pos in {'ADJS', 'PRTS'})
        values = (len(words) / 8, scan.ending == 'STRONG_BOUNDARY',
                  scan.ending in {'INVALID_BOUNDARY', 'NO_SEPARATOR'},
                  scan.ending in {'WORD_LIMIT', 'CHAR_LIMIT'},
                  any(scan.comma_before) or scan.pending_comma, scan.pending_comma,
                  has_subject, additive, alternative, comma_nominals, pending_link,
                  reciprocal, possible_reciprocal,
                  bool(finite_after) and not following_copula, following_copula,
                  *_number_agreement(predicates, finite_after),
                  bool(left), bool(left) and left_words[-1] in _COPULAS,
                  *_number_agreement(predicates, left),
                  any(a.pos == 'ADVB' for a in candidate_tags))
        return tuple(float(v) for v in values)


def extend_continuation_features(previous, continuation, left_context, right_context, candidate):
    """Append a new schema; no silent reinterpretation of a frozen model."""
    extra = continuation.extract(left_context, right_context, candidate)
    if (len(previous) != PREVIOUS_FEATURES or len(extra) != len(FEATURE_NAMES)
            or any(not math.isfinite(v) for v in tuple(previous) + tuple(extra))):
        raise ValueError('CONTINUATION_FEATURE_SCHEMA')
    return tuple(previous) + tuple(extra)
