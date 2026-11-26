import unittest
from types import SimpleNamespace

import audit_q7_variant_families as subject
from holdout_ledger import keys_for
from source_identities import unsupported_surface_key


class Lexicon:
    def analyses(self, word):
        return (SimpleNamespace(lemma='мама'),) if word == 'мама' else ()


class VariantFamilyAuditTest(unittest.TestCase):
    def test_verified_source_relation_and_missing_family(self):
        origin = {'language': 'ru', 'target': {'word': 'мама'}}
        rows = [{'language': 'ru', 'typed': w} for w in subject.generator.variants('мама')]
        keys = keys_for([{'families': ['мама']}], 'family')
        result = subject.audit(rows, [origin], Lexicon(), keys, set())
        self.assertEqual(2, result['knownSourceRows'])
        self.assertEqual(0, result['missingSourceFamilyKeys'])
        self.assertEqual(1, subject.audit(rows, [origin], Lexicon(), set(), set())['missingSourceFamilyKeys'])
        bad = [dict(r) for r in rows]; bad[1]['typed'] = 'нет'
        with self.assertRaisesRegex(ValueError, 'Q7_VARIANT_RELATION'):
            subject.audit(bad, [origin], Lexicon(), keys, set())

    def test_unknown_source_requires_exact_surface_quarantine(self):
        origin = {'language': 'ru', 'target': {'word': 'слово'}}
        rows = [{'language': 'ru', 'typed': w} for w in subject.generator.variants('слово')]
        self.assertEqual(1, subject.audit(rows, [origin], Lexicon(), set(), set())['missingSourceSurfaces'])
        known = {unsupported_surface_key('слово')}
        self.assertEqual(0, subject.audit(rows, [origin], Lexicon(), set(), known)['missingSourceSurfaces'])
