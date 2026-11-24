import unittest
from unittest.mock import patch
import audit_case_homograph_source as subject


class HomographScreenTest(unittest.TestCase):
    def test_real_boundaries_and_case_are_counted(self):
        lines = ['1\trus\tНужны \"клавы\" и читы.\tuser\n',
                 '2\trus\tМоника пишет.\tuser\n',
                 '3\trus\tСуперклавы рядом.\tuser\n']
        with patch.object(subject, 'keys_for', return_value={'allowed'}):
            result = subject.scan(lines, {'allowed'})
        self.assertEqual(3, result['occurrences'])
        self.assertEqual(2, result['articles'])
        self.assertIn({'article': 'tatoeba:2', 'typed': 'моника', 'sourceCase': 'title',
                       'sentenceInitial': True}, result['hits'])

    def test_rejects_unregistered_or_malformed_source(self):
        with patch.object(subject, 'keys_for', return_value={'missing'}):
            with self.assertRaisesRegex(ValueError, 'HOMOGRAPH_SOURCE_NOT_EXCLUDED'):
                subject.scan(['1\trus\tнет клавы\tuser\n'], set())
        with self.assertRaisesRegex(ValueError, 'HOMOGRAPH_SOURCE_ROW'):
            subject.scan(['broken\n'], set())
        with patch.object(subject, 'keys_for', return_value={'allowed'}):
            with self.assertRaisesRegex(ValueError, 'HOMOGRAPH_DUPLICATE_ARTICLE'):
                subject.scan(['1\trus\tнет клавы\tuser\n'] * 2, {'allowed'})


if __name__ == '__main__':
    unittest.main()
