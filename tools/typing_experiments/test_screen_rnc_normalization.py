import json
import unittest

import screen_rnc_normalization as subject


class RncNormalizationScreenTest(unittest.TestCase):
    def test_counts_preserve_case_and_compare_exact_orthographic_variants(self):
        pairs = [
            [['тёплый', 'чай'], ['тёплый', 'чай']],
            [['ТЁПЛЫЙ', 'чай'], ['тёплый', 'чай']],
            [['уселась', 'сарока'], ['уселась', 'сорока']],
            [['пьем', 'чай'], ['пьём', 'чай']],
            [['народ', 'локал'], ['народ', '<foreign>']],
        ]
        result = subject.screen(json.dumps(pairs).encode())
        counts = result['counts']
        self.assertEqual(1, counts['strictLowercaseUnchangedRows'])
        self.assertEqual(2, counts['shortCyrillicUnchangedAfterCasefoldRows'])
        self.assertEqual(1, counts['distinctCasefoldUnchangedPhrases'])
        self.assertEqual(2, counts['oneChangedToken'])
        self.assertEqual(1, counts['oneChangedFinalToken'])
        self.assertEqual(1, counts['exactGeneratorFinalMatches'])
        self.assertEqual(1, counts['yoOnly'])
        self.assertEqual({'vowel_oa': 1}, result['generatedKinds'])
        self.assertNotIn('тёплый', str(result))

    def test_refuses_changed_source_and_nonparallel_pairs(self):
        with self.assertRaisesRegex(ValueError, 'RNC_NORMALIZATION_SOURCE_IDENTITY'):
            subject.verify_source(b'[]')
        with self.assertRaisesRegex(ValueError, 'RNC_NORMALIZATION_PAIR'):
            subject.screen(b'[[["a"],["b","c"]]]')
