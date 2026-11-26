import unittest

import audit_unimorph_text_boundaries as subject
from source_identities import unsupported_surface_key


class SourceBoundaryTest(unittest.TestCase):
    def test_only_source_whole_words_are_projected(self):
        text = 'кот северо-запад домик д’артаньян слово'
        rows = [{'articleId': '1', 'text': 'кот северо запад домик д артаньян сло'}]
        words = ('кот', 'северо', 'запад', 'домик', 'д', 'артаньян', 'сло')
        keys = {unsupported_surface_key(word) for word in words}
        result = subject.source_matches('parent', rows, {'1': text}, keys, keys)
        self.assertEqual({unsupported_surface_key('кот'), unsupported_surface_key('домик')},
                         {row['surfaceKey'] for row in result})

    def test_missing_or_mismatched_source_is_refused(self):
        rows = [{'articleId': '1', 'text': 'кот'}]
        with self.assertRaisesRegex(ValueError, 'UNIMORPH_TEXT_SOURCE'):
            subject.source_matches('parent', rows, {}, set(), set())
        with self.assertRaisesRegex(ValueError, 'UNIMORPH_TEXT_MISMATCH'):
            subject.source_matches('parent', rows, {'1': 'пёс'}, set(), set())


if __name__ == '__main__':
    unittest.main()
