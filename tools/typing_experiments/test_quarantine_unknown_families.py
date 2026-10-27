from types import SimpleNamespace
import unittest
from quarantine_unknown_families import classify
from source_identities import unsupported_surface_key


class Dictionary:
    def analyses(self,word):return [SimpleNamespace(lemma='слово')] if word=='слова' else []


class UnknownFamilyTest(unittest.TestCase):
    def test_predictions_are_recorded_as_unsupported_surfaces_never_as_lemmas(self):
        rows=[dict(id='a',expectedSpelling='дарси'),dict(id='b',expectedSpelling='слова')]
        keys,details,counts=classify(rows,Dictionary(),lambda _:['FakeDictionary','KnownSuffixAnalyzer'])
        self.assertEqual([unsupported_surface_key('дарси')],keys)
        self.assertEqual({'PREDICTION_ONLY':1},counts);self.assertEqual('a',details[0]['id'])
        self.assertNotIn('lemma',details[0])

    def test_protected_controls_are_verified_and_not_misclassified_as_words(self):
        row=dict(id='p',word='слова',cohort='correct',group='protected',noAuto=True,typed='@слова',expectedSpelling='@слова')
        self.assertEqual(([],[],{}),classify([row],Dictionary(),lambda _:self.fail('prediction for a control')))
        with self.assertRaisesRegex(ValueError,'PROTECTED_CONSTRUCTION'):classify([row|dict(noAuto=False)],Dictionary(),lambda _:[])

    def test_dictionary_disagreement_aborts_instead_of_choosing_a_guess(self):
        with self.assertRaisesRegex(ValueError,'DICTIONARY_DISAGREEMENT'):
            classify([dict(id='a',expectedSpelling='дарси')],Dictionary(),lambda _:['DictionaryAnalyzer'])

    def test_missing_targets_nonlexical_tokens_and_no_analysis_remain_explicit(self):
        for row in (dict(id='a'),dict(id='a',expectedSpelling='@дарси')):
            with self.assertRaises(ValueError):classify([row],Dictionary(),lambda _:[])
        _,_,counts=classify([dict(id='a',expectedSpelling='дарси')],Dictionary(),lambda _:[])
        self.assertEqual({'NO_ANALYSIS':1},counts)


if __name__=='__main__':unittest.main()
