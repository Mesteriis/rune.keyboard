import bz2
import hashlib
import unittest
from unittest.mock import patch

import screen_english_i_source as screen


class EnglishIScreenTest(unittest.TestCase):
    def test_distinguishes_contractions_period_word_boundaries_and_punctuation(self):
        data = bz2.compress(('1\teng\tI think, i.e. I\'m not ii.\ta\n'
                             '2\teng\tI! i I’  I\tb\n').encode())
        with patch.object(screen, 'SHA256', hashlib.sha256(data).hexdigest()):
            result = screen.screen(data)
        self.assertEqual({'source_rows': 2, 'upper_space': 1, 'lower_period': 1,
                          'upper_apostrophe': 2, 'upper_other_admitted_punctuation': 1,
                          'lower_space': 1, 'upper_end': 1}, result)

    def test_rejects_drift_duplicate_id_and_wrong_language(self):
        with self.assertRaisesRegex(ValueError, 'EN_I_SOURCE_DIGEST'):
            screen.screen(b'bad')
        for raw in ('1\trus\tI\ta\n', '1\teng\tI\ta\n01\teng\ti\tb\n'):
            data = bz2.compress(raw.encode())
            with patch.object(screen, 'SHA256', hashlib.sha256(data).hexdigest()):
                with self.assertRaisesRegex(ValueError, 'EN_I_SOURCE_ROW'):
                    screen.screen(data)

    def test_apostrophe_before_i_is_reported_even_at_an_admitted_boundary(self):
        data = bz2.compress("1\teng\tBaha'i, Baha’i faith and i.\ta\n".encode())
        with patch.object(screen, 'SHA256', hashlib.sha256(data).hexdigest()):
            result = screen.screen(data)
        self.assertEqual(2, result['lower_preceded_by_apostrophe'])
        self.assertEqual(2, result['lower_preceded_by_apostrophe_admitted_boundary'])
        self.assertEqual(1, result['lower_period'])

    def test_pinned_source_counts_are_reproducible(self):
        self.assertEqual({'source_rows': 41513, 'upper_space': 5096, 'upper_apostrophe': 1560,
                          'upper_other_admitted_punctuation': 13, 'upper_period': 9,
                          'upper_other': 1, 'lower_space': 1, 'lower_period': 2,
                          'lower_other_admitted_punctuation': 1,
                          'lower_preceded_by_apostrophe': 3,
                          'lower_preceded_by_apostrophe_admitted_boundary': 2,
                          'upper_preceded_by_apostrophe': 5,
                          'upper_preceded_by_apostrophe_admitted_boundary': 5}, screen.screen(screen.SOURCE.read_bytes()))


if __name__ == '__main__':
    unittest.main()
