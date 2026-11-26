import unittest
from dataclasses import dataclass
import audit_chat_case_morphology as subject


@dataclass
class Analysis:
    grammemes: frozenset


class FakeLexicon:
    def analyses(self, word):
        return {'proper': (Analysis(frozenset({'Name'})),),
                'mixed': (Analysis(frozenset({'Geox'})), Analysis(frozenset({'NOUN'}))),
                'common': (Analysis(frozenset({'NOUN'})),), 'missing': ()}[word]


class CaseMorphologyScreenTest(unittest.TestCase):
    def setUp(self):
        self.review = {'schema': 1, 'purpose': subject.PURPOSE, 'cases': [
            {'id': word, 'typed': word, 'baseline': word, 'label': 'lowercase_preserve'}
            for word in ('proper', 'mixed', 'common', 'missing')]}

    def test_all_dictionary_categories_are_reported(self):
        report = subject.screen(self.review, FakeLexicon())
        self.assertFalse(report['independentQualification'])
        self.assertEqual({'proper_only', 'proper_and_other', 'other_only', 'unknown'},
                         {row['dictionaryEvidence'] for row in report['counts']})
        self.assertEqual(4, sum(row['occurrences'] for row in report['counts']))

    def test_missing_scope_duplicate_and_unknown_labels_fail(self):
        for review in ({**self.review, 'purpose': 'new'},
                       {**self.review, 'cases': self.review['cases'] * 2},
                       {**self.review, 'cases': [{**self.review['cases'][0], 'label': 'guess'}]}):
            with self.subTest(review=review), self.assertRaises(ValueError):
                subject.screen(review, FakeLexicon())


if __name__ == '__main__':
    unittest.main()
