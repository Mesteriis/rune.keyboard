from types import SimpleNamespace
import unittest

from right_context_continuation_features import (
    FEATURES, FEATURE_NAMES, RightContextContinuationFeatures,
    continuation_prefixes, extend_continuation_features, scan_continuation,
)


def tag(pos='NOUN', number='sing', case='nomn', lemma=''):
    return SimpleNamespace(pos=pos, number=number, case=case, lemma=lemma)


class Dictionary:
    def __init__(self):
        self.words = {word: (tag(),) for word in ('покупка', 'продажа', 'тошнота', 'диарея', 'запор', 'друг')}
        self.words.update({
            'он': (tag('NPRO'),), 'другу': (tag(case='datv', lemma='друг'),),
            'друга': (tag(case='gent', lemma='друг'),),
            'другом': (tag(case='ablt', lemma='друг'),), 'с': (tag('PREP'),),
            'и': (tag('CONJ'), tag()), 'или': (tag('CONJ'),),
            'к': (tag('PREP'), tag()),
            'готов': (tag('ADJS', case=None),),
            'готовы': (tag('ADJS', 'plur', None),),
            'были': (tag('VERB', 'plur', None),),
            'была': (tag('VERB', case=None),),
            'позволяет': (tag('VERB', case=None),),
            'непреднамеренно': (tag('ADVB', case=None), tag('ADJS', case=None)),
        })

    def analyses(self, word):
        return self.words.get(word, ())


class ContinuationTest(unittest.TestCase):
    def values(self, right, left='', candidate='готовы', dictionary=None):
        values = RightContextContinuationFeatures(dictionary or Dictionary()).extract(left, right, candidate)
        self.assertEqual(len(FEATURE_NAMES), len(values))
        return dict(zip(FEATURE_NAMES, values))

    def test_commas_complete_words_without_hiding_the_rest_of_a_list(self):
        scan = scan_continuation(' тошнота, диарея или запор. чужая фраза ')
        self.assertEqual(('тошнота', 'диарея', 'или', 'запор'), scan.words)
        self.assertEqual((False, True, False, False), scan.comma_before)
        self.assertEqual('STRONG_BOUNDARY', scan.ending)
        values = self.values(' тошнота, диарея или запор.')
        self.assertEqual(1, values['continuation_comma_nominals'])
        self.assertEqual(1, values['continuation_alternative_link'])
        self.assertEqual(0, values['continuation_additive_link'])

    def test_unfinished_second_noun_never_supplies_its_morphology(self):
        for suffix in (' покупка и', ' покупка и ', ' покупка и прода'):
            values = self.values(suffix)
            self.assertEqual(0, values['continuation_additive_link'])
        self.assertEqual(1, self.values(' покупка и ')['continuation_pending_nominal_link'])
        self.assertEqual(1, self.values(' покупка и продажа ')['continuation_additive_link'])
        self.assertEqual(1, self.values(' покупка,')['continuation_pending_comma'])

    def test_reciprocal_requires_all_completed_words_and_no_internal_comma(self):
        for suffix in (' друг другу ', ' друг к другу ', ' друг друга ', ' друг с другом '):
            self.assertEqual(1, self.values(suffix)['continuation_reciprocal'])
        for suffix in (' друг другу', ' друг к другу', ' друг, другу ', ' друг к, другу '):
            self.assertEqual(0, self.values(suffix)['continuation_reciprocal'])
        self.assertEqual(1, self.values(' друг ')['continuation_possible_reciprocal'])

    def test_finite_after_subject_is_distinct_from_postsubject_copula(self):
        values = self.values(' он позволяет ', candidate='непреднамеренно')
        self.assertEqual(1, values['continuation_finite_after_subject'])
        self.assertEqual(1, values['candidate_adverb_reading'])
        self.assertEqual(1, values['continuation_finite_number_supported'])
        self.assertEqual(0, values['continuation_copula_after_subject'])
        self.assertEqual(1, self.values(' покупка была ')['continuation_copula_after_subject'])
        self.assertEqual(0, self.values(' он позволяет')['continuation_finite_after_subject'])
        for suffix in (' он, позволяет ', ' он а позволяет ', ' он но позволяет '):
            self.assertEqual(0, self.values(suffix)['continuation_finite_after_subject'])

    def test_function_homographs_do_not_supply_a_subject(self):
        for suffix in (' и позволяет ', ' к позволяет ', ' , он позволяет '):
            self.assertEqual(0, self.values(suffix)['continuation_subject_available'])

    def test_adjacent_left_finite_preserves_plural_and_does_not_search_backwards(self):
        values = self.values(' покупка ', left='где были ')
        self.assertEqual(1, values['adjacent_left_copula_available'])
        self.assertEqual(1, values['adjacent_left_number_supported'])
        self.assertEqual(0, values['adjacent_left_number_conflict'])
        self.assertEqual(1, self.values(' покупка ', left='где были ', candidate='готов')['adjacent_left_number_conflict'])
        for left in ('были', 'были, ', 'были теперь ', 'prefix_были ', 'были. теперь '):
            self.assertEqual(0, self.values(' покупка ', left=left)['adjacent_left_finite_available'])
        dictionary = Dictionary()
        dictionary.words['были'] += (tag('VERB', 'sing', None),)
        values = self.values(' покупка ', left='были ', candidate='готов', dictionary=dictionary)
        self.assertEqual(1, values['adjacent_left_number_ambiguous'])
        self.assertEqual(1, values['adjacent_left_number_supported'])
        self.assertEqual(0, values['adjacent_left_number_conflict'])

    def test_unknown_finite_number_cannot_establish_conflict(self):
        dictionary = Dictionary()
        dictionary.words['были'] += (tag('VERB', None, None),)
        self.assertEqual(0, self.values(' покупка ', left='были ', candidate='готов', dictionary=dictionary)['adjacent_left_number_conflict'])

    def test_strong_boundaries_and_identifiers_cannot_launder_evidence(self):
        for boundary in '.!?;:\n\r':
            scan = scan_continuation(' он' + boundary + ' позволяет ')
            self.assertEqual(('он',), scan.words)
            self.assertEqual('STRONG_BOUNDARY', scan.ending)
        for suffix in (' он_тест позволяет ', ' он-тест позволяет ', ' он2 позволяет ', ' он😀 позволяет '):
            self.assertEqual((), scan_continuation(suffix).words)
            self.assertEqual('INVALID_BOUNDARY', scan_continuation(suffix).ending)
        for suffix in ('он ', ', он ', '\nон '):
            self.assertEqual('NO_SEPARATOR', scan_continuation(suffix).ending)

    def test_bounds_cannot_manufacture_a_completed_word_or_clause(self):
        self.assertEqual('CHAR_LIMIT', scan_continuation(' ' * 125 + 'она' + '.').ending)
        self.assertEqual((), scan_continuation(' ' * 125 + 'она' + '.').words)
        self.assertEqual('INVALID_BOUNDARY', scan_continuation(' ' + 'я' * 33 + ' ').ending)
        scan = scan_continuation(' он ' * 9 + '.')
        self.assertEqual(8, len(scan.words))
        self.assertEqual('WORD_LIMIT', scan.ending)
        self.assertEqual('OPEN', scan_continuation(' он ').ending)

    def test_new_layout_does_not_mutate_or_reinterpret_old_fields(self):
        previous = [float(i) for i in range(178)]
        extractor = RightContextContinuationFeatures(Dictionary())
        values = extend_continuation_features(previous, extractor, 'были ', ' покупка и продажа ', 'готовы')
        self.assertEqual(FEATURES, len(values))
        self.assertEqual(tuple(previous), values[:178])
        previous[0] = -100
        self.assertEqual(0, values[0])
        for bad in ([0.] * 177, [float('nan')] * 178):
            with self.assertRaises(ValueError):
                extend_continuation_features(bad, extractor, '', '', 'готовы')

    def test_timeline_observes_comma_and_closure_even_without_another_word(self):
        events = list(continuation_prefixes(' покупка  , продажа . ещё слова '))
        self.assertEqual([' покупка ', ' покупка  ,', ' покупка  , продажа ',
                          ' покупка  , продажа .'], [prefix for _, prefix in events])
        self.assertEqual([1, 1, 2, 2], [len(scan.words) for scan, _ in events])
        self.assertEqual('STRONG_BOUNDARY', events[-1][0].ending)
        self.assertEqual([], list(continuation_prefixes(' покупка')))
        self.assertEqual([' он ', ' он провёл '],
                         [prefix for _, prefix in continuation_prefixes(' он провёл неизве')])


if __name__ == '__main__':
    unittest.main()
