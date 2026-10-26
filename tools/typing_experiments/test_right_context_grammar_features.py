from types import SimpleNamespace
import unittest
from right_context_grammar_features import FEATURE_NAMES, RightContextGrammarFeatures, completed_following_words


def tag(pos, number=None, gender=None, case=None):
    return SimpleNamespace(pos=pos, number=number, gender=gender, case=case)


class Dictionary:
    def __init__(self):
        self.words = {'готов': [tag('ADJS', 'sing', 'masc')], 'готовы': [tag('ADJS', 'plur')],
                      'была': [tag('VERB', 'sing', 'femn')], 'будут': [tag('VERB', 'plur')],
                      'будет': [tag('VERB', 'sing')], 'был': [tag('VERB', 'sing', 'masc')],
                      'они': [tag('NPRO', 'plur', case='nomn')],
                      'она': [tag('NPRO', 'sing', 'femn', 'nomn')],
                      'им': [tag('NPRO', 'plur', case='datv')],
                      'стали': [tag('VERB', 'plur')]}
        self.lookups = []

    def analyses(self, word):
        self.lookups.append(word)
        return self.words.get(word, ())


class FollowingContextTest(unittest.TestCase):
    def setUp(self):
        self.dictionary = Dictionary()
        self.model = RightContextGrammarFeatures(self.dictionary)

    def features(self, suffix, word='готов'):
        vector = self.model.extract(suffix, word)
        self.assertEqual(len(FEATURE_NAMES), len(vector))
        self.assertTrue(all(0 <= value <= 1 for value in vector))
        return dict(zip(FEATURE_NAMES, vector))

    def test_future_copula_disambiguates_number_without_inventing_gender(self):
        a, b = self.features(' будут '), self.features(' будут ', 'готовы')
        self.assertEqual(a['right_copula_number_conflict'], 1)
        self.assertEqual(b['right_copula_number_supported'], 1)
        self.assertEqual(a['right_copula_gender_conflict'], 0)
        self.assertEqual(a['right_copula_gender_supported'], 0)
        self.assertEqual(self.features(' будет ')['right_copula_number_supported'], 1)

    def test_past_copula_and_subject_supply_gender_separately(self):
        self.assertEqual(self.features(' была ')['right_copula_gender_conflict'], 1)
        self.assertEqual(self.features(' был ')['right_copula_gender_supported'], 1)
        result = self.features(' будет она ')
        self.assertEqual(result['right_copula_number_supported'], 1)
        self.assertEqual(result['right_subject_gender_conflict'], 1)

    def test_immediate_subject_only_and_no_dative_subject(self):
        self.assertEqual(self.features(' они ')['right_subject_number_conflict'], 1)
        self.assertEqual(self.features(' им ')['right_subject_available'], 0)
        self.assertEqual(self.features(' где они ')['right_subject_available'], 0)
        self.assertEqual(self.features(' были где они ')['right_subject_available'], 0)

    def test_unfinished_words_never_supply_evidence_even_if_the_prefix_is_a_word(self):
        for suffix in (' будут', ' буд', ' он', ' она', 'будут ', ''):
            self.assertEqual(completed_following_words(suffix), ())
        self.assertEqual(completed_following_words(' будут он'), ('будут',))
        self.assertNotIn('он', self.dictionary.lookups)

    def test_identifiers_hyphens_and_foreign_text_cannot_launder_a_cue(self):
        for suffix in (' будут_имя ', ' будут-то ', ' будут1 ', ' будутabc ', ' \u200bбудут ', ' abc будут '):
            self.assertEqual(completed_following_words(suffix), ())
        for suffix in (' , будут ', ' \nбудут ', ' . будут '):
            self.assertEqual(completed_following_words(suffix), ())

    def test_clause_barriers_complete_the_current_word_but_never_cross(self):
        for suffix in (' будут, она ', ' будут. она ', ' будут\nона ', ' будут! она '):
            self.assertEqual(completed_following_words(suffix), ('будут',))
            self.assertEqual(self.features(suffix)['right_subject_available'], 0)

    def test_bounds_and_normalization(self):
        self.assertEqual(completed_following_words(' БУДУТ\tОНИ '), ('будут', 'они'))
        self.assertEqual(completed_following_words(' е\u0308лки '), ('ёлки',))
        self.assertEqual(len(completed_following_words(' слово' * 100 + ' ')), 8)
        self.assertEqual(completed_following_words(' ' * 123 + 'будут '), ())
        self.assertEqual(completed_following_words(' ' + 'а' * 33 + ' будут '), ())

    def test_ambiguity_retains_supported_reading_instead_of_asserting_conflict(self):
        self.dictionary.words['готов'].append(tag('ADJS', 'plur'))
        self.dictionary.words['они'].append(tag('NPRO', 'sing', 'femn', 'nomn'))
        result = self.features(' они ')
        self.assertEqual(result['right_subject_number_supported'], 1)
        self.assertEqual(result['right_subject_number_conflict'], 0)
        self.assertEqual(result['candidate_predicate_ambiguous'], 1)
        self.assertEqual(result['right_cue_ambiguous'], 1)

    def test_candidate_normalization_never_hides_a_trailing_identifier_suffix(self):
        normalized = 'ё' * 32
        decomposed = 'ё' * 31 + 'е\u0308'
        self.dictionary.words[normalized] = [tag('ADJS', 'sing', 'masc')]
        self.assertEqual(self.features(' ', decomposed)['dictionary_available'], 1)
        self.assertEqual(self.features(' ', decomposed + 'x')['dictionary_available'], 0)
        self.assertEqual(self.features(' ', 'а' * 1000)['dictionary_available'], 0)

    def test_no_dictionary_guesses_and_no_ordinary_verb_as_copula(self):
        self.assertEqual(self.features(' стали ')['right_copula_available'], 0)
        self.dictionary.words.pop('будут')
        self.assertEqual(self.features(' будут ')['right_copula_available'], 0)
        self.assertEqual(self.features(' они ', 'готово_имя')['dictionary_available'], 0)
        self.assertEqual(self.features(' они ', 'неизвестно')['candidate_predicate_available'], 0)


if __name__ == '__main__':
    unittest.main()
