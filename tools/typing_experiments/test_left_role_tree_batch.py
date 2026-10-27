import math
import random
import struct
import unittest
import numpy as np

from residual_tree_batch import forest_scores
from right_context_left_role_ranker import LeftRoleResidualForest, LeftRoleResidualRanker
from rank_refinement import tree_score
from test_right_context_residual_ranker import model


class LeftRoleBatchTest(unittest.TestCase):
    def test_96_field_reader_and_batch_match_legacy_math_for_all_leaf_bits(self):
        rng = random.Random(27102026)
        blob = bytearray(struct.pack('<4sIIff', b'RET2', 96, 6, .7, .3))
        for depth in range(1, 7):
            blob.extend(struct.pack('<I', depth))
            for _ in range(depth):
                blob.extend(struct.pack('<If', rng.randrange(96), rng.uniform(-1, 1)))
            blob.extend(struct.pack('<' + 'f' * (1 << depth), *[rng.uniform(-2, 2) for _ in range(1 << depth)]))
        forest = LeftRoleResidualForest.decode(bytes(blob))
        matrix = np.asarray([[rng.uniform(-2, 2) for _ in range(96)] for _ in range(256)])
        self.assertEqual([tree_score(blob, row) for row in matrix], list(forest_scores(forest, matrix)))
        self.assertEqual([forest.score(row) for row in matrix], list(forest_scores(forest, matrix)))

    def test_new_composition_preserves_base_and_adds_head_before_bounding(self):
        base, head = model(), model(96, index=95, leaves=(-.5, .5))
        ranker = LeftRoleResidualRanker(base, head)
        matrix = np.zeros((4, 242))
        matrix[:, 0] = [0., 1., 0., 1.]
        matrix[:, 241] = [0., 0., 1., 1.]
        scores = forest_scores(ranker.base, matrix[:, :178]) + forest_scores(ranker.residual, matrix[:, 146:])
        for row, raw in zip(matrix, scores, strict=True):
            expected = tree_score(base, row[:178]) + tree_score(head, row[146:])
            self.assertEqual(expected, raw)
            self.assertEqual(expected, ranker.raw_score(row))
            self.assertEqual(.8 * math.tanh(expected / 4), ranker.score(row))


if __name__ == '__main__':
    unittest.main()
