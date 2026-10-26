from collections import defaultdict
from types import SimpleNamespace
import unittest
import grammar_contrast_corpus as prior
import right_context_contrast_corpus as corpus
from right_context_grammar_features import completed_following_words


class Dictionary:
    def __init__(self):
        self.words = {}
        for left, right in corpus.PAIRS:
            self.words[left] = [SimpleNamespace(lemma=left, pos='ADJS', number='sing', gender='masc')]
            self.words[right] = [SimpleNamespace(lemma=left, pos='ADJS', number='plur', gender=None)]

    def analyses(self, word):
        return self.words.get(word, ())


class RightContrastsTest(unittest.TestCase):
    def test_deterministic_and_disjoint_from_disclosed_and_prior_predicate_forms(self):
        rows, skipped = corpus.generate(Dictionary())
        self.assertEqual((rows, skipped), corpus.generate(Dictionary()))
        self.assertEqual(len(rows), len({r['id'] for r in rows}))
        forms = {w for pair in corpus.PAIRS for w in pair}
        self.assertTrue(forms.isdisjoint({'виновен', 'виновны'} | {w for pair in prior.PREDICATES for w in pair}))
        self.assertTrue(all(r['split'] == 'train' for r in rows))
        self.assertTrue(all(r['purpose'] == 'AUTHORED_RIGHT_CONTEXT_TRAINING_ONLY' for r in rows))

    def test_same_unknown_typo_requires_opposing_results_from_the_right_context(self):
        dictionary = Dictionary()
        rows, _ = corpus.generate(dictionary)
        groups = defaultdict(list)
        for row in rows:
            if row['kind'] == 'unknown_original':
                self.assertFalse(dictionary.analyses(row['original']))
                self.assertTrue(completed_following_words(row['rightContext']))
                self.assertEqual(row['contrastEditCosts'], [prior.one_edit_cost(row['original'], word) for word in row['candidateForms']])
                groups[row['family'], row['original'], row['leftContext'], row['applied']].append(row)
        self.assertTrue(groups)
        for group in groups.values():
            self.assertEqual(set(group[0]['candidateForms']), {r['expectedApplied'] for r in group})

    def test_correct_original_and_weak_evidence_never_require_a_revision(self):
        dictionary = Dictionary()
        rows, _ = corpus.generate(dictionary)
        for row in rows:
            if row['kind'] != 'unknown_original':
                self.assertEqual(row['applied'], row['expectedApplied'])
            if row['kind'] == 'correct_original':
                self.assertEqual(row['original'], row['applied'])
                self.assertTrue(dictionary.analyses(row['original']))
        self.assertEqual(set(corpus.WEAK_SUFFIXES), {r['rightContext'] for r in rows if r['kind'] == 'insufficient_right_evidence'})

    def test_missing_or_different_lemma_analyses_are_not_silent_labels(self):
        for tags in [[], [SimpleNamespace(lemma='другой', pos='ADJS', number='plur', gender=None)]]:
            dictionary = Dictionary()
            dictionary.words[corpus.PAIRS[0][1]] = tags
            with self.assertRaisesRegex(ValueError, 'RIGHT_CONTEXT_PARADIGM_MISMATCH'):
                corpus.generate(dictionary)


if __name__ == '__main__':
    unittest.main()
