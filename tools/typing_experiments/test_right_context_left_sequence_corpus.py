import unittest

from right_context_left_sequence_corpus import generate
from right_context_training_groups import query
from test_right_context_applied_corpus import Dictionary


class LeftSequenceCorpusTest(unittest.TestCase):
    def rows(self):
        lexicon = Dictionary()
        rows, skipped = generate(lexicon, {'полезен': tuple(lexicon.words)}, pairs=[('полезен', 'полезны')])
        self.assertFalse(skipped)
        return rows

    def test_every_frame_has_retention_and_repair_in_both_applied_states(self):
        rows = self.rows()
        scenarios = {r['scenario'] for r in rows if r['kind'] == 'unknown_original'}
        self.assertEqual(6, len(scenarios))
        for scenario in scenarios:
            selected = [r for r in rows if r['scenario'] == scenario and r['kind'] == 'unknown_original']
            expected = 'полезная' if scenario.startswith('full_') else 'полезна'
            self.assertEqual({expected}, {r['expectedApplied'] for r in selected})
            self.assertTrue(any(r['applied'] == expected for r in selected))
            self.assertTrue(any(r['applied'] not in {expected, r['original']} for r in selected))

    def test_controls_and_ownership_of_queries(self):
        rows = self.rows()
        self.assertEqual(len(rows), len({r['id'] for r in rows}))
        self.assertTrue(all(r['expectedApplied'] == r['applied'] for r in rows if r['kind'] != 'unknown_original'))
        for row in rows:
            self.assertEqual('train', row['split'])
            self.assertEqual('AUTHORED_RIGHT_CONTEXT_TRAINING_ONLY', row['purpose'])
            self.assertEqual(query(row), query(row | dict(expectedApplied='другое', rightContext=' другой текст.')))


if __name__ == '__main__':
    unittest.main()
