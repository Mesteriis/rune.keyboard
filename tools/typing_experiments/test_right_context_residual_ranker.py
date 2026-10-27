import math
import struct
import unittest

from right_context_residual_ranker import NumericForest, ResidualRightContextRanker, structural_features


def model(count=178, index=0, border=.5, leaves=(-1., 2.), scale=1., bias=0.):
    return (struct.pack('<4sIIff', b'RET2', count, 1, scale, bias)
            + struct.pack('<IIf', 1, index, border) + struct.pack('<ff', *leaves))


class ResidualRankerTest(unittest.TestCase):
    def test_zero_correction_preserves_frozen_base_raw_and_bounded_scores(self):
        base = model(scale=.75, bias=.25)
        ranker = ResidualRightContextRanker(base, model(56, leaves=(0., 0.)))
        forest = NumericForest.decode(base, 178)
        for value in (-1e300, -.3, .5, .50000000001, .7, 1e300):
            vector = [value] + [0.] * 201
            raw = forest.score(vector[:178])
            self.assertEqual(raw, ranker.raw_score(vector))
            self.assertEqual(.8 * math.tanh(raw / 4), ranker.score(vector))

    def test_structural_head_cannot_see_lexical_fields(self):
        ranker = ResidualRightContextRanker(model(leaves=(0., 0.)), model(56))
        vector = [0.] * 202
        before = ranker.raw_score(vector)
        vector[:146] = [19.] * 146
        self.assertEqual(before, ranker.raw_score(vector))
        vector[146] = 1.
        self.assertNotEqual(before, ranker.raw_score(vector))
        self.assertEqual(tuple(vector[146:]), structural_features(vector))

    def test_strict_float32_border_and_finite_overflow_match_runtime_semantics(self):
        forest = NumericForest.decode(model(), 178)
        next_float = struct.unpack('<f', struct.pack('<I', 0x3f000001))[0]
        for value, expected in ((.5, -1.), (.5 + 1e-12, -1.), (next_float, 2.), (1e300, 2.), (-1e300, -1.)):
            self.assertEqual(expected, forest.score([value] + [0.] * 177))

    def test_additive_raw_score_is_bounded_only_after_composition(self):
        ranker = ResidualRightContextRanker(model(leaves=(2., 2.)), model(56, leaves=(3., 3.)))
        vector = [0.] * 202
        self.assertEqual(5., ranker.raw_score(vector))
        self.assertEqual(.8 * math.tanh(5 / 4), ranker.score(vector))
        self.assertNotEqual(.8 * math.tanh(2 / 4) + .8 * math.tanh(3 / 4), ranker.score(vector))

    def test_invalid_vectors_and_wrong_model_layouts_are_rejected(self):
        ranker = ResidualRightContextRanker(model(), model(56))
        for vector in ([0.] * 201, [0.] * 203, [float('nan')] * 202, [float('inf')] * 202, ['0'] * 202):
            with self.assertRaises(ValueError):
                ranker.score(vector)
        with self.assertRaises(ValueError):
            ResidualRightContextRanker(model(56), model())
        with self.assertRaises(ValueError):
            NumericForest.decode(model(146), 146)

    def test_model_headers_bounds_truncation_and_trailing_bytes_fail_closed(self):
        base = model()
        bad = [b'', base[:-1], base + b'x', b'x' * 65537, b'RET1' + base[4:]]
        for offset, value in ((8, 0), (8, 129), (20, 0), (20, 7), (24, 178)):
            blob = bytearray(base)
            struct.pack_into('<I', blob, offset, value)
            bad.append(blob)
        for offset, value in ((12, float('nan')), (12, 33.), (16, float('inf')),
                              (28, float('nan')), (28, 33.), (32, float('nan')), (36, -33.)):
            blob = bytearray(base)
            struct.pack_into('<f', blob, offset, value)
            bad.append(blob)
        for blob in bad:
            with self.assertRaises(ValueError):
                NumericForest.decode(blob, 178)

    def test_decoded_model_and_feature_views_do_not_alias_callers(self):
        blob = bytearray(model())
        forest = NumericForest.decode(blob, 178)
        struct.pack_into('<f', blob, 32, 20.)
        self.assertEqual(-1., forest.score([0.] * 178))
        vector = [0.] * 202
        structural = structural_features(vector)
        vector[146] = 1.
        self.assertEqual(0., structural[0])


if __name__ == '__main__':
    unittest.main()
