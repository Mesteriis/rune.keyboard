"""Soft Russian grammatical evidence from preceding text and dictionary analyses.

The injected lexicon must return dictionary analyses only. Ambiguity is retained;
these features never grant correction admission or consult an expected spelling.
"""
import re
import unicodedata

PARTS = ('NOUN', 'ADJF', 'ADJS', 'VERB', 'INFN', 'PRTF', 'PRTS', 'GRND',
         'NPRO', 'ADVB', 'PRED')
CASES = ('nomn', 'gent', 'datv', 'accs', 'ablt', 'loct')
FEATURE_NAMES = (('dictionary_available', 'analysis_ambiguity')
                 + tuple('candidate_pos_' + x for x in PARTS)
                 + tuple('candidate_case_' + x for x in CASES)
                 + ('candidate_singular', 'candidate_plural', 'candidate_first_person',
                    'candidate_second_person', 'candidate_third_person',
                    'infinitive_cue', 'infinitive_supported', 'finite_after_infinitive_cue',
                    'subject_available', 'subject_finite_agreement', 'subject_finite_conflict',
                    'subject_predicate_agreement', 'subject_predicate_conflict',
                    'preposition_available', 'preposition_case_supported',
                    'preposition_case_conflict', 'adjective_agreement',
                    'accusative_verb_cue', 'accusative_object_supported'))
_CONTEXT = re.compile(r'[а-яё]+(?:[ \t]+[а-яё]+){0,7}[ \t]*\Z')
_MODALS = frozenset(('хотеть', 'мочь', 'уметь', 'начать', 'начинать', 'продолжать',
                     'продолжить', 'перестать', 'пытаться', 'стараться', 'собираться'))
_IMPERSONAL = frozenset(('надо', 'нужно', 'необходимо', 'можно', 'нельзя', 'пора',
                         'хочется', 'пришлось', 'удалось', 'должен', 'должна', 'должны'))
_TRANSPARENT = frozenset(('не', 'очень', 'немного', 'уже', 'снова', 'ещё', 'еще',
                          'теперь', 'просто', 'только', 'бы', 'же'))
_SUBJECTS = {'я': ('sing', '1per', None), 'ты': ('sing', '2per', None),
             'он': ('sing', '3per', 'masc'), 'она': ('sing', '3per', 'femn'),
             'оно': ('sing', '3per', 'neut'), 'мы': ('plur', '1per', None),
             'вы': ('plur', '2per', None), 'они': ('plur', '3per', None)}
_PREPOSITIONS = {'в': {'accs', 'loct'}, 'на': {'accs', 'loct'}, 'с': {'gent', 'ablt'},
                 'к': {'datv'}, 'ко': {'datv'}, 'из': {'gent'}, 'у': {'gent'},
                 'для': {'gent'}, 'без': {'gent'}, 'до': {'gent'}, 'от': {'gent'},
                 'после': {'gent'}, 'около': {'gent'}, 'перед': {'ablt'},
                 'над': {'ablt'}, 'между': {'ablt', 'gent'}, 'о': {'loct', 'accs'},
                 'об': {'loct', 'accs'}, 'по': {'datv', 'loct', 'accs'},
                 'за': {'accs', 'ablt'}, 'под': {'accs', 'ablt'}}
# Valency cues are deliberately soft: these verbs also occur in other constructions.
_ACCUSATIVE_VERBS = frozenset(('видеть', 'увидеть', 'смотреть', 'посмотреть', 'показать',
                              'показывать', 'читать', 'прочитать', 'писать', 'написать',
                              'купить', 'покупать', 'искать', 'найти', 'брать', 'взять',
                              'делать', 'сделать', 'любить', 'знать', 'помнить',
                              'получить', 'получать', 'готовить', 'открыть', 'закрыть'))


def preceding_words(context):
    context = unicodedata.normalize('NFC', context).casefold()
    start = max(0, len(context) - 128)
    match = _CONTEXT.search(context[start:])
    if not match:
        return ()
    absolute = start + match.start()
    if absolute and (context[absolute - 1].isalnum() or context[absolute - 1] in '_-'):
        return ()
    return tuple(match.group().split())


def _case(analysis):
    return {'gen1': 'gent', 'gen2': 'gent', 'acc2': 'accs', 'loc1': 'loct', 'loc2': 'loct'}.get(
        analysis.case, analysis.case)


def _agrees(left, right):
    return (left.case is not None and _case(left) == _case(right)
            and left.number is not None and left.number == right.number
            and (left.number == 'plur' or (left.gender is not None and left.gender == right.gender)))


class GrammarContextFeatures:
    def __init__(self, lexicon):
        self.lexicon = lexicon

    def extract(self, context, original, candidate):
        analyses = self.lexicon.analyses(candidate)
        words = preceding_words(context)
        tags = [self.lexicon.analyses(word) for word in words]
        values = [bool(analyses), min(len(analyses), 8) / 8]
        values += [any(a.pos == pos for a in analyses) for pos in PARTS]
        values += [any(_case(a) == case for a in analyses) for case in CASES]
        values += [any(a.number == number for a in analyses) for number in ('sing', 'plur')]
        values += [any(a.person == person for a in analyses) for person in ('1per', '2per', '3per')]
        infinitive = accusative = False
        for word, variants in list(zip(words, tags))[-4:][::-1]:
            if word in _TRANSPARENT or any(a.pos == 'NPRO' and a.case == 'datv' for a in variants):
                continue
            infinitive = (bool(variants) and word in _IMPERSONAL) or any(
                a.lemma in _MODALS and a.pos in {'VERB', 'INFN'} for a in variants)
            accusative = any(a.lemma in _ACCUSATIVE_VERBS and a.pos in {'VERB', 'INFN'} for a in variants)
            break
        subject = next((_SUBJECTS[word] for word in words[-6:][::-1] if word in _SUBJECTS), None)
        finite = [a for a in analyses if a.pos == 'VERB']
        predicates = [a for a in analyses if a.pos in {'ADJS', 'PRTS'}]
        def subject_match(a):
            return (subject is not None and a.number == subject[0]
                    and (a.person is None or a.person == subject[1])
                    and (a.gender is None or subject[2] is None or a.gender == subject[2]))
        preposition = None
        for index in range(len(words) - 1, -1, -1):
            if words[index] in _PREPOSITIONS and any(a.pos == 'PREP' for a in tags[index]):
                if all(any(a.pos == 'ADJF' for a in variants) for variants in tags[index + 1:]):
                    preposition = _PREPOSITIONS[words[index]]
                break
        case_analyses = [a for a in analyses if a.pos in {'NOUN', 'NPRO', 'ADJF'} and a.case]
        adjective_agreement = bool(tags) and any(
            left.pos == 'ADJF' and right.pos in {'NOUN', 'NPRO'} and _agrees(left, right)
            for left in tags[-1] for right in analyses)
        values += [infinitive, infinitive and any(a.pos == 'INFN' for a in analyses),
                   infinitive and bool(finite), bool(subject),
                   bool(subject) and any(subject_match(a) for a in finite),
                   bool(subject) and bool(finite) and not any(subject_match(a) for a in finite),
                   bool(subject) and any(subject_match(a) for a in predicates),
                   bool(subject) and bool(predicates) and not any(subject_match(a) for a in predicates),
                   preposition is not None,
                   preposition is not None and any(_case(a) in preposition for a in case_analyses),
                   preposition is not None and bool(case_analyses) and not any(_case(a) in preposition for a in case_analyses),
                   adjective_agreement, accusative,
                   accusative and any(a.pos == 'NOUN' and _case(a) == 'accs' for a in analyses)]
        return [float(value) for value in values]
