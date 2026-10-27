from types import SimpleNamespace
import unittest

from right_context_signature_weights import MAX_FACTOR, TargetSignatureWeights
from test_right_context_training_weights import row


class Dictionary:
    def __init__(self):
        self.words = {'готов': ('ADJS',), 'готовая': ('ADJF',), 'зал': ('NOUN',),
                      'смешанный': ('NOUN', 'ADJS', 'ADJS')}

    def analyses(self, word):
        return tuple(SimpleNamespace(pos=part) for part in self.words.get(word, ()))


class SignatureWeightsTest(unittest.TestCase):
    def test_rare_targets_gain_weight_without_changing_total_strong_mass(self):
        lex = Dictionary()
        rows = [row()] * 9 + [row(expectedApplied='зал')]
        policy = TargetSignatureWeights.fit(rows, lex)
        weights = [policy.weight(r, lex) for r in rows]
        self.assertGreater(weights[-1], weights[0])
        self.assertAlmostEqual(30., sum(weights))
        self.assertTrue(all(0 < weight <= 3 * MAX_FACTOR for weight in weights))

    def test_cap_limits_amplification_for_tiny_classes(self):
        lex = Dictionary(); rows = [row()] * 1000 + [row(expectedApplied='зал')]
        policy = TargetSignatureWeights.fit(rows, lex)
        factors = {key: factor for key, _, factor in policy.entries}
        self.assertEqual(MAX_FACTOR, factors[('NOUN',)])
        self.assertAlmostEqual(MAX_FACTOR, policy.weight(rows[-1], lex) / policy.weight(rows[0], lex))

    def test_mixed_readings_are_a_separate_order_independent_signature(self):
        lex = Dictionary(); rows = [row(), row(expectedApplied='смешанный')]
        first = TargetSignatureWeights.fit(rows, lex)
        lex.words['смешанный'] = ('ADJS', 'NOUN')
        second = TargetSignatureWeights.fit(reversed(rows), lex)
        self.assertEqual(first, second)
        self.assertEqual({('ADJS',), ('ADJS', 'NOUN')}, {key for key, _, _ in first.entries})

    def test_three_strong_intents_and_retention_controls_remain_distinct(self):
        lex = Dictionary(); rows = [row(applied=a) for a in ('готв', 'готов', 'готова')]
        policy = TargetSignatureWeights.fit(rows, lex)
        self.assertEqual([3., 3., 3.], [policy.weight(r, lex) for r in rows])
        for r in (row(kind='insufficient_right_evidence', expectedApplied='готова'),
                  row(kind='correct_original', original='готов', applied='готов')):
            self.assertEqual(1., policy.weight(r, lex))

    def test_invalid_data_unknown_dictionary_and_unseen_signatures_fail_explicitly(self):
        lex = Dictionary()
        for rows in ([], [row(split='holdout')], [row(kind='insufficient_right_evidence')],
                     [row(expectedApplied='нетвсловаре')]):
            with self.assertRaises(ValueError):
                TargetSignatureWeights.fit(rows, lex)
        policy = TargetSignatureWeights.fit([row()], lex)
        with self.assertRaisesRegex(ValueError, 'NOT_FITTED'):
            policy.weight(row(expectedApplied='зал'), lex)
        lex.words['готов'] = (None,)
        with self.assertRaisesRegex(ValueError, 'DICTIONARY'):
            policy.weight(row(), lex)


if __name__ == '__main__':
    unittest.main()
