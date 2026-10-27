"""Soft case-role and gender evidence for a new experimental ranker layout.

A possible nominative analysis is not proof of subjecthood. Case alternatives,
other parts of speech and gender uncertainty remain visible to the model.
No feature grants admission, reads labels, or changes the frozen v1 layout.
"""
import re
import unicodedata
import math
from right_context_grammar_features import completed_following_words
from right_context_revision_features import revision_features, FEATURES as PREVIOUS_FEATURES

VERSION = 1
FEATURE_NAMES = (
    'right_nominal_case_alternative', 'right_nominal_case_unambiguous',
    'right_nominal_number_ambiguous', 'right_nominal_other_part',
    'right_nominal_is_noun', 'right_nominal_is_pronoun',
    'right_gender_available', 'right_gender_ambiguous',
    'candidate_masculine', 'candidate_feminine', 'candidate_neuter',
    'left_past_gender_available', 'left_past_gender_supported',
    'left_past_gender_conflict', 'left_past_gender_ambiguous',
)
_COPULAS = frozenset(('буду','будешь','будет','будем','будете','будут',
                      'был','была','было','были'))
_WORD = re.compile('[а-яё]{1,32}\\Z')
FEATURES = PREVIOUS_FEATURES + len(FEATURE_NAMES)


def role_revision_features(base, right, role, left_context, right_context, applied, candidate):
    previous = revision_features(base, right, right_context, applied, candidate)
    extra = role.extract(left_context, right_context, candidate)
    if len(extra) != len(FEATURE_NAMES) or any(not math.isfinite(v) for v in extra):
        raise ValueError('ROLE_REVISION_FEATURE_SCHEMA')
    return previous + tuple(extra)


def preceding_clause_words(context):
    """At most eight complete words, allowing commas within a bounded clause.

    A hard sentence/identifier boundary stops traversal. Do not remove foreign
    or malformed text to manufacture an apparent adjacent Russian word.
    """
    text = unicodedata.normalize('NFC', context[-128:]).lower()
    if not text or text[-1] not in ' \t,':
        return ()
    end = len(text); result = []
    while end and len(result) < 8:
        while end and text[end-1] in ' \t,':end -= 1
        start = end
        while start and ('а' <= text[start-1] <= 'я' or text[start-1] == 'ё'):start -= 1
        word = text[start:end]
        if not _WORD.fullmatch(word):break
        if start and text[start-1] not in ' \t,.:;!?\n\r':break
        # The window might begin in a word; no evidence from that partial token.
        if start == 0 and len(context) > 128 and context[-129].isalnum():break
        result.append(word)
        if start == 0 or text[start-1] not in ' \t,':break
        end = start
    return tuple(reversed(result))


class RightContextRoleFeatures:
    def __init__(self, lexicon):
        self.lexicon = lexicon

    def extract(self, left_context, right_context, candidate):
        words = completed_following_words(right_context)
        first = tuple(self.lexicon.analyses(words[0])) if words else ()
        copula = tuple(a for a in first if a.pos == 'VERB') if words and words[0] in _COPULAS else ()
        subject_tags = tuple(self.lexicon.analyses(words[1])) if copula and len(words)>1 else first if not copula else ()
        nominal = tuple(a for a in subject_tags if a.pos in {'NOUN','NPRO'})
        nominative = tuple(a for a in nominal if a.case == 'nomn')
        case_alternative = any(a.case != 'nomn' for a in nominal)
        right_genders = {a.gender for a in copula+nominative if a.number == 'sing' and a.gender in {'masc','femn','neut'}}
        candidate_tags = tuple(self.lexicon.analyses(candidate))
        predicates = tuple(a for a in candidate_tags if a.pos in {'ADJS','PRTS'})
        candidate_genders = {a.gender for a in predicates if a.number == 'sing' and a.gender in {'masc','femn','neut'}}
        past = []
        for word in reversed(preceding_clause_words(left_context)):
            tags = self.lexicon.analyses(word)
            finite = [a for a in tags if a.pos == 'VERB' and a.tense == 'past']
            if finite:
                # The nearest past finite surface can itself be ambiguous.
                past = finite
                break
        past_genders = {a.gender for a in past if a.number == 'sing' and a.gender in {'masc','femn','neut'}}
        values = (bool(nominative) and case_alternative,
                  bool(nominative) and not case_alternative and len(nominal)==len(subject_tags),
                  len({a.number for a in nominal if a.number is not None})>1,
                  bool(nominative) and len(nominal)!=len(subject_tags),
                  any(a.pos=='NOUN' for a in nominative),any(a.pos=='NPRO' for a in nominative),
                  bool(right_genders),len(right_genders)>1,
                  *[gender in candidate_genders for gender in ('masc','femn','neut')],
                  bool(past_genders),bool(past_genders & candidate_genders),
                  bool(past_genders) and bool(candidate_genders) and not bool(past_genders & candidate_genders),
                  len(past_genders)>1)
        return tuple(float(v) for v in values)
