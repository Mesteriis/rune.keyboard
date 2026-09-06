#!/usr/bin/env python3
"""Replay archived calibration to diagnose punctuation length bias; never qualify a policy."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path


HERE = Path(__file__).resolve().parent
ARCHIVE = HERE / "results/2026-09-03-contextual-quality"
INPUTS = {
    "rows.jsonl.gz": "a7fd0d36e302d66d2e5066b7f281fa9321cad856b44602541c16fc877c1d8592",
    "calibration-scores.jsonl.gz": "149082bb78597b69869e50e0aed49a3c578463ba75cab4d57df555b886c597fa",
    "calibration-complete.json": "13cc02d6613290979ebe81a61e7878add4115e898906be505b33df9d61088722",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_calibration() -> tuple[list[dict], dict]:
    for name, expected in INPUTS.items():
        if sha(ARCHIVE / name) != expected:
            raise ValueError("ARCHIVED_CALIBRATION_IDENTITY")
    with gzip.open(ARCHIVE / "rows.jsonl.gz", "rt") as stream:
        # The old export includes both splits. Held-out rows never reach decisions or metrics.
        rows = [row for line in stream if (row := json.loads(line))["split"] == "calibration"]
    with gzip.open(ARCHIVE / "calibration-scores.jsonl.gz", "rt") as stream:
        cache = [json.loads(line) for line in stream]
    complete = json.loads((ARCHIVE / "calibration-complete.json").read_text())
    if (complete["scope"] != "contextual-calibration-scores" or complete["scores"] != 600
            or cache[0]["cacheIdentity"] != complete["identity"]):
        raise ValueError("CALIBRATION_RECEIPT")
    decoded = gzip.decompress((ARCHIVE / "calibration-scores.jsonl.gz").read_bytes())
    if hashlib.sha256(decoded).hexdigest() != complete["scoresSha256"]:
        raise ValueError("CALIBRATION_SCORE_DIGEST")
    scores = {row["id"]: row for row in cache[1:]}
    if len(rows) != 600 or len(scores) != 600 or set(scores) != {row["id"] for row in rows}:
        raise ValueError("CALIBRATION_ROWS")
    for row in rows:
        values = scores[row["id"]]["scores"]
        if (set(value["id"] for value in values) != set(range(7)) or len(values) != 7
                or any(not math.isfinite(value["sumLogProbability"])
                       or value["sumLogProbability"] > 0
                       or not 1 <= value["scoredTokenCount"] <= 255 for value in values)):
            raise ValueError("BOUNDED_NUMERIC_SCORES")
    return rows, scores


def choose(scores: list[dict], *, average: bool, original_margin: float, rival_margin: float) -> int:
    values = {value["id"]: value["sumLogProbability"] /
              (value["scoredTokenCount"] if average else 1) for value in scores}
    winner = max(range(1, 7), key=lambda identifier: (values[identifier], -identifier))
    rival = max(values[identifier] for identifier in range(1, 7) if identifier != winner)
    if values[winner] - values[0] <= original_margin or values[winner] - rival < rival_margin:
        return 0
    return winner


def report() -> dict:
    rows, scores = load_calibration()
    # These are development diagnostics, including a margin suggested by a calibration-only
    # exploratory grid. They are not precommitted release thresholds or an acceptance test.
    policies = {
        "current_average": dict(average=True, original_margin=0.0, rival_margin=0.0),
        "total_only": dict(average=False, original_margin=0.0, rival_margin=0.0),
        "total_with_two_margins": dict(average=False, original_margin=0.5, rival_margin=4.0),
    }
    results = {}
    for name, policy in policies.items():
        languages = {}
        for language in ("en", "ru", "es"):
            selected = [row for row in rows if row["language"] == language]
            clear = [row for row in selected if not row["ambiguous"]]
            ambiguous = [row for row in selected if row["ambiguous"]]
            decisions = {row["id"]: choose(scores[row["id"]]["scores"], **policy) for row in selected}
            suggested = [row for row in clear if decisions[row["id"]] != 0]
            languages[language] = {
                "clearRows": len(clear), "ambiguousRows": len(ambiguous),
                "clearSuggestions": len(suggested),
                "correctClearSuggestions": sum(decisions[row["id"]] == row["expectedCandidate"]
                                               for row in suggested),
                "ambiguousNonSpaceSuggestions": sum(decisions[row["id"]] != 0 for row in ambiguous),
            }
        results[name] = {"parameters": policy, "languages": languages}
    return {
        "scope": "contextual-calibration-development-diagnostic",
        "inputs": INPUTS, "scriptSha256": sha(Path(__file__)), "rows": len(rows),
        "holdoutDecisions": 0, "productionChanged": False, "releaseQualified": False,
        "independentObservations": False,
        "note": "Repeated authored contexts; calibration comparisons cannot establish unseen quality.",
        "policies": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(report(), indent=2, sort_keys=True, allow_nan=False))
