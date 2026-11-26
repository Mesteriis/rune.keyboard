import unittest
from types import SimpleNamespace

from audit_all_text_source_boundaries import derive


class FakeLexicon:
    def analyses(self, word):
        return [] if word in {'альфа', 'квази'} else [SimpleNamespace(lemma=word)]


class AllTextSourceBoundariesTest(unittest.TestCase):
    def test_shared_unknown_components_are_traced_to_full_source_token(self):
        parts = {'train': [{'articleId': '1', 'text': 'альфа код общий'}],
                 'dev': [{'articleId': '2', 'text': 'альфа код другой'}], 'test': []}
        sources = {'1': 'Альфа-код общий', '2': 'Альфа-код другой'}
        rows, counts = derive(parts, sources, FakeLexicon())
        self.assertEqual(2, len(rows))
        self.assertEqual({'Альфа-код'}, {row['typed'] for row in rows})
        self.assertEqual(1, counts['unknownSurfaces'])
        self.assertEqual({'1', '2'}, {row['article'] for row in rows})
        self.assertNotEqual(rows[0]['id'], rows[1]['id'])

    def test_truncated_final_word_does_not_become_a_source_token(self):
        parts = {'train': [{'articleId': '1', 'text': 'квази'}],
                 'dev': [{'articleId': '2', 'text': 'квази'}], 'test': []}
        rows, counts = derive(parts, {'1': 'квазислово', '2': 'квазислово'}, FakeLexicon())
        self.assertEqual([], rows)
        self.assertEqual(1, counts['truncatedSeen'])
        self.assertEqual(0, counts['completeSeen'])

    def test_unknown_forms_from_one_partition_and_two_heads_in_one_token(self):
        parts = {'train': [{'articleId': '1', 'text': 'альфа квази'}], 'dev': [], 'test': []}
        rows, counts = derive(parts, {'1': 'альфа-квази'}, FakeLexicon())
        self.assertEqual(2, len(rows))
        self.assertEqual({'альфа', 'квази'}, {row['head'] for row in rows})
        self.assertEqual({'альфа-квази'}, {row['typed'] for row in rows})
        self.assertEqual(2, len({row['id'] for row in rows}))
        self.assertEqual(2, counts['unknownSurfaces'])

    def test_changed_source_and_partition_are_rejected(self):
        parts = {'train': [{'articleId': '1', 'text': 'альфа код'}],
                 'dev': [{'articleId': '2', 'text': 'альфа код'}], 'test': []}
        with self.assertRaisesRegex(ValueError, 'ALL_TEXT_MISMATCH'):
            derive(parts, {'1': 'альфа-код', '2': 'другой-код'}, FakeLexicon())
        with self.assertRaisesRegex(ValueError, 'ALL_TEXT_PARTITIONS'):
            derive({'train': []}, {}, FakeLexicon())


if __name__ == '__main__':
    unittest.main()
