import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import import_a4_frequency_source as subject


class A4FrequencySourceImportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.controls = subject.reviewed.control.load(subject.CONTROL)
        cls.ledger = subject.reviewed.lexical.load_ledger(subject.LEXICAL)
        cls.control_entry = next(e for e in cls.controls['entries'] if e['id'] == subject.ENTRY)
        cls.lexical_entry = next(e for e in cls.ledger['entries'] if e['id'] == subject.ENTRY)

    def test_all_source_keys_bound_and_review_is_subset(self):
        left=self.lexical_entry['keys']['article'];right=self.control_entry['articleKeys']
        self.assertEqual(92622,len(left));self.assertEqual(92622,len(right))
        self.assertEqual((self.control_entry,self.lexical_entry),subject.entries(left,right))
        reviewed_control,reviewed_lexical=subject.reviewed.entries()
        self.assertTrue(set(reviewed_control['articleKeys'])<=set(right))
        self.assertTrue(set(reviewed_lexical['keys']['article'])<=set(left))
        self.assertEqual(['family','sentence','context'],self.lexical_entry['missingAxes'])

    def test_both_guards_reject_article_using_full_shard_entry(self):
        old_keys={k for entry in self.ledger['entries'] if entry['id'] not in
                  (subject.ENTRY,subject.reviewed.ENTRY) for k in entry['keys'].get('article',[])}
        records=json.loads(subject.reviewed.SAMPLE.read_text())['records']
        row=next({'article':r['article'],'language':'ru','prefix':'','typed':'qzv-unique-source-control'}
                 for r in records if not subject.reviewed.lexical.keys_for([{'article':r['article']}], 'article') & old_keys)
        ledger=dict(self.ledger,entries=[e for e in self.ledger['entries'] if e['id']!=subject.reviewed.ENTRY])
        controls=dict(self.controls,entries=[e for e in self.controls['entries'] if e['id']!=subject.reviewed.ENTRY])
        with self.assertRaisesRegex(ValueError,'LEDGER_OVERLAP:article'):
            subject.reviewed.lexical.assert_disjoint([row],ledger,kinds=('article',),require_complete=False)
        with self.assertRaisesRegex(ValueError,'CONTROL_ARTICLE_OVERLAP'):
            subject.reviewed.control.assert_disjoint([row],controls,'regression')

    def test_mutated_key_and_manifest_fail_closed(self):
        left=list(self.lexical_entry['keys']['article']);right=self.control_entry['articleKeys']
        left[0]='f'*64
        with self.assertRaisesRegex(ValueError,'A4_SOURCE_KEYS'):subject.entries(left,right)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'changed.json';path.write_bytes(subject.MANIFEST.read_bytes()+b' ')
            with patch.object(subject,'MANIFEST',path):
                with self.assertRaisesRegex(ValueError,'A4_SOURCE_FROZEN_MANIFEST'):subject.manifest()


if __name__=='__main__':unittest.main()
