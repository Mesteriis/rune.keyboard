import math
import struct
import unittest

from right_context_applied_ranker import AppliedResidualForest, AppliedResidualRanker
from right_context_residual_ranker import NumericForest, ResidualRightContextRanker
from test_right_context_residual_ranker import model


class AppliedRankerTest(unittest.TestCase):
    def test_zero_head_keeps_base_and_new_fields_have_their_exact_offset(self):
        ranker = AppliedResidualRanker(model(), model(75, leaves=(0., 0.)))
        vector = [0.] * 221
        self.assertEqual(-1., ranker.raw_score(vector))
        self.assertEqual(.8 * math.tanh(-1 / 4), ranker.score(vector))
        ranker = AppliedResidualRanker(model(leaves=(0., 0.)), model(75, index=74))
        self.assertEqual(-1., ranker.raw_score(vector))
        vector[220] = 1.
        self.assertEqual(2., ranker.raw_score(vector))

    def test_old_and_new_profiles_cannot_silently_interpret_each_other(self):
        for blob in (model(56), model(178), model(221)):
            with self.assertRaises(ValueError):
                AppliedResidualForest.decode(blob)
        with self.assertRaises(ValueError):
            NumericForest.decode(model(75), 75)
        with self.assertRaises(ValueError):
            ResidualRightContextRanker(model(), model(75))
        ranker = AppliedResidualRanker(model(), model(75))
        for vector in ([0.] * 202, [0.] * 220, [float('nan')] * 221):
            with self.assertRaises(ValueError):
                ranker.score(vector)

    def test_new_profile_keeps_all_numeric_model_bounds(self):
        original = model(75)
        bad = [original[:-1], original + b'x', b'x' * 65537]
        for offset, value in ((8, 0), (8, 129), (20, 0), (20, 7), (24, 75)):
            blob = bytearray(original)
            struct.pack_into('<I', blob, offset, value)
            bad.append(blob)
        for offset, value in ((12, float('nan')), (16, 33.), (28, float('inf')), (32, 33.)):
            blob = bytearray(original)
            struct.pack_into('<f', blob, offset, value)
            bad.append(blob)
        for blob in bad:
            with self.assertRaises(ValueError):
                AppliedResidualForest.decode(blob)


if __name__ == '__main__':
    unittest.main()
