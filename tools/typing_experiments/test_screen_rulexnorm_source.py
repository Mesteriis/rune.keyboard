import unittest

import screen_rulexnorm_source as subject


class RuLexNormScreenTest(unittest.TestCase):
    def test_aggregates_without_disclosing_text(self):
        result = subject.screen('Привет\tПривет\nмир\tмир\n\n'
                                'дом\tдом\nнет\tда\n\n'
                                'ошибка\tошибка\textra\n'.encode())
        self.assertEqual(3, result['counts']['groups'])
        self.assertEqual(1, result['counts']['excludedMalformedGroups'])
        self.assertEqual(1, result['counts']['strictShortOccurrences'])
        self.assertEqual(2, result['counts']['unchangedLowercaseWords'])
        self.assertNotIn('Привет', str(result))
        self.assertNotIn('дом', str(result))

    def test_source_identity_and_invalid_utf8_refuse(self):
        with self.assertRaisesRegex(ValueError, 'RULEXNORM_SOURCE_IDENTITY'):
            subject.verify_source(b'wrong source')
        with self.assertRaises(UnicodeDecodeError):
            subject.screen(b'\xff')


if __name__ == '__main__':
    unittest.main()
