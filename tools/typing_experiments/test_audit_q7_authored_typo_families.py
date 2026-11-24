import unittest
from types import SimpleNamespace

from audit_q7_authored_typo_families import audit
from holdout_ledger import keys_for


class Lexicon:
    def analyses(self, word):
        return (SimpleNamespace(lemma='стать'), SimpleNamespace(lemma='сталь')) if word == 'стали' else ()


class Q7TypoFamilyAuditTest(unittest.TestCase):
    def test_unknown_typo_maps_only_to_explicit_target_dictionary_analyses(self):
        row = {'id': 'one', 'language': 'ru', 'cohort': 'typo', 'typed': 'стли', 'expectedSpelling': 'стали'}
        families = keys_for([{'families': ['стать', 'сталь']}], 'family')
        result = audit([row], Lexicon(), families)
        self.assertEqual((1, 1, 0), (result['unknownTypoRows'], result['knownTargetRows'], result['missingTargetFamilyKeys']))
        self.assertEqual(2, audit([row], Lexicon(), set())['missingTargetFamilyKeys'])
        with self.assertRaisesRegex(ValueError, 'Q7_TYPO_ROW_ID'): audit([row, row], Lexicon(), families)
        with self.assertRaisesRegex(ValueError, 'Q7_TYPO_TARGET'): audit([row | {'expectedSpelling': None}], Lexicon(), families)
