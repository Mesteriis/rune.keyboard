from pathlib import Path
import unittest

from holdout_ledger import assert_disjoint, load_ledger


class PublicLedgerSnapshotTest(unittest.TestCase):
    def setUp(self):
        self.ledger = load_ledger(Path(__file__).with_name('holdout-ledger.json'))

    def test_historical_entries_cannot_disappear_from_the_bootstrap_snapshot(self):
        expected = {f'public-spelling-v{v}' for v in range(7, 13)} | {
            'public-right-context-available-v6-calibration',
            'public-right-context-available-v6-holdout',
            'authored-right-context-supervised-families-v12',
        }
        self.assertTrue(expected <= {e['id'] for e in self.ledger['entries']})

    def test_known_public_article_is_blocked_without_any_build_directory(self):
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:article'):
            assert_disjoint([dict(article='8825104')], self.ledger, kinds=('article',))


if __name__ == '__main__':
    unittest.main()
