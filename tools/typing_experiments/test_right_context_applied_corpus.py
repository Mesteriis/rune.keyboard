from types import SimpleNamespace
import unittest

from right_context_applied_corpus import generate
from right_context_training_groups import query


def tag(pos, gender='femn', case=None, grammemes=()):
    return SimpleNamespace(pos=pos, lemma='полезный', gender=gender, number='sing', case=case, grammemes=frozenset(grammemes))


class Dictionary:
    def __init__(self):
        self.words = {'полезен': (tag('ADJS', 'masc'),), 'полезна': (tag('ADJS'),),
                      'полезная': (tag('ADJF', case='nomn'),)}

    def analyses(self, word):
        return self.words.get(word, ())


class AppliedCorpusTest(unittest.TestCase):
    def rows(self):
        lexicon = Dictionary()
        rows, skipped = generate(lexicon, {'полезен': tuple(lexicon.words)}, pairs=[('полезен', 'полезны')])
        self.assertFalse(skipped)
        return rows

    def test_full_adjective_is_both_a_retained_target_and_a_repairable_wrong_state(self):
        rows = self.rows()
        self.assertTrue(any(r['applied'] == 'полезная' and r['expectedApplied'] == 'полезная'
                            and r['kind'] == 'unknown_original' for r in rows))
        self.assertTrue(any(r['applied'] == 'полезная' and r['expectedApplied'] == 'полезна'
                            and r['kind'] == 'unknown_original' for r in rows))
        self.assertTrue(any(r['applied'] == 'полезна' and r['expectedApplied'] == 'полезная'
                            and r['kind'] == 'unknown_original' for r in rows))

    def test_correct_originals_and_unresolved_clauses_are_retained(self):
        rows = self.rows()
        self.assertTrue(all(r['expectedApplied'] == r['applied'] for r in rows if r['kind'] != 'unknown_original'))
        self.assertTrue(all(r['original'] == r['applied'] for r in rows if r['kind'] == 'correct_original'))
        self.assertEqual(len(rows), len({r['id'] for r in rows}))
        self.assertTrue(all(r['family'] == 'полезный' and r['split'] == 'train' for r in rows))

    def test_queries_are_label_and_following_context_independent(self):
        row = self.rows()[0]
        self.assertEqual(query(row), query(row | dict(expectedApplied='полезная', applied='полезная', rightContext=' другая фраза.')))

    def test_missing_dictionary_forms_are_reported_without_inventing_targets(self):
        lexicon = Dictionary()
        with self.assertRaisesRegex(ValueError, 'EMPTY_APPLIED_ROLE_CORPUS'):
            generate(lexicon, {'полезен': ['полезен']}, pairs=[('полезен', 'полезны')])
        lexicon.words['полезен'] = ()
        with self.assertRaisesRegex(ValueError, 'APPLIED_CORPUS_PARADIGM'):
            generate(lexicon, {}, pairs=[('полезен', 'полезны')])

    def test_superlative_sort_order_cannot_remove_an_available_positive_pair(self):
        lexicon = Dictionary()
        lexicon.words['наиполезнейшая'] = (tag('ADJF', case='nomn', grammemes={'Supr'}),)
        rows, skipped = generate(lexicon, {'полезен': tuple(lexicon.words)}, pairs=[('полезен', 'полезны')])
        self.assertFalse(skipped)
        self.assertEqual({'полезна', 'полезная'}, {word for row in rows for word in row['candidateForms']})


if __name__ == '__main__':
    unittest.main()
