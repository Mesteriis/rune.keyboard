from types import SimpleNamespace
import unittest

from right_context_left_sequence_features import (
    FEATURES, FEATURE_NAMES, LeftSequenceFeatures, extend_left_sequence_features,
)


def tag(pos, lemma='', case=None, number='sing', gender='femn'):
    return SimpleNamespace(pos=pos, lemma=lemma, case=case, number=number, gender=gender)


class Dictionary:
    def __init__(self):
        self.words = {
            'умная': (tag('ADJF', 'умный', 'nomn'),),
            'умна': (tag('ADJS', 'умный'),),
            'готова': (tag('ADJS', 'готовый'),),
            'готовая': (tag('ADJF', 'готовый', 'nomn'),),
            'готов': (tag('ADJS', 'готовый', gender='masc'),),
            'готовы': (tag('ADJS', 'готовый', number='plur', gender=None),),
            'и': (tag('CONJ'), tag('INTJ'), tag('NOUN', 'и', 'nomn')),
            'но': (tag('CONJ'), tag('INTJ')), 'не': (tag('PRCL'),),
            'очень': (tag('ADVB'),), 'она': (tag('NPRO', 'она', 'nomn'),),
            'эх': (tag('INTJ'),),
            'девочка': (tag('NOUN', 'девочка', 'nomn'),),
            'пришла': (tag('VERB', 'прийти'),),
            'оказалась': (tag('VERB', 'оказаться'),),
            'был': (tag('VERB', 'быть', gender='masc'),),
            'залом': (tag('NOUN', 'зал', 'ablt', gender='masc'),),
            'здания': (tag('NOUN', 'здание', 'gent', gender='neut'),
                       tag('NOUN', 'здание', 'nomn', number='plur', gender='neut')),
            'воды': (tag('NOUN', 'вода', 'gent'),),
            'в': (tag('PREP'), tag('NOUN', 'в', 'gent')),
        }

    def analyses(self, word):
        return self.words.get(word, ())


class LeftSequenceTest(unittest.TestCase):
    def values(self, left='', right='', applied='готовая', candidate='готова', lexicon=None):
        values = LeftSequenceFeatures(lexicon or Dictionary()).extract(left, right, applied, candidate)
        self.assertEqual(len(FEATURE_NAMES), len(values))
        return dict(zip(FEATURE_NAMES, values))

    def test_full_and_short_coordination_remain_distinguishable(self):
        full = self.values('умная, но очень не ')
        short = self.values('умна и не ')
        self.assertEqual(1, full['left_sequence_full_adjective'])
        self.assertEqual(0, full['left_sequence_short_predicate'])
        self.assertEqual(0, short['left_sequence_full_adjective'])
        self.assertEqual(1, short['left_sequence_short_predicate'])
        for v in (full, short):
            self.assertEqual(1, v['left_sequence_conjunction'])
            self.assertEqual(1, v['left_sequence_negation'])
            self.assertEqual(1, v['left_sequence_gender_supported'])
            self.assertEqual(1, v['left_sequence_bridge_ambiguous'])
        self.assertEqual(1, full['left_sequence_adverb'])
        self.assertEqual(3 / 8, full['left_sequence_skipped_words'])

    def test_no_remote_adjective_across_content_unknown_or_hard_boundary(self):
        for middle in ('девочка ', 'пришла ', 'она ', 'абракадабра ', 'в ', 'эх ',
                       'word ', 'x_ ', '. ', '; ', '\n', '!!! '):
            v = self.values('умная ' + middle + 'и не ')
            self.assertEqual(0, v['left_sequence_adjective_available'], middle)
            self.assertEqual(0, v['left_sequence_conjunction'], middle)
            self.assertEqual(0, v['left_sequence_skipped_words'], middle)

    def test_unfinished_word_and_word_window_cannot_supply_adjective(self):
        for left in ('умная', 'умная и н', 'умная ' + 'не ' * 8,
                     'умная ' + ' ' * 128 + 'и не '):
            self.assertEqual(0, self.values(left)['left_sequence_adjective_available'], left)
        self.assertEqual(1, self.values('умная ' + 'не ' * 7)['left_sequence_adjective_available'])

    def test_unknown_agreement_and_homographs_preserve_uncertainty(self):
        lex = Dictionary()
        lex.words['умная'] += (tag('NOUN', 'умная', 'nomn'), tag('ADJF', 'умный', 'nomn', gender=None))
        v = self.values('умная и ', candidate='готов', lexicon=lex)
        self.assertEqual(1, v['left_sequence_adjective_ambiguous'])
        self.assertEqual(0, v['left_sequence_gender_conflict'])
        self.assertEqual(1, self.values('умная и ', candidate='готов')['left_sequence_gender_conflict'])
        self.assertEqual(1, self.values('умная и ', candidate='готовы')['left_sequence_number_conflict'])
        lex.words['очень'] += (tag('NOUN', 'очень', 'nomn'),)
        self.assertEqual(0, self.values('умная очень ', lexicon=lex)['left_sequence_adjective_available'])

    def test_linking_lemma_is_possible_reading_not_all_finite_verbs(self):
        self.assertEqual(1, self.values('оказалась ')['adjacent_left_linking_lemma_possible'])
        for left in ('пришла ', 'оказалась', 'оказалась, ', 'оказалась. и '):
            self.assertEqual(0, self.values(left)['adjacent_left_linking_lemma_possible'])

    def test_instrumental_noun_and_genitive_complement_keep_case_alternatives(self):
        v = self.values('был ', ' здания.', applied='залом', candidate='залом')
        for field in ('applied_instrumental_noun', 'applied_pure_instrumental_noun',
                      'candidate_instrumental_noun', 'right_genitive_noun',
                      'right_nominative_plural_noun', 'right_genitive_noun_ambiguous'):
            self.assertEqual(1, v[field], field)
        self.assertEqual(0, v['right_pure_genitive_noun'])
        self.assertEqual(1, self.values(right=' воды.')['right_pure_genitive_noun'])
        for right in (' воды', 'воды.', ' воды_suffix ', ' в '):
            self.assertEqual(0, self.values(right=right)['right_genitive_noun'])
        lex = Dictionary()
        lex.words['залом'] += (tag('ADJS', 'залый'),)
        v = self.values(applied='залом', lexicon=lex)
        self.assertEqual(1, v['applied_instrumental_noun'])
        self.assertEqual(0, v['applied_pure_instrumental_noun'])

    def test_append_only_layout_normalization_and_validation(self):
        extractor = LeftSequenceFeatures(Dictionary())
        previous = [float(i) for i in range(221)]
        full = extend_left_sequence_features(previous, extractor, 'УМНАЯ И НЕ ', '', 'ГОТОВАЯ', 'ГОТОВА')
        self.assertEqual(242, FEATURES)
        self.assertEqual(FEATURES, len(full))
        self.assertEqual(tuple(previous), full[:221])
        previous[0] = -1
        self.assertEqual(0, full[0])
        for bad in ([0.] * 220, [float('nan')] * 221, ['0'] * 221):
            with self.assertRaises(ValueError):
                extend_left_sequence_features(bad, extractor, '', '', 'готовая', 'готова')
        for bad in ('', 'word', 'я' * 65, 'гот_ова'):
            with self.assertRaises(ValueError):
                extractor.extract('', '', bad, 'готова')


if __name__ == '__main__':
    unittest.main()
