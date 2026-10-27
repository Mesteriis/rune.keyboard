import random
import struct
import unittest
import numpy as np

from residual_tree_batch import forest_scores
from right_context_residual_ranker import NumericForest
from test_right_context_residual_ranker import model


class BatchTreeTest(unittest.TestCase):
    def test_batch_matches_scalar_tree_order_and_float32_borders_exactly(self):
        forest = NumericForest.decode(model(scale=.7, bias=.3), 178)
        rng = random.Random(27102026)
        matrix = np.asarray([[rng.uniform(-2, 2) for _ in range(178)] for _ in range(512)], dtype=np.float64)
        matrix[:5, 0] = [.5, .5 + 1e-12, np.nextafter(np.float32(.5), np.float32(1)), 1e300, -1e300]
        actual = forest_scores(forest, matrix)
        self.assertEqual([forest.score(row) for row in matrix], list(actual))

    def test_residual_profile_and_empty_batch_are_supported(self):
        forest = NumericForest.decode(model(56), 56)
        self.assertEqual([], list(forest_scores(forest, np.zeros((0, 56)))))
        self.assertEqual([-1., 2.], list(forest_scores(forest, np.asarray([[0.] * 56, [1.] * 56]))))

    def test_malformed_batches_do_not_cast_invalid_data_into_evidence(self):
        forest = NumericForest.decode(model(), 178)
        for matrix in (np.zeros(178), np.zeros((1, 177)), np.zeros((1, 1, 178)),
                       np.full((1, 178), float('nan')), np.full((1, 178), float('inf')),
                       np.full((1, 178), '0'), np.zeros((1, 178), dtype=complex)):
            with self.assertRaises(ValueError):
                forest_scores(forest, matrix)
        with self.assertRaises(ValueError):
            forest_scores(None, np.zeros((1, 178)))

    def test_all_six_leaf_bits_and_multiple_trees_match_independent_legacy_scorer(self):
        from rank_refinement import tree_score
        rng = random.Random(27062026)
        blob = bytearray(struct.pack('<4sIIff', b'RET2', 178, 12, .7, .3))
        for tree in range(12):
            depth = tree % 6 + 1
            blob.extend(struct.pack('<I', depth))
            for _ in range(depth):
                blob.extend(struct.pack('<If', rng.randrange(178), rng.uniform(-1, 1)))
            blob.extend(struct.pack('<' + 'f' * (1 << depth), *[rng.uniform(-2, 2) for _ in range(1 << depth)]))
        forest = NumericForest.decode(bytes(blob), 178)
        matrix = np.asarray([[rng.uniform(-2, 2) for _ in range(178)] for _ in range(256)])
        actual = list(forest_scores(forest, matrix))
        self.assertEqual([tree_score(blob, row) for row in matrix], actual)
        self.assertEqual([forest.score(row) for row in matrix], actual)

    def test_float64_accumulation_keeps_original_tree_order(self):
        blob = bytearray(struct.pack('<4sIIff', b'RET2', 178, 3, 1., 0.))
        for value in (32., 1e-30, -32.):
            blob.extend(struct.pack('<IIf', 1, 0, .5))
            blob.extend(struct.pack('<ff', value, value))
        forest = NumericForest.decode(bytes(blob), 178)
        self.assertEqual([0., 0.], list(forest_scores(forest, np.zeros((2, 178)))))


if __name__ == '__main__':
    unittest.main()
