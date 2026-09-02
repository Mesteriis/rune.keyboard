"""Small source-derived RNK1 regressions; no frozen inputs, indexes or legacy FRB1 needed."""
import io
import struct
import unittest

from build_packed_assets import derive_ranks


HEADER = 'key\tsource_rank\tsource_word\tsource_count\n'


class RankDerivationTest(unittest.TestCase):
    def test_canonical_order_determines_ordinals_and_missing_keys_use_sentinel(self):
        words = 'a\nb\né\nё\n😀\n'
        rows = ['ё\t1\tЁ\t99\n', 'a\t50000\tA\t1\n', '😀\t3\t😀\t30\n',
                'absent\t2\tabsent\t40\n']
        expected = b'RNK1' + struct.pack('<IIIIIIIII', 5, 4, 0, 2147483647,
                                      50000, 2147483647, 2147483647, 1, 3)
        for frequency_order in (rows, list(reversed(rows))):
            actual = derive_ranks(io.StringIO(words), io.StringIO(HEADER + ''.join(frequency_order)), 5)
            self.assertEqual(expected, actual)
            self.assertEqual(16 + 4 * 6, len(actual))

    def test_duplicate_or_unsorted_words_are_rejected_instead_of_reordered(self):
        for words in ('b\na\n', 'a\na\n', '\na\n'):
            with self.subTest(words=words), self.assertRaisesRegex(ValueError, '^WORD_ORDER$'):
                derive_ranks(io.StringIO(words), io.StringIO(HEADER), 2)

    def test_declared_count_and_canonical_line_boundaries_are_strict(self):
        for words, count in (('a\n', 2), ('a\nb\n', 1), ('a', 1), ('', 1), ('a\n', 0)):
            with self.subTest(count=count), self.assertRaises(ValueError):
                derive_ranks(io.StringIO(words), io.StringIO(HEADER), count)

    def test_frequency_header_duplicate_keys_and_rank_bounds_are_strict(self):
        for text in ('key\trank\n', HEADER + 'a\t0\tA\t1\n', HEADER + 'a\t50001\tA\t1\n',
                     HEADER + 'a\t1\tA\t1\na\t2\tA\t1\n', HEADER + 'a\t1\n'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                derive_ranks(io.StringIO('a\n'), io.StringIO(text), 1)


if __name__ == '__main__':
    unittest.main()
