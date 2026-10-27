"""Offline capped target-POS frequency ablation, not a contextual POS parser.

All possible dictionary parts form one signature: mixed readings are never
collapsed to a preferred role. Fit only on authored training groups. Normalize
the capped inverse-square-root factors to preserve total strong weight mass;
unresolved and protected-original groups retain the frozen weight of one.
"""
from collections import Counter
from dataclasses import dataclass
import math

from right_context_training_weights import strong_supervision_weight

VERSION = 1
MAX_FACTOR = 8.


def target_signature(word, lexicon):
    parts = {a.pos for a in lexicon.analyses(word)}
    if (not parts or any(not isinstance(part, str) or not 1 <= len(part) <= 16
                         or not part.isascii() or not part.isalpha() or not part.isupper()
                         for part in parts)):
        raise ValueError('TARGET_SIGNATURE_DICTIONARY')
    return tuple(sorted(parts))


@dataclass(frozen=True)
class TargetSignatureWeights:
    entries: tuple
    normalization: float

    @classmethod
    def fit(cls, rows, lexicon):
        counts = Counter()
        for row in rows:
            strong_supervision_weight(row)  # Reject non-training/malformed labels.
            if row['kind'] == 'unknown_original':
                counts[target_signature(row['expectedApplied'], lexicon)] += 1
        if not counts:
            raise ValueError('TARGET_SIGNATURE_NO_STRONG_GROUPS')
        largest = max(counts.values())
        entries = tuple((signature, count, min(MAX_FACTOR, math.sqrt(largest / count)))
                        for signature, count in sorted(counts.items()))
        normalization = math.fsum(count * factor for _, count, factor in entries) / sum(counts.values())
        return cls(entries, normalization)

    def weight(self, row, lexicon):
        base = strong_supervision_weight(row)
        if row['kind'] != 'unknown_original':
            return base
        signature = target_signature(row['expectedApplied'], lexicon)
        factors = {key: factor for key, _, factor in self.entries}
        if signature not in factors:
            raise ValueError('TARGET_SIGNATURE_NOT_FITTED')
        return base * factors[signature] / self.normalization
