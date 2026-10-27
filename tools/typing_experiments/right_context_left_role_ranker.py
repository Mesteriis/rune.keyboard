"""Explicit 242/96 residual profile; the frozen 202/56 reader is unchanged.

The separate bounded reader preserves reproducible old model/source bindings.
No profile is registered with the keyboard or granted source/editor authority.
"""
import math
import struct

from right_context_residual_ranker import NumericForest, NumericTree, _vector

FULL_FEATURES = 242
BASE_FEATURES = 178
STRUCTURAL_START = 146
RESIDUAL_FEATURES = 96


class LeftRoleResidualForest(NumericForest):
    @classmethod
    def decode(cls, blob, expected_features=RESIDUAL_FEATURES):
        if (expected_features != RESIDUAL_FEATURES or not isinstance(blob, (bytes, bytearray))
                or not 20 <= len(blob) <= 65536):
            raise ValueError('LEFT_ROLE_RESIDUAL_MODEL')

        def valid(value):
            return math.isfinite(value) and abs(value) <= 32

        try:
            magic, features, count, scale, bias = struct.unpack_from('<4sIIff', blob)
            if (magic != b'RET2' or features != RESIDUAL_FEATURES or not 1 <= count <= 128
                    or not valid(scale) or not valid(bias)):
                raise ValueError('LEFT_ROLE_RESIDUAL_MODEL')
            offset = 20
            trees = []
            for _ in range(count):
                depth, = struct.unpack_from('<I', blob, offset)
                offset += 4
                if not 1 <= depth <= 6:
                    raise ValueError('LEFT_ROLE_RESIDUAL_MODEL')
                splits = []
                for _ in range(depth):
                    index, border = struct.unpack_from('<If', blob, offset)
                    offset += 8
                    if index >= RESIDUAL_FEATURES or not valid(border):
                        raise ValueError('LEFT_ROLE_RESIDUAL_MODEL')
                    splits.append((index, border))
                leaves = struct.unpack_from('<' + 'f' * (1 << depth), blob, offset)
                offset += 4 * (1 << depth)
                if not all(valid(value) for value in leaves):
                    raise ValueError('LEFT_ROLE_RESIDUAL_MODEL')
                trees.append(NumericTree(tuple(splits), leaves))
            if offset != len(blob):
                raise ValueError('LEFT_ROLE_RESIDUAL_MODEL')
            return cls(features, scale, bias, tuple(trees))
        except struct.error as error:
            raise ValueError('LEFT_ROLE_RESIDUAL_MODEL') from error


class LeftRoleResidualRanker:
    def __init__(self, base_bytes, residual_bytes):
        self.base = NumericForest.decode(base_bytes, BASE_FEATURES)
        self.residual = LeftRoleResidualForest.decode(residual_bytes)

    def raw_score(self, full):
        values = _vector(full, FULL_FEATURES)
        return self.base.score(values[:BASE_FEATURES]) + self.residual.score(values[STRUCTURAL_START:])

    def score(self, full):
        return .8 * math.tanh(self.raw_score(full) / 4)
