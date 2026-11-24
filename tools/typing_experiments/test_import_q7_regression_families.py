import unittest
from types import SimpleNamespace

import import_q7_regression_families as subject
from holdout_ledger import keys_for
from test_holdout_ledger import ledger


class FakeLexicon:
    def analyses(self, word):
        return (SimpleNamespace(lemma='стать'), SimpleNamespace(lemma='сталь')) if word == 'стали' else ()


class RegressionFamilyTest(unittest.TestCase):
    def test_unions_all_dictionary_analyses_and_quarantines_unknown_surface(self):
        words = subject.lexical_surfaces(['Стали', 'стали', 'неизвестно', 'email@example.org', 'abc'])
        families, unknown, counts = subject.analyze(words, FakeLexicon())
        self.assertEqual({'dictionaryResolved': 1, 'dictionaryUnresolved': 1, 'surfaces': 2}, counts)
        self.assertEqual(keys_for([{'families': ['сталь', 'стать']}], 'family'), set(families))
        self.assertEqual(1, len(unknown))
        with self.assertRaisesRegex(ValueError, 'Q7_SURFACE_TYPE'):
            subject.lexical_surfaces([None])

    def test_parent_drift_and_duplicate_import_fail(self):
        base = ledger(False); parent = base['entries'][0]
        inputs = {'fixture': (['стали'], parent)}
        result, counts = subject.build(base, inputs, FakeLexicon(), {'fixture': 'a' * 64}, 'b' * 64)
        self.assertEqual(1, counts['fixture']['dictionaryResolved'])
        with self.assertRaisesRegex(ValueError, 'Q7_FAMILY_PARENT_DRIFT'):
            subject.build(base, {'fixture': (['стали'], parent | {'notes': 'changed'})}, FakeLexicon(), {'fixture': 'a' * 64}, 'b' * 64)
        with self.assertRaisesRegex(ValueError, 'Q7_FAMILIES_ALREADY_IMPORTED'):
            subject.build(result, inputs, FakeLexicon(), {'fixture': 'a' * 64}, 'b' * 64)
