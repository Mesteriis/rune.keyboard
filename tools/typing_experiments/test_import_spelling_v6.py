import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from import_spelling_v6 import assemble,ENTRY
from test_holdout_ledger import ledger


class Dictionary:
    def analyses(self,word):return [SimpleNamespace(lemma='слово')] if word=='слова' else []
    def receipt(self):return dict(dictionaryOnly=True)


class SpellingV6Test(unittest.TestCase):
    def setUp(self):
        self.rows=[dict(id='a',template='holdout-wikipedia-'+'a'*64,prefix='Пример',typed='слвва',expectedSpelling='слова',cohort='typo'),
                   dict(id='b',template='holdout-wikipedia-'+'b'*64,prefix='Второй',typed='слова',cohort='correct')]
        self.records=[dict(id='a',selectionHash='a'*64,article='1',contextHash='c'*64),
                      dict(id='a',selectionHash='a'*64,article='2',contextHash='d'*64),
                      dict(id='b',selectionHash='b'*64,article='3',contextHash='e'*64)]
        self.base=ledger(False);self.manifest=dict(counts=dict(total=2),source={},sources={'generator.py':'f'*64})

    def run_import(self,**changes):
        args=dict(base=self.base,rows=self.rows,records=self.records,manifest=self.manifest,bindings={'rows':'f'*64},lexicon=Dictionary())|changes
        return assemble(**args)

    def test_every_original_match_and_correct_control_is_retained(self):
        result,receipt=self.run_import()
        self.assertEqual(3,receipt['articles']);self.assertEqual(3,receipt['matchedOccurrences'])
        self.assertEqual(1,receipt['rowsInMultipleOccurrences']);self.assertEqual(2,receipt['contexts'])
        self.assertEqual(2,receipt['counts']['resolvedRows'])
        self.assertEqual(['family'],result['entries'][-2]['missingAxes'])
        self.assertEqual(ENTRY,result['entries'][-2]['id'])

    def test_missing_rows_wrong_selection_and_duplicate_rows_fail(self):
        for changes in (dict(records=self.records[:2]),dict(records=[self.records[0]|dict(selectionHash='f'*64)]+self.records[1:]),dict(rows=self.rows*2)):
            with self.assertRaises(ValueError):self.run_import(**changes)

    def test_old_entries_keys_bindings_and_pending_coverage_remain_intact(self):
        old=copy.deepcopy(self.base);result,_=self.run_import()
        self.assertEqual(old,self.base);self.assertEqual(old['entries'],result['entries'][:-2])
        self.assertEqual(old['coverage'],result['coverage'])
        self.assertEqual([ENTRY],result['historicalArticleOverlap']['scopeEntries'])
        with self.assertRaisesRegex(ValueError,'ALREADY_IMPORTED'):self.run_import(base=result)

    def test_original_v6_builder_is_preserved_without_executing_it(self):
        directory=Path(__file__).with_name('frozen_sources');digest='956436a1fbd708706bddb3bad44c1fdf7bff838ef95a8c06911008148590fe01'
        entry=json.loads((directory/'manifest.json').read_text())['sources'][digest]
        self.assertEqual('tools/typing_experiments/prepare_external_spelling_holdout.py',entry['originalPath'])
        self.assertEqual(digest,hashlib.sha256((directory/entry['file']).read_bytes()).hexdigest())


if __name__=='__main__':unittest.main()
