import unittest

from a3_lowercase_sidecar import lowercase_forms


class LowercaseSidecarTest(unittest.TestCase):
    def test_only_complete_short_lowercase_cyrillic_words(self):
        self.assertEqual(['мир', 'мама', 'сёла'], lowercase_forms('Мир мир мама сёла МАМА длинное пол-мир'))
        self.assertEqual([], lowercase_forms('абвгд аб ё ЁЖ ёж а-бвг'))
        self.assertEqual([], lowercase_forms('abcмир мир2 _мир мир_'))
        self.assertEqual([], lowercase_forms('кот\u0301 \u0301кот'))
        self.assertEqual(['ёлка'], lowercase_forms('е\u0308лка'))
