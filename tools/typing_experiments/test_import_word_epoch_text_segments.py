import hashlib
import unittest

import import_word_epoch_text_segments as subject
from holdout_ledger import keys_for


class HistoricalTextSegmentsTest(unittest.TestCase):
    def test_segment_normalization_cross_source_and_article_scope(self):
        records = [{'articleId': '42', 'text': 'Привет мир.\nДругой текст!'}]
        entry = subject.make_entry('test', records, ['42', '43'], 'parent', {'fixture': 'a' * 64})
        digest = hashlib.sha256('привет мир.'.encode()).hexdigest()
        row = {'sourceRepository': 'tatoeba', 'language': 'ru', 'article': 'tatoeba:1', 'sentenceHash': digest}
        self.assertTrue(keys_for([row], 'sentence') <= set(entry['keys']['sentence']))
        self.assertEqual(2, len(entry['keys']['sentence']))
        with self.assertRaisesRegex(ValueError, 'TEXT_ARTICLE_SCOPE'):
            subject.make_entry('test', records, ['43'], 'parent', {'fixture': 'a' * 64})
        with self.assertRaisesRegex(ValueError, 'TEXT_ARTICLE_SCOPE'):
            subject.make_entry('test', records * 2, ['42'], 'parent', {'fixture': 'a' * 64})
        with self.assertRaisesRegex(ValueError, 'TEXT_SEGMENT_EMPTY'):
            subject.segment_keys('  ')
