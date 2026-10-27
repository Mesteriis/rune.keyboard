"""Bounded observed role sequences for a new, inactive experimental schema.

Append-only relative to 221 fields. These are possible dictionary readings,
not parse decisions or correction certificates. Never traverse a content-word
head while looking for an adjective behind conjunctions/particles/adverbs.
"""
import math
from numbers import Real
import unicodedata

from right_context_applied_features import FEATURES as PREVIOUS_FEATURES, _word
from right_context_grammar_features import completed_following_words, _agreement
from right_context_role_features import preceding_clause_words
from right_context_subject_evidence import SubjectEvidenceLexicon

VERSION = 1
FEATURE_NAMES = (
    'left_sequence_adjective_available', 'left_sequence_full_adjective',
    'left_sequence_short_predicate', 'left_sequence_adjective_ambiguous',
    'left_sequence_conjunction', 'left_sequence_negation',
    'left_sequence_adverb', 'left_sequence_skipped_words',
    'left_sequence_number_supported', 'left_sequence_number_conflict',
    'left_sequence_gender_supported', 'left_sequence_gender_conflict',
    'adjacent_left_linking_lemma_possible',
    'applied_instrumental_noun', 'applied_pure_instrumental_noun',
    'candidate_instrumental_noun', 'right_genitive_noun',
    'right_pure_genitive_noun', 'right_nominative_plural_noun',
    'right_genitive_noun_ambiguous',
    'left_sequence_bridge_ambiguous',
)
FEATURES = PREVIOUS_FEATURES + len(FEATURE_NAMES)
_FULL = frozenset(('ADJF', 'PRTF'))
_SHORT = frozenset(('ADJS', 'PRTS'))
_BRIDGE = frozenset(('CONJ', 'PRCL', 'ADVB'))
# Possible linking use only: these verbs can also have other contextual roles.
_LINKING = frozenset(('быть', 'стать', 'становиться', 'оказаться', 'казаться', 'оставаться'))


class LeftSequenceFeatures:
    def __init__(self, lexicon):
        self.lexicon = lexicon
        self.reliable = SubjectEvidenceLexicon(lexicon)

    def extract(self, left_context, right_context, applied, candidate):
        applied, candidate = map(_word, (applied, candidate))
        previous = tuple(self.lexicon.analyses(applied))
        target = tuple(self.lexicon.analyses(candidate))
        words = preceding_clause_words(left_context)
        bounded_left = unicodedata.normalize('NFC', left_context[-128:]).lower().rstrip(' \t')
        adjacent = tuple(self.reliable.analyses(words[-1])) if words and bounded_left.endswith(words[-1]) else ()
        adjective = (); readings = (); skipped = 0
        conjunction = negation = adverb = bridge_ambiguous = False
        for word in reversed(words):
            tags = tuple(self.reliable.analyses(word))
            found = tuple(a for a in tags if a.pos in _FULL | _SHORT)
            if found:
                adjective, readings = found, tags
                break
            # Dictionary conjunctions such as и/но also have interjection
            # readings. Keep that uncertainty visible without traversing an
            # arbitrary interjection or a content-word homograph.
            allowed = _BRIDGE | {'INTJ'} if any(a.pos in {'CONJ', 'PRCL'} for a in tags) else _BRIDGE
            if not tags or any(a.pos not in allowed for a in tags):
                break
            bridge_ambiguous |= any(a.pos not in _BRIDGE for a in tags)
            skipped += 1
            conjunction |= any(a.pos == 'CONJ' for a in tags)
            negation |= word == 'не' and any(a.pos == 'PRCL' for a in tags)
            adverb |= any(a.pos == 'ADVB' for a in tags)
        # Bridge observations belong to a found adjective, never a remote one.
        if not adjective:
            skipped = 0
            conjunction = negation = adverb = bridge_ambiguous = False
        right_words = completed_following_words(right_context)
        right = tuple(self.reliable.analyses(right_words[0])) if right_words else ()
        genitive = tuple(a for a in right if a.pos == 'NOUN' and a.case == 'gent')
        instrumental = tuple(a for a in previous if a.pos == 'NOUN' and a.case == 'ablt')
        values = (
            bool(adjective), any(a.pos in _FULL for a in adjective),
            any(a.pos in _SHORT for a in adjective),
            bool(adjective) and (len(adjective) != len(readings) or
                len({(a.pos, a.case, a.number, a.gender) for a in adjective}) > 1),
            conjunction, negation, adverb, skipped / 8,
            *_agreement(tuple(a for a in target if a.pos in _FULL | _SHORT), adjective),
            any(a.pos == 'VERB' and a.lemma in _LINKING for a in adjacent),
            bool(instrumental), bool(previous) and len(instrumental) == len(previous),
            any(a.pos == 'NOUN' and a.case == 'ablt' for a in target),
            bool(genitive), bool(right) and len(genitive) == len(right),
            any(a.pos == 'NOUN' and a.case == 'nomn' and a.number == 'plur' for a in right),
            bool(genitive) and (len(genitive) != len(right) or
                len({(a.number, a.gender) for a in genitive}) > 1),
            bridge_ambiguous,
        )
        return tuple(float(value) for value in values)


def extend_left_sequence_features(previous, extractor, left_context, right_context, applied, candidate):
    values = tuple(previous)
    extra = tuple(extractor.extract(left_context, right_context, applied, candidate))
    if (len(values) != PREVIOUS_FEATURES or len(extra) != len(FEATURE_NAMES)
            or any(not isinstance(v, Real) or not math.isfinite(v) for v in values + extra)):
        raise ValueError('LEFT_SEQUENCE_FEATURE_SCHEMA')
    return values + extra
