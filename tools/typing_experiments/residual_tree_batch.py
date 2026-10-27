"""Training-only vectorized evaluation of an already validated numeric forest.

NumPy belongs to the existing training runtime. Scalar model parsing and scoring
remain usable without it. Accumulate in tree order at float64 precision while
comparing float32 inputs to exported float32 borders.
"""
import numpy as np

from right_context_residual_ranker import NumericForest


def forest_scores(forest, matrix):
    if not isinstance(forest, NumericForest):
        raise ValueError('RESIDUAL_BATCH_MODEL')
    values = np.asarray(matrix)
    if (values.ndim != 2 or values.shape[1] != forest.feature_count
            or values.dtype.kind not in 'biuf' or not np.isfinite(values).all()):
        raise ValueError('RESIDUAL_BATCH_FEATURES')
    with np.errstate(over='ignore'):
        inputs = values.astype(np.float32, copy=False)
    result = np.zeros(len(inputs), dtype=np.float64)
    for tree in forest.trees:
        leaves = np.zeros(len(inputs), dtype=np.uint8)
        for depth, (index, border) in enumerate(tree.splits):
            leaves |= (inputs[:, index] > border).astype(np.uint8) << depth
        result += np.asarray(tree.leaves, dtype=np.float64)[leaves]
    return result * forest.scale + forest.bias
