import math
import struct
import unittest

from right_context_left_role_ranker import LeftRoleResidualForest, LeftRoleResidualRanker
from right_context_residual_ranker import NumericForest, ResidualRightContextRanker
from right_context_applied_ranker import AppliedResidualForest
from test_right_context_residual_ranker import model


class LeftRoleRankerTest(unittest.TestCase):
    def test_zero_head_keeps_base_and_new_fields_have_their_exact_offset(self):
        ranker = LeftRoleResidualRanker(model(), model(96, leaves=(0., 0.)))
        vector = [0.] * 242
        self.assertEqual(-1., ranker.raw_score(vector))
        self.assertEqual(.8 * math.tanh(-1 / 4), ranker.score(vector))
        ranker = LeftRoleResidualRanker(model(leaves=(0., 0.)), model(96, index=95))
        self.assertEqual(-1., ranker.raw_score(vector))
        vector[241] = 1.
        self.assertEqual(2., ranker.raw_score(vector))

    def test_old_and_new_profiles_cannot_silently_interpret_each_other(self):
        for blob in (model(56), model(75), model(178), model(221), model(242)):
            with self.assertRaises(ValueError):
                LeftRoleResidualForest.decode(blob)
        with self.assertRaises(ValueError):
            NumericForest.decode(model(96), 96)
        with self.assertRaises(ValueError):
            ResidualRightContextRanker(model(), model(96))
        with self.assertRaises(ValueError):
            AppliedResidualForest.decode(model(96))
        ranker = LeftRoleResidualRanker(model(), model(96))
        for vector in ([0.] * 202, [0.] * 241, [float('nan')] * 242):
            with self.assertRaises(ValueError):
                ranker.score(vector)

    def test_new_profile_keeps_all_numeric_model_bounds(self):
        original = model(96)
        bad = [original[:-1], original + b'x', b'x' * 65537]
        for offset, value in ((8, 0), (8, 129), (20, 0), (20, 7), (24, 96)):
            blob = bytearray(original)
            struct.pack_into('<I', blob, offset, value)
            bad.append(blob)
        for offset, value in ((12, float('nan')), (16, 33.), (28, float('inf')), (32, 33.)):
            blob = bytearray(original)
            struct.pack_into('<f', blob, offset, value)
            bad.append(blob)
        for blob in bad:
            with self.assertRaises(ValueError):
                LeftRoleResidualForest.decode(blob)


if __name__ == '__main__':
    unittest.main()
