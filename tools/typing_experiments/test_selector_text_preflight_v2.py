import unittest

import selector_text_preflight_v1 as previous
import selector_text_preflight_v2 as subject
from test_selector_text_preflight_v1 import sample, Lexicon, ledger, controls


class FormatCharacterPreflightTest(unittest.TestCase):
    def test_invisible_source_joiners_are_blocked_without_changing_v1(self):
        for char in ('\u200b', '\u200d', '\u2060', '\u202e'):
            with self.subTest(codepoint=ord(char)):
                texts, rows, sources = sample()
                texts['train'][0]['text'] = 'слово часть'
                sources['901'] = 'слово' + char + 'часть'
                old = previous.assess(texts, rows, sources, Lexicon(), ledger(False), controls())
                new = subject.assess(texts, rows, sources, Lexicon(), ledger(False), controls())
                self.assertEqual(0, old['textIdentityBlockers']['sourceTokenFragments'])
                self.assertGreater(new['textIdentityBlockers']['sourceFormatFragments'], 0)
                self.assertEqual('BLOCKED_TEXT_IDENTITIES', new['status'])
                self.assertFalse(new['publicationPermitted'])
                self.assertFalse(new['independentQualification'])

    def test_ordinary_space_is_not_a_format_fragment(self):
        texts, rows, sources = sample()
        texts['train'][0]['text'] = 'слово часть'
        sources['901'] = 'слово часть'
        result = subject.assess(texts, rows, sources, Lexicon(), ledger(False), controls())
        self.assertEqual(0, result['textIdentityBlockers']['sourceFormatFragments'])

    def test_combining_and_mixed_source_fragments_remain_blocked(self):
        for source, fragment in (('сло\u0301во', 'сло во'), ('северо-запад', 'северо запад'),
                                 ('слово123', 'слово'), ('словоLatin', 'слово')):
            with self.subTest(source=source):
                texts, rows, sources = sample()
                texts['train'][0]['text'] = fragment
                sources['901'] = source
                result = subject.assess(texts, rows, sources, Lexicon(), ledger(False), controls())
                self.assertGreater(result['textIdentityBlockers']['sourceTokenFragments'], 0)
                self.assertFalse(result['publicationPermitted'])


if __name__ == '__main__':
    unittest.main()
