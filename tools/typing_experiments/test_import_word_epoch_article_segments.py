import unittest

from import_word_epoch_article_segments import collect
from import_word_epoch_text_segments import segment_keys


class ArticleSegmentsTest(unittest.TestCase):
    def test_captures_every_article_in_each_partition(self):
        sets = {'one': {'1', '2'}, 'two': {'2'}}
        batches = [(['1', '2', 'unrelated'], ['Первый.', 'Второй.', 'Чужой.'])]
        result = collect(sets, batches)
        self.assertEqual(segment_keys('Первый.') | segment_keys('Второй.'), result['one'])
        self.assertEqual(segment_keys('Второй.'), result['two'])
        with self.assertRaisesRegex(ValueError, 'ARTICLE_SEGMENT_MISSING'):
            collect(sets, [(['1'], ['Первый.'])])
        with self.assertRaisesRegex(ValueError, 'ARTICLE_SEGMENT_DUPLICATE'):
            collect(sets, [(['1', '1', '2'], ['Первый.', 'Другой.', 'Второй.'])])
