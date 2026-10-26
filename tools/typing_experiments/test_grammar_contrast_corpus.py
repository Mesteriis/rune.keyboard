from collections import defaultdict
from types import SimpleNamespace
import unittest

import grammar_contrast_corpus as corpus


def tag(lemma, pos, **kwargs):
    return SimpleNamespace(lemma=lemma, pos=pos, person=kwargs.get('person'),
                           number=kwargs.get('number'), gender=kwargs.get('gender'),
                           case=kwargs.get('case'))


class Dictionary:
    def __init__(self):
        self.words = {}
        for left, right in corpus.VERBS:
            self.words[left] = [tag(left, 'INFN')]
            self.words[right] = [tag(left, 'VERB', person='2per', number='sing')]
        for left, right in corpus.PREDICATES:
            self.words[left] = [tag(left, 'ADJS', number='sing', gender='masc')]
            self.words[right] = [tag(left, 'ADJS', number='plur')]
        for left, right in corpus.OBJECTS:
            self.words[left] = [tag(left, 'NOUN', case='accs')]
            self.words[right] = [tag(left, 'NOUN', case='ablt')]

    def analyses(self, word):
        return self.words.get(word, ())


class GrammarContrastCorpusTest(unittest.TestCase):
    def test_neighborhood_is_exactly_one_edit_and_contains_shared_corruption(self):
        self.assertIn('учищься', corpus.one_edit_words('учиться'))
        self.assertIn('учищься', corpus.one_edit_words('учишься'))
        self.assertNotIn('учиться', corpus.one_edit_words('учиться'))
        self.assertIn('книг', corpus.one_edit_words('книга'))
        self.assertIn('книгаа', corpus.one_edit_words('книга'))

    def test_each_typo_has_opposing_targets_and_same_context_retention_controls(self):
        dictionary = Dictionary()
        rows, skipped = corpus.generate(dictionary)
        self.assertFalse(skipped)
        by_family = defaultdict(list)
        for row in rows:
            by_family[row['family']].append(row)
            self.assertEqual(row['split'], 'train')
            self.assertEqual(row['purpose'], 'AUTHORED_CONTRAST_TRAINING_ONLY')
        for family_rows in by_family.values():
            typos = [row for row in family_rows if not row['noAuto']]
            self.assertEqual(len(typos), 6)
            self.assertEqual(len({row['typed'] for row in typos}), 1)
            self.assertEqual(len({row['expectedSpelling'] for row in typos}), 2)
            for row in typos:
                self.assertFalse(dictionary.analyses(row['typed']))
                for form in row['contrastCandidates']:
                    self.assertIn(row['typed'], corpus.one_edit_words(form))
                    self.assertTrue(any(control['prefix'] == row['prefix'] and
                                        control['typed'] == control['expectedSpelling'] == form and
                                        control['noAuto'] for control in family_rows))

    def test_repeatable_and_excludes_disclosed_targets(self):
        first = corpus.generate(Dictionary())
        self.assertEqual(first, corpus.generate(Dictionary()))
        targets = {form for row in first[0] for form in row['contrastCandidates']}
        self.assertTrue(targets.isdisjoint({'фотографию', 'фотографией', 'злиться', 'злишься',
                                          'научиться', 'научишься', 'заплатить', 'заплатишь',
                                          'виновен', 'виновны'}))

    def test_malformed_dictionary_paradigm_fails_closed(self):
        dictionary = Dictionary()
        dictionary.words['говоришь'] = [tag('другой', 'INFN')]
        with self.assertRaisesRegex(ValueError, 'PARADIGM_DICTIONARY_MISMATCH'):
            corpus.generate(dictionary)

    def test_dictionary_word_is_never_used_as_typo(self):
        dictionary = Dictionary()
        rows, _ = corpus.generate(dictionary)
        selected = rows[0]['typed']
        dictionary.words[selected] = [tag('известный', 'ADJF')]
        changed, _ = corpus.generate(dictionary)
        self.assertTrue(all(row['typed'] != selected for row in changed if not row['noAuto']))


if __name__ == '__main__':
    unittest.main()
