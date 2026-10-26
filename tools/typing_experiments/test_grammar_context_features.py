from types import SimpleNamespace
import unittest
from grammar_context_features import FEATURE_NAMES, GrammarContextFeatures, preceding_words


def tag(lemma, pos, **attributes):
    return SimpleNamespace(**dict(dict(lemma=lemma, pos=pos, case=None, number=None,
                                      gender=None, person=None), **attributes))


class Lexicon:
    def __init__(self, values): self.values = values
    def analyses(self, word): return self.values.get(word.casefold(), ())


class GrammarContextFeaturesTest(unittest.TestCase):
    def setUp(self):
        self.words = {
            'надо': [tag('надо', 'PRED')], 'могу': [tag('мочь', 'VERB')],
            'начал': [tag('начать', 'VERB')], 'показал': [tag('показать', 'VERB')],
            'тебе': [tag('ты', 'NPRO', case='datv')],
            'учиться': [tag('учиться', 'INFN')],
            'учишься': [tag('учиться', 'VERB', number='sing', person='2per')],
            'учимся': [tag('учиться', 'VERB', number='plur', person='1per')],
            'новой': [tag('новый', 'ADJF', case='datv', number='sing', gender='femn')],
            'книге': [tag('книга', 'NOUN', case='datv', number='sing', gender='femn')],
            'книгу': [tag('книга', 'NOUN', case='accs', number='sing', gender='femn')],
            'в': [tag('в', 'PREP')], 'к': [tag('к', 'PREP')],
            'виновны': [tag('виновный', 'ADJS', number='plur')],
            'виновен': [tag('виновный', 'ADJS', number='sing', gender='masc')],
        }
        self.model = GrammarContextFeatures(Lexicon(self.words))

    def features(self, context, word):
        vector = self.model.extract(context, 'опечатка', word)
        self.assertEqual(len(vector), len(FEATURE_NAMES))
        self.assertTrue(all(0 <= x <= 1 for x in vector))
        return dict(zip(FEATURE_NAMES, vector))

    def test_infinitive_cue_crosses_only_short_transparent_context(self):
        for context in ('тебе надо ', 'я не могу тебе ', 'он начал немного '):
            self.assertEqual(self.features(context, 'учиться')['infinitive_supported'], 1)
            self.assertEqual(self.features(context, 'учишься')['finite_after_infinitive_cue'], 1)
        self.assertEqual(self.features('я могу книгу ', 'учиться')['infinitive_cue'], 0)

    def test_subject_person_number_and_short_predicate(self):
        self.assertEqual(self.features('ты уже ', 'учишься')['subject_finite_agreement'], 1)
        self.assertEqual(self.features('мы уже ', 'учишься')['subject_finite_conflict'], 1)
        self.assertEqual(self.features('мы уже ', 'учимся')['subject_finite_agreement'], 1)
        self.assertEqual(self.features('они ', 'виновны')['subject_predicate_agreement'], 1)
        self.assertEqual(self.features('они ', 'виновен')['subject_predicate_conflict'], 1)

    def test_preposition_adjective_and_ambiguous_case(self):
        self.assertEqual(self.features('к новой ', 'книге')['preposition_case_supported'], 1)
        self.assertEqual(self.features('к новой ', 'книге')['adjective_agreement'], 1)
        self.assertEqual(self.features('к ', 'книгу')['preposition_case_conflict'], 1)
        self.words['книгу'].append(tag('книга', 'NOUN', case='datv'))
        value = self.features('к ', 'книгу')
        self.assertEqual(value['preposition_case_supported'], 1)
        self.assertEqual(value['preposition_case_conflict'], 0)
        # Predicative short adjectives do not take the preposition's noun case.
        self.assertEqual(self.features('они в ', 'виновны')['preposition_case_conflict'], 0)

    def test_valency_is_evidence_only_and_handles_intervening_dative(self):
        self.assertEqual(self.features('он показал тебе ', 'книгу')['accusative_object_supported'], 1)
        self.assertEqual(self.features('он показал тебе ', 'книге')['accusative_object_supported'], 0)

    def test_secondary_dictionary_cases_keep_their_grammatical_family(self):
        self.words['лесу'] = [tag('лес', 'NOUN', case='loc2')]
        value = self.features('в ', 'лесу')
        self.assertEqual(value['candidate_case_loct'], 1)
        self.assertEqual(value['preposition_case_supported'], 1)
        self.assertEqual(value['preposition_case_conflict'], 0)
        self.words['из'] = [tag('из', 'PREP')]
        self.words['чаю'] = [tag('чай', 'NOUN', case='gen2')]
        self.assertEqual(self.features('из ', 'чаю')['candidate_case_gent'], 1)
        self.assertEqual(self.features('из ', 'чаю')['preposition_case_supported'], 1)

    def test_boundaries_and_unknown_dictionary_words(self):
        for prefix in ('надо, ', 'надо. ты ', 'надо\nты ', 'xнадо ', '_надо ', 'надо-нибудь '):
            self.assertEqual(self.features(prefix, 'учиться')['infinitive_cue'], 0)
        self.assertEqual(preceding_words('Надо\tуже '), ('надо', 'уже'))
        self.assertLessEqual(len(preceding_words('слово ' * 100)), 8)
        self.assertEqual(self.features('надо ', 'незнакомоеслово')['dictionary_available'], 0)
        self.assertEqual(self.features('надо ', 'незнакомоеслово')['infinitive_supported'], 0)


if __name__ == '__main__': unittest.main()
