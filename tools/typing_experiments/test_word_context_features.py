import math
import unittest
from word_context_features import WordContextFeatures, previous_word


class WordContextFeaturesTest(unittest.TestCase):
    def test_context_boundary_does_not_erase_punctuation_or_identifiers(self):
        self.assertEqual('на', previous_word('поставь стакан НА '))
        self.assertEqual('мы', previous_word('мы'))
        for context in ('мы, ', '@мы ', 'x=мы ', 'abcмы ', '', 'мы! ', 'на\n. '):
            self.assertIsNone(previous_word(context), context)

    def test_counts_are_finite_bounded_and_original_relative(self):
        features = WordContextFeatures([('на', 'стол', 20, 10), ('мы', 'стол', 2, 1), ('на', 'стал', 1, 1)])
        vector = features.extract('поставь на ', 'сттл', 'стол')
        self.assertEqual(6, len(vector))
        self.assertTrue(all(math.isfinite(x) and -1 <= x <= 1 for x in vector))
        self.assertAlmostEqual(20 / 23, vector[2])
        self.assertAlmostEqual(20 / 22, vector[3])
        self.assertGreater(vector[4], 0)
        self.assertEqual(0, features.extract('на ', 'стол', 'стол')[4])
        self.assertLess(features.extract('на ', 'стол', 'стал')[4], 0)

    def test_missing_evidence_and_case_have_deterministic_semantics(self):
        features = WordContextFeatures([('на', 'стол', 20, 10)])
        self.assertEqual(features.extract('на ', 'сттл', 'стол'), features.extract('НА ', 'СТТЛ', 'СТОЛ'))
        self.assertEqual([0.] * 6, features.extract('из ', 'сттл', 'стол'))
        self.assertEqual([0.] * 6, features.extract('на, ', 'сттл', 'стол'))

    def test_invalid_counts_fail_closed(self):
        for rows in [[('на', 'стол', 1, 2)], [('на', 'стол', True, 1)], [('на', 'стол', 1, 0)],
                     [('на', 'стол', 1, 1), ('на', 'стол', 2, 1)]]:
            with self.assertRaises(ValueError): WordContextFeatures(rows)
