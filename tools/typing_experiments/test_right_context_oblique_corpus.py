from types import SimpleNamespace
import unittest

from right_context_oblique_corpus import generate
from right_context_training_groups import query


def adjective(number='sing', gender='masc'):
    return SimpleNamespace(pos='ADJS', lemma='полезный', number=number, gender=gender, grammemes=())


class Dictionary:
    def __init__(self):
        self.words = {'полезен': (adjective(),), 'полезна': (adjective(gender='femn'),),
                      'полезно': (adjective(gender='neut'),), 'полезны': (adjective('plur', None),),
                      'аудитории': (SimpleNamespace(pos='NOUN', case='datv'),
                                    SimpleNamespace(pos='NOUN', case='gent'),
                                    SimpleNamespace(pos='NOUN', case='nomn'))}

    def analyses(self, word):
        return self.words.get(word, ())


class ObliqueCorpusTest(unittest.TestCase):
    def rows(self, lex=None, forms=None):
        lex = lex or Dictionary()
        return generate(lex, {'полезен': list(lex.words) if forms is None else forms},
                        predicates=['полезен'], complements=['аудитории'])

    def test_same_corruption_and_suffix_support_opposite_visible_left_agreement(self):
        rows, skipped = self.rows()
        self.assertFalse(skipped)
        selected = [r for r in rows if r['kind'] == 'unknown_original' and r['candidateForms'] == ['полезна', 'полезно']]
        self.assertTrue(selected)
        original = selected[0]['original']
        same = [r for r in selected if r['original'] == original and r['applied'] == 'полезно']
        self.assertEqual({'полезна', 'полезно'}, {r['expectedApplied'] for r in same})
        self.assertTrue(any(r['leftContext'] == 'она была ' and r['expectedApplied'] == 'полезна' for r in same))
        self.assertTrue(any(r['leftContext'] == 'это было ' and r['expectedApplied'] == 'полезно' for r in same))
        self.assertEqual({' аудитории.'}, {r['rightContext'] for r in same})

    def test_retention_controls_raw_acquisition_and_query_isolation(self):
        rows, _ = self.rows()
        self.assertTrue(all(r['expectedApplied'] == r['applied'] for r in rows if r['kind'] != 'unknown_original'))
        self.assertTrue(any(r['kind'] == 'unknown_original' and r['applied'] == r['original'] for r in rows))
        self.assertEqual(len(rows),len({r['id'] for r in rows}))
        for row in rows:
            self.assertEqual('train',row['split'])
            self.assertEqual(query(row),query(row | dict(expectedApplied='другое',rightContext=' иначе.')))

    def test_guessed_complement_or_missing_forms_cannot_be_silently_fabricated(self):
        lex = Dictionary(); lex.words['аудитории'] = ()
        with self.assertRaisesRegex(ValueError,'OBLIQUE_COMPLEMENT_DICTIONARY'):
            self.rows(lex)
        with self.assertRaisesRegex(ValueError,'EMPTY_OBLIQUE_CORPUS'):
            self.rows(forms=['полезен'])
        lex = Dictionary(); lex.words['полезен'] = ()
        with self.assertRaisesRegex(ValueError,'OBLIQUE_PREDICATE_DICTIONARY'):
            self.rows(lex)


if __name__ == '__main__':
    unittest.main()
