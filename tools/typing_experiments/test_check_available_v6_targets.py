import json
from itertools import product
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import check_available_v6_targets as checker


class TargetReceiptTests(unittest.TestCase):
    def test_retained_matches(self):
        result = checker.check()
        self.assertEqual((result['targets'], result['matches'], result['uniqueTargets'],
                          result['ambiguousTargets'], result['unmatchedTargets'],
                          result['crossPartitionMatches']), (9064, 6584, 6570, 6, 2488, 0))
        self.assertFalse(result['independentQualification'])

    def test_receipt_cannot_claim_original_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            shutil.copy(checker.DIRECTORY / 'matches.jsonl', path)
            receipt = json.loads((checker.DIRECTORY / 'receipt.json').read_text())
            receipt['originalLabelsRecovered'] = True
            (path / 'receipt.json').write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, 'V6_TARGET_RECEIPT'):
                checker.check(path)

    def test_rehashed_modified_matches_are_rejected(self):
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            raw = (checker.DIRECTORY / 'matches.jsonl').read_bytes() + b'\n'
            (path / 'matches.jsonl').write_bytes(raw)
            receipt = json.loads((checker.DIRECTORY / 'receipt.json').read_text())
            receipt['matchesSha256'] = hashlib.sha256(raw).hexdigest()
            (path / 'receipt.json').write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, 'V6_TARGET_RECEIPT'):
                checker.check(path)

    def test_ledger_binding_rejects_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            shutil.copy(checker.DIRECTORY / 'matches.jsonl', path)
            receipt = json.loads((checker.DIRECTORY / 'receipt.json').read_text())
            receipt['ledgerSha256'] = '0' * 64
            (path / 'receipt.json').write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, 'V6_TARGET_LEDGER_BINDING'):
                checker.check(path)

    def test_earlier_ledger_change_cannot_be_hidden_by_later_a4_entries(self):
        stored = json.loads(checker.recovery.LEDGER.read_bytes())
        stored['coverage']['pending'].append('unexpected alteration')
        expected = json.loads((checker.DIRECTORY / 'receipt.json').read_bytes())['ledgerSha256']
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'ledger.json'
            path.write_text(json.dumps(stored, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
            with self.assertRaisesRegex(ValueError, 'V6_TARGET_LEDGER_BINDING'):
                checker.verify_ledger_binding(path, expected)

    def test_later_exclusions_require_exact_complete_groups(self):
        expected = json.loads((checker.DIRECTORY / 'receipt.json').read_bytes())['ledgerSha256']
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'ledger.json'
            additions = (checker.NOUN_CASE_ADDITIONS, checker.GRAMMAR_CONTRAST_ADDITIONS,
                         checker.RECOVERED_V6_ADDITIONS, checker.RARE_RANKING_ADDITIONS)
            for group, change in product(additions, ('drop', 'alter')):
                with self.subTest(group=tuple(group), change=change):
                    stored = json.loads(checker.recovery.LEDGER.read_bytes())
                    index = next(i for i, entry in enumerate(stored['entries'])
                                 if entry['id'] in group)
                    if change == 'drop':
                        stored['entries'].pop(index)
                    else:
                        stored['entries'][index]['notes'] += ' altered'
                    path.write_text(json.dumps(stored, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
                    with self.assertRaisesRegex(ValueError, 'V6_TARGET_LEDGER_BINDING'):
                        checker.verify_ledger_binding(path, expected)


if __name__ == '__main__':
    unittest.main()
