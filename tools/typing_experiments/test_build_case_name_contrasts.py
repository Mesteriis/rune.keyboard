import unittest
from unittest.mock import patch
import build_case_name_contrasts as subject


class NameContrastTest(unittest.TestCase):
    def test_extracts_whole_noninitial_title_only_from_excluded_articles(self):
        articles = [{'id': '1', 'text': 'Она встретила Моника. Моника тут. Санта-Моника.'},
                    {'id': '2', 'text': 'Она увидела Моника.'}]
        with patch.object(subject, 'keys_for', side_effect=lambda rows, kind: {rows[0]['article']}):
            rows = subject.extract(articles, {'моника'}, {'1'})
        self.assertEqual(1, len(rows))
        self.assertEqual(('она встретила', 'моника', 'Моника'),
                         (rows[0]['prefix'], rows[0]['typed'], rows[0]['expectedSpelling']))
        self.assertEqual('1', rows[0]['article'])

    def test_rejects_bad_and_duplicate_articles(self):
        with self.assertRaisesRegex(ValueError, 'NAME_CONTRAST_SOURCE_ROW'):
            subject.extract([{'id': '1'}], {'моника'}, set())
        with patch.object(subject, 'keys_for', return_value={'1'}):
            with self.assertRaisesRegex(ValueError, 'NAME_CONTRAST_DUPLICATE_ARTICLE'):
                subject.extract([{'id': '1', 'text': 'Она видит Моника.'}] * 2, {'моника'}, {'1'})


if __name__ == '__main__':
    unittest.main()
