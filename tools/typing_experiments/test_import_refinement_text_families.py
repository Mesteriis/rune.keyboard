from types import SimpleNamespace
import copy
import unittest

import import_refinement_text_families as subject
from holdout_ledger import keys_for
from source_identities import unsupported_surface_key


class RefinementTextFamilyTest(unittest.TestCase):
    def test_parent_articles_and_dictionary_analyses(self):
        class Lexicon:
            def analyses(self, word):
                return [SimpleNamespace(lemma='стать'), SimpleNamespace(lemma='сталь')] if word == 'стали' else []
        rows = [{'articleId': '42', 'text': 'Стали несловарное'}]
        parent = {'id': 'public-ranker-history-train', 'keys': {'article': sorted(keys_for([{'article': '42'}], 'article'))}}
        source, family, counts = subject.partition_entries('train', rows, ['42'], parent, Lexicon(), {'a': 'a' * 64}, 'b' * 64)
        self.assertEqual(['public-ranker-history-train'], source['parentEntries'])
        self.assertEqual([source['id']], family['parentEntries'])
        self.assertEqual(keys_for([{'families': ['стать', 'сталь']}], 'family'), set(family['keys']['family']))
        self.assertEqual([unsupported_surface_key('несловарное')], family['unsupportedSurfaceKeys'])
        self.assertEqual(1, counts['dictionaryUnresolved'])
        bad = copy.deepcopy(parent); bad['keys']['article'] = []
        with self.assertRaisesRegex(ValueError, 'REFINEMENT_TEXT_PARENT_ARTICLES'):
            subject.partition_entries('train', rows, ['42'], bad, Lexicon(), {}, 'b' * 64)
        with self.assertRaisesRegex(ValueError, 'REFINEMENT_TEXT_PARENT'):
            subject.partition_entries('dev', rows, ['42'], parent, Lexicon(), {}, 'b' * 64)
        with self.assertRaisesRegex(ValueError, 'TEXT_ARTICLE_SCOPE'):
            subject.partition_entries('train', rows, ['43'], parent, Lexicon(), {}, 'b' * 64)


if __name__ == '__main__':
    unittest.main()
