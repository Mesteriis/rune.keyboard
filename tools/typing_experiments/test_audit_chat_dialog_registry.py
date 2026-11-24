import io
from pathlib import Path
import tempfile
import unittest
from audit_chat_dialog_registry import run,scan
from holdout_ledger import keys_for
from test_holdout_ledger import ledger


class DialogRegistryAuditTest(unittest.TestCase):
    def test_token_and_last_context_overlaps_are_distinct_and_deduplicated(self):
        base=ledger(False)
        rows=[dict(prefix='мы уже',typed='готовы',expectedSpelling='готовы')]
        base['entries'][0]['keys']['context']=sorted(keys_for(rows,'context'))
        data='q,a\nмы уже готовы идти,мы уже готовы\nмы уже готовы идти,не хочу идти\n'
        result=scan(io.StringIO(data),base)
        self.assertEqual(3,result['uniquePhrases'])
        self.assertEqual(2,result['phrasesWithAnyContextOverlap'])
        self.assertEqual(0,result['phrasesWithFirstContextOverlap'])
        self.assertEqual(2,result['phrasesWithLaterContextOverlap'])
        self.assertEqual(1,result['phrasesWithLastContextOverlap'])
        self.assertEqual(1,result['distinctTokenContextOverlaps'])
        self.assertFalse(result['ledgerComplete'])

    def test_bad_rows_and_empty_source_fail(self):
        for data in ('q,a\n','x,a\na,b\n','q,a\na\n','q,a\na,b,c\n'):
            with self.assertRaises(ValueError):scan(io.StringIO(data),ledger(False))

    def test_unpinned_public_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            paths=[Path(folder)/name for name in ('source','readme','ledger')]
            for path in paths:path.write_text('changed',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'DIALOG_SOURCE_IDENTITY'):run(*paths)


if __name__=='__main__':unittest.main()
