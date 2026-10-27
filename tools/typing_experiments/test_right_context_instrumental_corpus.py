from types import SimpleNamespace
import unittest

from right_context_instrumental_corpus import generate
from right_context_training_groups import query


def tag(lemma, pos, case=None):
    return SimpleNamespace(lemma=lemma, pos=pos, case=case, number='sing', gender='masc')


class Dictionary:
    def __init__(self):
        self.words = {'важен': (tag('важный', 'ADJS'),), 'вагон': (tag('вагон', 'NOUN', 'nomn'),),
                      'вагоном': (tag('вагон', 'NOUN', 'ablt'),),
                      'поезда': (tag('поезд', 'NOUN', 'gent'),)}

    def analyses(self, word):
        return self.words.get(word, ())


class InstrumentalCorpusTest(unittest.TestCase):
    def rows(self, lex=None):
        return generate(lex or Dictionary(), {'вагон': ['вагон', 'вагоном']}, pairs=[('важен', 'вагон', 'поезда')])

    def test_visible_complement_changes_intent_without_changing_query(self):
        rows, skipped = self.rows()
        self.assertFalse(skipped)
        unknown = [r for r in rows if r['kind'] == 'unknown_original' and r['applied'] == 'вагоном']
        self.assertTrue(unknown)
        for noun in [r for r in unknown if r['expectedApplied'] == 'вагоном']:
            predicate = next(r for r in unknown if r['original'] == noun['original']
                and r['leftContext'] == noun['leftContext'] and r['expectedApplied'] == 'важен')
            self.assertEqual(query(noun), query(predicate))
            self.assertNotEqual(noun['rightContext'], predicate['rightContext'])
            self.assertFalse(Dictionary().analyses(noun['original']))

    def test_controls_raw_acquisition_and_unfinished_retention_are_explicit(self):
        rows, _ = self.rows()
        self.assertEqual(len(rows), len({r['id'] for r in rows}))
        self.assertTrue(all(r['expectedApplied'] == r['applied'] for r in rows if r['kind'] != 'unknown_original'))
        self.assertTrue(any(r['applied'] == r['original'] and r['kind'] == 'unknown_original' for r in rows))
        self.assertTrue(all(r['contrastFamilies'] == ['вагон', 'важный'] for r in rows))
        for row in rows:
            self.assertNotIn('contrastEditCosts', row)
            if row['kind'] != 'correct_original':
                adjective, noun = row['contrastUnitDistances']
                self.assertTrue(1 <= adjective <= 3)
                self.assertEqual(1, noun)

    def test_wrong_case_unknown_or_ambiguous_forms_cannot_claim_pure_coverage(self):
        for extra in ((), (tag('вагон', 'NOUN', 'nomn'),), (tag('другой', 'ADJS'),)):
            lex = Dictionary()
            lex.words['вагоном'] = extra
            with self.assertRaisesRegex(ValueError, 'EMPTY_INSTRUMENTAL_CORPUS'):
                self.rows(lex)
        lex = Dictionary(); lex.words['поезда'] = ()
        with self.assertRaisesRegex(ValueError, 'INSTRUMENTAL_CORPUS_DICTIONARY'):
            self.rows(lex)


if __name__ == '__main__':
    unittest.main()
