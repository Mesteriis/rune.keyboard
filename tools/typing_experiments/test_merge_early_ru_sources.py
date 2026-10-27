import copy
import unittest
from merge_early_ru_sources import enrich


class EarlyMergeTest(unittest.TestCase):
    def setUp(self):
        self.parent=dict(rowCount=1,keys={'context':['a'*64]},missingAxes=['article','family','sentence'],bindings={'rows':'b'*64})
        self.rows=[dict(id='a',split='calibration',template='calibration-wikipedia-'+'c'*64)]
        self.records=[dict(id='a',selectionHash='c'*64,article='1',contextHash='d'*64),
                      dict(id='a',selectionHash='c'*64,article='2',contextHash='e'*64)]
        self.receipt=dict(allRowsRecovered=True,missingRows=[],modelCalls=0,sourceRows=1,recoveredRows=1,matchedOccurrences=2)

    def merge(self,**changes):
        args=dict(parent=self.parent,rows=self.rows,records=self.records,receipt=self.receipt,bindings={'receipt':'f'*64})|changes
        return enrich(**args)

    def test_all_articles_and_occurrences_are_added_without_removing_old_keys(self):
        before=copy.deepcopy(self.parent);result=self.merge()
        self.assertEqual(before,self.parent);self.assertEqual(before['keys']['context'],result['keys']['context'])
        self.assertEqual(2,len(result['keys']['article']));self.assertEqual(['family'],result['missingAxes'])
        self.assertEqual(2,result['recoveryCounts']['occurrences'])

    def test_incomplete_receipts_changed_counts_and_model_calls_fail(self):
        for changes in (dict(allRowsRecovered=False),dict(missingRows=['a']),dict(sourceRows=2),dict(recoveredRows=0),dict(matchedOccurrences=1),dict(modelCalls=1)):
            with self.assertRaises(ValueError):self.merge(receipt=self.receipt|changes)

    def test_wrong_selection_missing_rows_and_duplicate_ids_fail(self):
        for changes in (dict(records=[self.records[0]|dict(selectionHash='0'*64),self.records[1]]),
                        dict(records=[self.records[0]|dict(id='other'),self.records[1]]),dict(rows=self.rows*2)):
            with self.assertRaises(ValueError):self.merge(**changes)

    def test_previous_bindings_cannot_be_rewritten(self):
        with self.assertRaisesRegex(ValueError,'BINDING_CHANGE'):self.merge(bindings={'rows':'0'*64})


if __name__=='__main__':unittest.main()
