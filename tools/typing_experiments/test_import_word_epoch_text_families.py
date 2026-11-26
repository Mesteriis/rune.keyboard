from types import SimpleNamespace
import copy
import unittest

import import_word_epoch_text_families as subject
import import_word_epoch_text_segments as segments
from holdout_ledger import keys_for
from source_identities import unsupported_surface_key


class TextFamilyImportTest(unittest.TestCase):
    def test_multiple_analyses_unknown_and_parent_scope(self):
        class Lexicon:
            def analyses(self, word):
                if word == 'стали':
                    return [SimpleNamespace(lemma='стать'), SimpleNamespace(lemma='сталь')]
                return []
        records = [{'articleId': '42', 'text': 'СТАЛИ непонятнос'}]
        parent = segments.make_entry('test', records, ['42'], 'source', {'fixture': 'a' * 64})
        entry, stats = subject.entry('test', records, ['42'], parent, Lexicon(), {'fixture': 'a' * 64}, 'b' * 64)
        self.assertEqual(keys_for([{'families': ['сталь', 'стать']}], 'family'), set(entry['keys']['family']))
        self.assertEqual([unsupported_surface_key('непонятнос')], entry['unsupportedSurfaceKeys'])
        self.assertEqual((2, 1, 1), (stats['surfaces'], stats['dictionaryResolved'], stats['dictionaryUnresolved']))
        bad = copy.deepcopy(parent); bad['keys']['sentence'] = []
        with self.assertRaisesRegex(ValueError, 'TEXT_FAMILY_PARENT_MISMATCH'):
            subject.entry('test', records, ['42'], bad, Lexicon(), {}, 'b' * 64)
        with self.assertRaisesRegex(ValueError, 'TEXT_ARTICLE_SCOPE'):
            subject.entry('test', records, ['43'], parent, Lexicon(), {}, 'b' * 64)
        long_word = [{'articleId': '42', 'text': 'а' * 33}]
        long_parent = segments.make_entry('test', long_word, ['42'], 'source', {})
        with self.assertRaisesRegex(ValueError, 'TEXT_FAMILY_SURFACE_TOO_LONG'):
            subject.entry('test', long_word, ['42'], long_parent, Lexicon(), {}, 'b' * 64)


if __name__ == '__main__':
    unittest.main()
