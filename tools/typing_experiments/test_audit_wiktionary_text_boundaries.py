import unittest

import audit_wiktionary_text_boundaries as subject


class WiktionaryProjectionTest(unittest.TestCase):
    def test_projection_retains_only_same_parent_matches(self):
        parts = {name: [] for name in subject.source_audit.TEXT_PARENTS}
        first, second = subject.source_audit.TEXT_PARENTS[:2]
        parts[first] = [{'surfaceKey': 'same'}, {'surfaceKey': 'other'}]
        parts[second] = [{'surfaceKey': 'same'}]
        matches = {name: [] for name in parts}
        matches[first] = ['same']
        self.assertEqual([{'surfaceKey': 'same'}], subject.selected_records(parts, matches))
        del matches[second]
        with self.assertRaisesRegex(ValueError, 'WIKTIONARY_TEXT_PARTITIONS'):
            subject.selected_records(parts, matches)


if __name__ == '__main__':
    unittest.main()
