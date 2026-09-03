"""Pure deterministic sampling used by host model validation."""
from __future__ import annotations

import random


def balanced_indices(languages: list[str], limit: int | None, seed: int = 0) -> list[int]:
    buckets = {language: [] for language in sorted(set(languages))}
    for index, language in enumerate(languages):
        buckets[language].append(index)
    rng = random.Random(seed)
    for values in buckets.values():
        rng.shuffle(values)
    selected = []
    while any(buckets.values()) and (limit is None or len(selected) < limit):
        for language in buckets:
            if buckets[language] and (limit is None or len(selected) < limit):
                selected.append(buckets[language].pop())
    return selected
