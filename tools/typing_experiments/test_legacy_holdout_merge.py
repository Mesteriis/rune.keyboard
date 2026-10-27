import copy
import unittest

from holdout_ledger import keys_for
from merge_legacy_holdout_recovery import enrich_entry
from recover_legacy_holdout import ORIGINAL


class LegacyMergeTest(unittest.TestCase):
    def setUp(self):
        self.entry = dict(id='public-spelling-v7', rowCount=1, usage='historical-exclusion',
            publicSource={'sha256': 'a' * 64}, generatorBindings={ORIGINAL: 'b' * 64},
            keys={'context': ['c' * 64]}, missingAxes=['article', 'family', 'sentence'],
            bindings={'rows.jsonl': 'd' * 64})
        self.records = [dict(id='r', selectionHash='e' * 64, article='1', contextHash='f' * 64),
                        dict(id='r', selectionHash='e' * 64, article='2', contextHash='f' * 64)]
        self.receipt = dict(allRowsRecovered=True, modelCalls=0, missingRows=[], source=self.entry['publicSource'],
            sourceGeneratorSha256='b' * 64, corpusRows=1, recoveredRows=1, matchedOccurrences=2)

    def merge(self, **changes):
        args = dict(entry=self.entry, receipt=self.receipt, records=self.records,
                    selections={'r': 'e' * 64}, bindings={'recovery.json': 'a' * 64}) | changes
        return enrich_entry(**args)

    def test_all_articles_are_added_without_changing_old_keys_or_the_input(self):
        before = copy.deepcopy(self.entry); updated = self.merge()
        self.assertEqual(before, self.entry)
        self.assertEqual(before['keys']['context'], updated['keys']['context'])
        self.assertEqual(keys_for(self.records, 'article'), set(updated['keys']['article']))
        self.assertEqual(['family'], updated['missingAxes'])
        self.assertEqual(2, updated['recoveryCounts']['articles'])

    def test_incomplete_coverage_wrong_source_and_model_calls_fail(self):
        for change in (dict(allRowsRecovered=False), dict(missingRows=['r']), dict(modelCalls=1),
                       dict(source={}), dict(sourceGeneratorSha256='0' * 64), dict(recoveredRows=0)):
            with self.assertRaises(ValueError):
                self.merge(receipt=self.receipt | change)

    def test_selection_identity_and_missing_rows_cannot_be_faked(self):
        with self.assertRaisesRegex(ValueError, 'SELECTION'):
            self.merge(selections={'r': '0' * 64})
        with self.assertRaisesRegex(ValueError, 'COVERAGE'):
            self.merge(selections={'different': 'e' * 64})

    def test_preexisting_bindings_cannot_be_rewritten(self):
        with self.assertRaisesRegex(ValueError, 'BINDING_CHANGE'):
            self.merge(bindings={'rows.jsonl': '0' * 64})


if __name__ == '__main__':
    unittest.main()
