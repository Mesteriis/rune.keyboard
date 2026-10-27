import unittest
from types import SimpleNamespace
from holdout_ledger import KEY_SCHEMA, assert_disjoint
from import_ranker_history import partition_entries


class Dictionary:
    def analyses(self, word):
        return [SimpleNamespace(lemma='старый')] if word == 'старого' else []


class RankerHistoryTest(unittest.TestCase):
    def entries(self, part='train', **changes):
        row=dict(id='r',expectedSpelling='старого',articleId='123',partition=part,language='ru') | changes
        return partition_entries(part,dict(articles=['123','124'],rows=1),[row],Dictionary(),{'manifest':'a'*64})

    def ledger(self, entries):
        return dict(schema=1,keySchema=KEY_SCHEMA,publicDataOnly=True,
                    coverage=dict(complete=False,pending=['history']),entries=entries)

    def test_all_text_exposure_articles_are_blocked_even_without_target_rows(self):
        entries,_=self.entries()
        with self.assertRaisesRegex(ValueError,'LEDGER_OVERLAP:article'):
            assert_disjoint([dict(article='124')],self.ledger(entries),kinds=('article',))

    def test_training_families_are_supervised_but_dev_and_test_are_historical(self):
        for part in ('train','dev','test'):
            entries,_=self.entries(part)
            self.assertEqual('supervised' if part=='train' else 'historical-family-exclusion',entries[1]['usage'])
            with self.assertRaisesRegex(ValueError,'LEDGER_OVERLAP:family'):
                assert_disjoint([dict(families=['старый'])],self.ledger(entries),kinds=('family',))

    def test_unknown_targets_keep_missing_family_axis(self):
        entries,counts=self.entries(expectedSpelling='неизвестное')
        self.assertEqual(1,len(entries));self.assertIn('family',entries[0]['missingAxes'])
        self.assertEqual(['r'],counts['unresolvedRows'])

    def test_wrong_article_partition_language_count_and_id_fail(self):
        for changes in (dict(articleId='125'),dict(partition='test'),dict(language='en'),dict(id=None)):
            with self.assertRaises(ValueError):self.entries(**changes)
        with self.assertRaisesRegex(ValueError,'ROW_COUNT'):
            partition_entries('train',dict(articles=['123'],rows=1),[],Dictionary(),{'manifest':'a'*64})


if __name__=='__main__':unittest.main()
