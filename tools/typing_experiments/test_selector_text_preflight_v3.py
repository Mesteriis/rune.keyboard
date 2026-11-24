import unittest
import unicodedata

import selector_text_preflight_v2 as old
import selector_text_preflight_v3 as subject
from test_selector_text_preflight_v1 import sample, Lexicon, ledger, controls


class DashPreflightTest(unittest.TestCase):
    def test_unspaced_dash_fragments_are_detected_and_old_report_is_preserved(self):
        for char in ('‒', '—', '־'):
            with self.subTest(char=char):
                texts, rows, sources = sample()
                texts['train'][0]['text'] = 'слово часть'
                sources['901'] = 'слово' + char + 'часть'
                before = old.assess(texts, rows, sources, Lexicon(), ledger(False), controls())
                after = subject.assess(texts, rows, sources, Lexicon(), ledger(False), controls())
                self.assertNotIn('sourceDashFragments', before['textIdentityBlockers'])
                self.assertEqual(2, after['textIdentityBlockers']['sourceDashFragments'])
                self.assertEqual('BLOCKED_TEXT_IDENTITIES', after['status'])
                self.assertFalse(after['publicationPermitted'])
                self.assertFalse(after['independentQualification'])

    def test_space_around_dash_is_not_a_fragment(self):
        texts, rows, sources = sample()
        texts['train'][0]['text'] = 'слово часть'
        sources['901'] = 'слово — часть'
        result = subject.assess(texts, rows, sources, Lexicon(), ledger(False), controls())
        self.assertEqual(0, result['textIdentityBlockers']['sourceDashFragments'])

    def test_all_unicode_dash_characters_detected(self):
        for n in range(0x110000):
            char = chr(n)
            if unicodedata.category(char) != 'Pd':
                continue
            texts, rows, sources = sample()
            texts['train'][0]['text'] = 'слово часть'
            sources['901'] = 'слово' + char + 'часть'
            result = subject.assess(texts, rows, sources, Lexicon(), ledger(False), controls())
            with self.subTest(codepoint=n):
                self.assertEqual(2, result['textIdentityBlockers']['sourceDashFragments'])
