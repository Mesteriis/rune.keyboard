import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import import_a4_review_exposure as subject


class A4ReviewExposureTest(unittest.TestCase):
    def test_all_articles_are_registered_and_both_guards_reject_reuse(self):
        control_entry, lexical_entry = subject.entries()
        controls = subject.control.load(subject.CONTROL)
        ledger = subject.lexical.load_ledger(subject.LEXICAL)
        self.assertEqual([control_entry], [x for x in controls['entries'] if x['id'] == subject.ENTRY])
        self.assertEqual([lexical_entry], [x for x in ledger['entries'] if x['id'] == subject.ENTRY])
        rows = json.loads(subject.SAMPLE.read_text())['records']
        self.assertEqual(46, len(lexical_entry['keys']['article']))
        self.assertEqual(46, len(control_entry['articleKeys']))
        self.assertEqual(set(lexical_entry['keys']['article']),
                         subject.lexical.keys_for([{'article': x['article']} for x in rows], 'article'))
        proposals = [{'article': x['article'], 'language': 'ru', 'prefix': '',
                      'typed': 'qzv-unique-review-control'} for x in rows]
        self.assertEqual(set(control_entry['articleKeys']), {subject.control.article_key(x) for x in proposals})
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:article'):
            subject.lexical.assert_disjoint(proposals, ledger, kinds=('article',), require_complete=False)
        with self.assertRaisesRegex(ValueError, 'CONTROL_ARTICLE_OVERLAP'):
            subject.control.assert_disjoint(proposals, controls, 'regression')

    def test_modified_sample_and_review_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'changed.json'
            for key, original in (('SAMPLE', subject.SAMPLE), ('REVIEW', subject.REVIEW)):
                path.write_bytes(original.read_bytes() + b' ')
                with patch.object(subject, key, path):
                    with self.assertRaisesRegex(ValueError, 'A4_REVIEW_FROZEN_IDENTITY'):
                        subject.entries()


if __name__ == '__main__': unittest.main()
