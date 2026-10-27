from types import SimpleNamespace
import unittest

from right_context_applied_features import FEATURES, FEATURE_NAMES, AppliedWordFeatures, extend_applied_features


def tag(pos='ADJS', lemma='готовый', case=None, number='sing', gender='masc'):
    return SimpleNamespace(pos=pos, lemma=lemma, case=case, number=number, gender=gender)


class Dictionary:
    def __init__(self):
        self.words = {'готов': (tag(),), 'готова': (tag(gender='femn'),),
            'готовая': (tag('ADJF', case='nomn', gender='femn'),),
            'спокоен': (tag(lemma='спокойный'),),
            'зал': (tag('NOUN', lemma='зал', case='nomn'),),
            'залом': (tag('NOUN', lemma='зал', case='ablt'),),
            'наш': (tag('ADJF', lemma='наш', case='nomn'),),
            'нашим': (tag('ADJF', lemma='наш', case='ablt'),),
            'он': (tag('NPRO', lemma='он', case='nomn'),),
            'и': (tag('CONJ', lemma='и'), tag('NPRO', lemma='и', case='nomn')),
            'ёлки': (tag('NOUN', lemma='ёлка', case='nomn', number='plur', gender=None),)}

    def analyses(self, word):
        return self.words.get(word, ())


class AppliedFeaturesTest(unittest.TestCase):
    def values(self, left='', original='готв', applied='готов', candidate='готова', lexicon=None):
        vector = AppliedWordFeatures(lexicon or Dictionary()).extract(left, original, applied, candidate)
        self.assertEqual(len(FEATURE_NAMES), len(vector))
        return dict(zip(FEATURE_NAMES, vector))

    def test_same_family_inflection_is_distinct_from_a_lemma_change(self):
        same = self.values()
        self.assertEqual(1, same['candidate_same_adjective_lemma'])
        self.assertEqual(0, same['candidate_different_adjective_lemma'])
        other = self.values(candidate='спокоен')
        self.assertEqual(0, other['candidate_same_adjective_lemma'])
        self.assertEqual(1, other['candidate_different_adjective_lemma'])

    def test_noun_and_full_adjective_transitions_remain_soft_features(self):
        noun = self.values(applied='зал')
        self.assertEqual(1, noun['applied_has_noun'])
        self.assertEqual(0, noun['applied_predicate_only'])
        full = self.values(applied='готовая')
        self.assertEqual(1, full['applied_has_full_adjective'])
        self.assertEqual(1, full['candidate_same_adjective_lemma'])
        self.assertEqual(0, full['candidate_has_full_adjective'])
        self.assertEqual(1, self.values(candidate='готовая')['candidate_has_full_adjective'])

    def test_known_original_and_raw_or_revised_state_come_from_words_not_labels(self):
        unknown = self.values(applied='готв', candidate='готв')
        self.assertEqual(0, unknown['original_dictionary_available'])
        self.assertEqual(1, unknown['applied_is_original'])
        self.assertEqual(1, unknown['candidate_is_original'])
        known = self.values(original='готов', applied='готов', candidate='готова')
        self.assertEqual(1, known['original_dictionary_available'])
        self.assertEqual(0, known['candidate_is_original'])
        self.assertEqual(1, self.values()['applied_dictionary_available'])

    def test_ambiguity_and_adverb_readings_are_not_erased(self):
        lexicon = Dictionary()
        lexicon.words['готов'] += (tag(lemma='другой'), tag('ADVB', lemma='готов'))
        v = self.values(lexicon=lexicon)
        self.assertEqual(1, v['applied_adjective_lemma_ambiguous'])
        self.assertEqual(1, v['applied_has_adverb'])
        self.assertEqual(0, v['applied_predicate_only'])
        self.assertEqual(1, v['candidate_same_adjective_lemma'])

    def test_adjacent_modifier_case_and_pronoun_are_independent_of_the_prior_role(self):
        v = self.values(left='нашим ', applied='готов', candidate='залом')
        self.assertEqual(1, v['left_modifier_available'])
        self.assertEqual(1, v['left_modifier_case_supported'])
        self.assertEqual(1, v['candidate_has_noun'])
        self.assertEqual(1, self.values(left='нашим ', candidate='зал')['left_modifier_case_conflict'])
        self.assertEqual(1, self.values(left='он ')['left_pronoun_nominative'])
        self.assertEqual(0, self.values(left='и ')['left_pronoun_nominative'])
        for left in ('наш', 'наш, ', 'prefix_наш ', 'наш. теперь '):
            self.assertEqual(0, self.values(left=left)['left_modifier_available'])

    def test_missing_cases_and_multiple_readings_cannot_establish_a_universal_conflict(self):
        lexicon = Dictionary()
        lexicon.words['нашим'] += (tag('ADJF', lemma='наш', case=None),)
        v = self.values(left='нашим ', candidate='зал', lexicon=lexicon)
        self.assertEqual(1, v['left_modifier_ambiguous'])
        self.assertEqual(0, v['left_modifier_case_conflict'])

    def test_normalization_layout_and_ownership_preserve_old_fields(self):
        v = self.values(original='ЁЛКИ', applied='ёлки', candidate='е\u0308лки')
        self.assertEqual(1, v['candidate_is_original'])
        self.assertEqual(1, v['applied_is_original'])
        previous = [float(i) for i in range(202)]
        full = extend_applied_features(previous, AppliedWordFeatures(Dictionary()), '', 'готв', 'готов', 'готова')
        self.assertEqual(FEATURES, len(full))
        self.assertEqual(tuple(previous), full[:202])
        previous[0] = -1
        self.assertEqual(0, full[0])

    def test_invalid_words_and_extensions_fail_explicitly(self):
        for word in ('', 'word', 'гот_в', 'я' * 65):
            with self.assertRaises(ValueError):
                self.values(original=word)
        for previous in ([0.] * 201, [float('nan')] * 202):
            with self.assertRaises(ValueError):
                extend_applied_features(previous, AppliedWordFeatures(Dictionary()), '', 'готв', 'готов', 'готова')
        class Invalid:
            def extract(self, *arguments):
                return (0.,)
        with self.assertRaises(ValueError):
            extend_applied_features([0.] * 202, Invalid(), '', 'готв', 'готов', 'готова')


if __name__ == '__main__':
    unittest.main()
