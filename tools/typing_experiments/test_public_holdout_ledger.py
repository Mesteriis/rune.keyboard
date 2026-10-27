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

    def test_recovered_historical_article_is_blocked_without_build(self):
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:article'):
            assert_disjoint([dict(article='5156102')], self.ledger, kinds=('article',))

    def test_recovered_dictionary_family_is_blocked_without_morphology(self):
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:family'):
            assert_disjoint([dict(families=['жара'])], self.ledger, kinds=('family',))

    def test_ranker_text_article_and_training_family_are_persisted(self):
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:article'):
            assert_disjoint([dict(article='3069606')], self.ledger, kinds=('article',))
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:family'):
            assert_disjoint([dict(families=['ранний'])], self.ledger, kinds=('family',), usages=('supervised',))

    def test_historical_overlap_disclosure_matches_recorded_keys(self):
        historical = {key for e in self.ledger['entries'] if e['id'].startswith('public-spelling-v')
                      for key in e['keys']['article']}
        disclosure = self.ledger['historicalArticleOverlap']
        self.assertEqual('NOT_INDEPENDENT_OF_HISTORICAL_SPELLING', disclosure['status'])
        self.assertEqual(len(historical), disclosure['historicalArticles'])
        for e in self.ledger['entries']:
            if e['id'] in disclosure['entries']:
                self.assertEqual(len(historical & set(e['keys']['article'])), disclosure['entries'][e['id']])
        self.assertEqual(97, disclosure['entries']['public-right-context-available-v6-calibration'])
        self.assertEqual(115, disclosure['entries']['public-right-context-available-v6-holdout'])


if __name__ == '__main__':
    unittest.main()
