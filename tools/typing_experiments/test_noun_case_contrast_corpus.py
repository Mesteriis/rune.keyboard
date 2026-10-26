from collections import defaultdict
from types import SimpleNamespace
import unittest

import grammar_contrast_corpus as old
import noun_case_contrast_corpus as corpus


class Dictionary:
    def __init__(self):
        self.words = {}
        for left, right in corpus.OBJECTS:
            self.words[left] = [SimpleNamespace(lemma=left, pos='NOUN', case='accs')]
            self.words[right] = [SimpleNamespace(lemma=left, pos='NOUN', case='ablt')]

    def analyses(self, word):
        return self.words.get(word, ())


class NounCaseContrastsTest(unittest.TestCase):
    def test_opposing_labels_require_shared_unknown_typo_and_complete_retention_controls(self):
        dictionary = Dictionary()
        rows, skipped = corpus.generate(dictionary)
        self.assertFalse(skipped)
        families = defaultdict(list)
        for r in rows:
            families[r['family']].append(r)
            self.assertEqual(r['purpose'], 'AUTHORED_CONTRAST_TRAINING_ONLY')
            self.assertEqual(r['split'], 'train')
            self.assertEqual(r['contrastKind'], 'object')
            if r['noAuto']:
                self.assertEqual(r['typed'], r['expectedSpelling'])
                self.assertTrue(dictionary.analyses(r['typed']))
            else:
                self.assertFalse(dictionary.analyses(r['typed']))
                self.assertEqual(r['contrastEditCosts'], [old.one_edit_cost(r['typed'], w)
                                                          for w in r['contrastCandidates']])
        self.assertEqual(len(corpus.OBJECTS), len(families))
        for family in families.values():
            typos = {r['typed'] for r in family if not r['noAuto']}
            for typo in typos:
                self.assertEqual(2, len({r['expectedSpelling'] for r in family if r['typed'] == typo}))
            for context in corpus.ACCUSATIVE_CONTEXTS + corpus.INSTRUMENTAL_CONTEXTS:
                controls = [r for r in family if r['noAuto'] and r['prefix'] == context]
                self.assertEqual(2, len(controls))
                self.assertEqual(set(family[0]['contrastCandidates']), {r['typed'] for r in controls})

    def test_deterministic_unique_and_disjoint_from_disclosed_and_prior_object_forms(self):
        rows, skipped = corpus.generate(Dictionary())
        self.assertEqual((rows, skipped), corpus.generate(Dictionary()))
        self.assertEqual(len(rows), len({r['id'] for r in rows}))
        forms = {w for r in rows for w in r['contrastCandidates']}
        self.assertTrue(forms.isdisjoint({w for pair in old.OBJECTS for w in pair}))
        self.assertTrue(forms.isdisjoint({'фотографию', 'фотографией', 'виновны', 'виновен'}))

    def test_known_dictionary_form_never_becomes_a_corruption(self):
        dictionary = Dictionary()
        initial, _ = corpus.generate(dictionary)
        word = next(r['typed'] for r in initial if not r['noAuto'])
        dictionary.words[word] = [SimpleNamespace(lemma=word, pos='NOUN', case='nomn')]
        changed, _ = corpus.generate(dictionary)
        self.assertFalse(any(r['typed'] == word for r in changed if not r['noAuto']))

    def test_wrong_case_or_lemma_cannot_silently_supply_training_labels(self):
        for tags in [[SimpleNamespace(lemma='иной', pos='NOUN', case='ablt')],
                     [SimpleNamespace(lemma=corpus.OBJECTS[0][0], pos='NOUN', case='gent')]]:
            dictionary = Dictionary()
            dictionary.words[corpus.OBJECTS[0][1]] = tags
            with self.assertRaisesRegex(ValueError, 'NOUN_CASE_DICTIONARY_MISMATCH'):
                corpus.generate(dictionary)


if __name__ == '__main__':
    unittest.main()
