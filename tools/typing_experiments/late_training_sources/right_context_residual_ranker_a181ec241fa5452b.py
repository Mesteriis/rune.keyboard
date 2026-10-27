"""Numeric-only residual experiment: frozen v6 scores plus a structural head.

The correction sees fields 146..201 only (56 fields), not lexical/frequency
inputs or labels. No source admission, model registration or editor authority.
"""
from dataclasses import dataclass
import math
from numbers import Real
import struct

BASE_FEATURES = 178
FULL_FEATURES = 202
STRUCTURAL_START = 146
RESIDUAL_FEATURES = FULL_FEATURES - STRUCTURAL_START


def _vector(features, count):
    values = tuple(features)
    if len(values) != count or any(not isinstance(v, Real) or not math.isfinite(v) for v in values):
        raise ValueError('RESIDUAL_FEATURE_SCHEMA')
    return values


def _float32(value):
    try:
        return struct.unpack('<f', struct.pack('<f', value))[0]
    except OverflowError:
        # Match Kotlin Double.toFloat / NumPy float32 for finite large inputs.
        return math.copysign(math.inf, value)


@dataclass(frozen=True)
class NumericTree:
    splits: tuple[tuple[int, float], ...]
    leaves: tuple[float, ...]


@dataclass(frozen=True)
class NumericForest:
    feature_count: int
    scale: float
    bias: float
    trees: tuple[NumericTree, ...]

    @classmethod
    def decode(cls, blob, expected_features):
        if (expected_features not in {BASE_FEATURES, RESIDUAL_FEATURES}
                or not isinstance(blob, (bytes, bytearray)) or not 20 <= len(blob) <= 65536):
            raise ValueError('RESIDUAL_FOREST_MODEL')

        def valid(value):
            return math.isfinite(value) and abs(value) <= 32

        try:
            magic, features, count, scale, bias = struct.unpack_from('<4sIIff', blob)
            if (magic != b'RET2' or features != expected_features or not 1 <= count <= 128
                    or not valid(scale) or not valid(bias)):
                raise ValueError('RESIDUAL_FOREST_MODEL')
            offset = 20
            trees = []
            for _ in range(count):
                depth, = struct.unpack_from('<I', blob, offset)
                offset += 4
                if not 1 <= depth <= 6:
                    raise ValueError('RESIDUAL_FOREST_MODEL')
                splits = []
                for _ in range(depth):
                    index, border = struct.unpack_from('<If', blob, offset)
                    offset += 8
                    if not 0 <= index < features or not valid(border):
                        raise ValueError('RESIDUAL_FOREST_MODEL')
                    splits.append((index, border))
                leaves = struct.unpack_from('<' + 'f' * (1 << depth), blob, offset)
                offset += 4 * (1 << depth)
                if not all(valid(value) for value in leaves):
                    raise ValueError('RESIDUAL_FOREST_MODEL')
                trees.append(NumericTree(tuple(splits), leaves))
            if offset != len(blob):
                raise ValueError('RESIDUAL_FOREST_MODEL')
            return cls(features, scale, bias, tuple(trees))
        except struct.error as error:
            raise ValueError('RESIDUAL_FOREST_MODEL') from error

    def score(self, features):
        values = _vector(features, self.feature_count)
        result = 0.0
        for tree in self.trees:
            leaf = 0
            for depth, (index, border) in enumerate(tree.splits):
                if _float32(values[index]) > border:
                    leaf |= 1 << depth
            result += tree.leaves[leaf]
        return result * self.scale + self.bias


def structural_features(full):
    return _vector(full, FULL_FEATURES)[STRUCTURAL_START:]


class ResidualRightContextRanker:
    def __init__(self, base_bytes, residual_bytes):
        self.base = NumericForest.decode(base_bytes, BASE_FEATURES)
        self.residual = NumericForest.decode(residual_bytes, RESIDUAL_FEATURES)

    def raw_score(self, full):
        values = _vector(full, FULL_FEATURES)
        return self.base.score(values[:BASE_FEATURES]) + self.residual.score(values[STRUCTURAL_START:])

    def score(self, full):
        return .8 * math.tanh(self.raw_score(full) / 4)
