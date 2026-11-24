import unittest
import audit_retrieval_unicode_boundaries as subject


class RetrievalUnicodeBoundaryTest(unittest.TestCase):
    def test_counts_distinct_rows_and_matches_without_text(self):
        rows = [{'id': 'r', 'articleId': '1', 'prefix': ' ', 'expectedSpelling': 'слово'}]
        result = subject.analyze(rows, {'1': ' слово_ и слово_ и слово\u0301'})
        self.assertEqual(1, result['rows'])
        self.assertEqual(3, result['matches'])
        self.assertEqual(2, result['rightUnderscoreMatches'])
        self.assertEqual(1, result['rightUnderscoreRows'])
        self.assertEqual(1, result['rightCombiningMarkRows'])
        self.assertNotIn('слово', str(result))

    def test_left_edge_mark_and_underscore_are_counted(self):
        rows = [{'id': 'r1', 'articleId': '1', 'prefix': 'до_', 'expectedSpelling': 'слово'},
                {'id': 'r2', 'articleId': '1', 'prefix': 'до\u0301', 'expectedSpelling': 'слово'}]
        result = subject.analyze(rows, {'1': 'до_слово до\u0301слово'})
        self.assertEqual(1, result['leftUnderscoreRows'])
        self.assertEqual(1, result['leftCombiningMarkRows'])

    def test_missing_source_and_duplicate_rows_are_rejected(self):
        row = {'id': 'r', 'articleId': '1', 'prefix': ' ', 'expectedSpelling': 'слово'}
        for rows, articles in [([row], {}), ([row], {'1': 'нет'}), ([row, row], {'1': ' слово'})]:
            with self.subTest(rows=len(rows)), self.assertRaises(ValueError):
                subject.analyze(rows, articles)


if __name__ == '__main__':
    unittest.main()
