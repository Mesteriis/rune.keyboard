#!/usr/bin/env python3
"""Pure validation for bounded MLX training segments."""
from __future__ import annotations


def plan(total_iterations: int, completed_iterations: int,
         requested_segment_iterations: int | None,
         gradient_accumulation_steps: int) -> dict[str, int]:
    if total_iterations <= 0 or gradient_accumulation_steps <= 0:
        raise ValueError("training limits must be positive")
    if completed_iterations < 0 or completed_iterations >= total_iterations:
        raise ValueError("completed iterations are outside the training plan")
    remaining = total_iterations - completed_iterations
    requested = remaining if requested_segment_iterations is None else requested_segment_iterations
    if requested <= 0:
        raise ValueError("segment iterations must be positive")
    segment = min(requested, remaining)
    if (completed_iterations % gradient_accumulation_steps != 0
            or segment % gradient_accumulation_steps != 0):
        raise ValueError("training segment must preserve gradient accumulation boundaries")
    return {
        "completedBefore": completed_iterations,
        "segmentIterations": segment,
        "completedAfter": completed_iterations + segment,
        "remainingAfter": remaining - segment,
    }
