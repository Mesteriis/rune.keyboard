"""Experimental revision vector: prior lexical features, completed right context,
and the observed applied-word flag. No targets, corpus IDs or future untyped text.
"""
import math
import unicodedata

VERSION = 1
BASE_FEATURES = 146
RIGHT_FEATURES = 16
FEATURES = BASE_FEATURES + RIGHT_FEATURES + 1


def _fold(word):
    return unicodedata.normalize('NFC', word).casefold()


def revision_features(base, right_features, right_context, applied, candidate):
    if len(base) != BASE_FEATURES:
        raise ValueError('REVISION_BASE_FEATURE_COUNT')
    following = right_features.extract(right_context, candidate)
    if len(following) != RIGHT_FEATURES:
        raise ValueError('REVISION_RIGHT_FEATURE_COUNT')
    values = tuple(base) + tuple(following) + (float(_fold(applied) == _fold(candidate)),)
    if not all(math.isfinite(value) for value in values):
        raise ValueError('REVISION_FEATURE_NONFINITE')
    return values
