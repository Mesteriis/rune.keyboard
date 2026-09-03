"""Portable integer ranking features; no labels, editor access, model or persistence."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Weights:
    edit: int
    frequency: int
    repetition: int
    fallback: int
    length: int


@dataclass(frozen=True)
class Thresholds:
    original_penalty: int
    minimum_margin: int
    minimum_length: int


@dataclass(frozen=True)
class Proposal:
    candidate_id: int
    penalty: float
    runner_up_penalty: float | None
    token_length: int


def propose(generation: dict, weights: Weights) -> Proposal | None:
    """Original has a separately calibrated OOV penalty; equal alternatives always abstain."""
    if generation["prohibitsAutoReplace"] or not generation["alternatives"]:
        return None
    ranked = []
    for c in generation["alternatives"]:
        # ceil(log2(rank)), exactly portable as integer bit length (rank1 -> band0).
        frequency_band = (c["frequencyRank"] - 1).bit_length()
        quarters = c["editCost"] * 4
        if not quarters.is_integer():
            raise ValueError("NON_QUARTER_EDIT_COST")
        penalty = (int(quarters) * weights.edit + frequency_band * weights.frequency
                   - c["repeatedCharacterEdits"] * weights.repetition
                   + int(c["isFallback"]) * weights.fallback
                   + c["lengthDifference"] * weights.length)
        ranked.append((penalty, c["id"]))
    ranked.sort()
    return Proposal(ranked[0][1], ranked[0][0], ranked[1][0] if len(ranked) > 1 else None,
                    len(generation["original"]))


def choose(proposal: Proposal | None, thresholds: Thresholds | None) -> int:
    """Returns original0 or a provisional replacement ID. This is not holdout authorization."""
    if proposal is None or thresholds is None or proposal.token_length < thresholds.minimum_length:
        return 0
    if thresholds.minimum_margin <= 0:
        raise ValueError("POSITIVE_MARGIN_REQUIRED")
    rival = thresholds.original_penalty
    if proposal.runner_up_penalty is not None:
        rival = min(rival, proposal.runner_up_penalty)
    return proposal.candidate_id if rival - proposal.penalty >= thresholds.minimum_margin else 0
