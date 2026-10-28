#!/usr/bin/env python3
"""Calibrate then evaluate the shipped compact scorer as an additive RU auto policy.

Calibration and holdout are deliberately separate commands.  A frozen policy must exist before
the holdout command can read its observations.  Promotion is fail-closed: correct replacements
must increase while incorrect and control changes may not increase at all.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import unicodedata


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
ASSETS = REPO / "app/src/main/assets/smarttyping/experiments"
SCHEMA = 1
MINIMUM_ADDITIONS = 100


def normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_json(path: Path, value: dict) -> None:
    if path.exists():
        raise ValueError("FRESH_OUTPUT_REQUIRED")
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
        allow_nan=False) + "\n")


def automatic_metrics(changes: int, correct: int, control_changes: int) -> dict:
    if not (0 <= correct <= changes and 0 <= control_changes <= changes):
        raise ValueError("INVALID_AUTOMATIC_METRICS")
    return {
        "changes": changes,
        "correct": correct,
        "incorrect": changes - correct,
        "controlChanges": control_changes,
        "precision": correct / changes if changes else None,
    }


def structurally_eligible(pool_size: int, full_completion: str) -> bool:
    """A singleton is confidence evidence only when the wider search also completed."""
    return pool_size >= 2 or full_completion == "COMPLETE"


def promotion_decision(active: dict, proposed: dict, additions: int,
        minimum_additions: int = MINIMUM_ADDITIONS) -> dict:
    refusals = []
    if additions < minimum_additions:
        refusals.append("INSUFFICIENT_ADDITIONS")
    if proposed["correct"] <= active["correct"]:
        refusals.append("CORRECT_CHANGES_NOT_IMPROVED")
    if proposed["incorrect"] > active["incorrect"]:
        refusals.append("INCORRECT_CHANGES_INCREASED")
    if proposed["controlChanges"] > active["controlChanges"]:
        refusals.append("CONTROL_CHANGES_INCREASED")
    active_precision = active["precision"] if active["precision"] is not None else 1.0
    proposed_precision = proposed["precision"] if proposed["precision"] is not None else 1.0
    if proposed_precision < active_precision:
        refusals.append("PRECISION_DECREASED")
    approved = not refusals
    return {"promotionApproved": approved, "rollbackRequired": not approved,
        "refusals": refusals}


def threshold_metrics(records: list[dict], minimum_score: float,
        minimum_margin: float) -> dict:
    selected = [record for record in records
        if record["topScore"] >= minimum_score and record["margin"] >= minimum_margin]
    correct = [record for record in selected if record["correct"]]
    return {
        "additions": len(selected),
        "correctAdditions": len(correct),
        "incorrectAdditions": len(selected) - len(correct),
        "controlChanges": sum(record["control"] for record in selected),
        "distinctCorrectFamilies": len({record["family"] for record in correct}),
        "selectedIds": [record["id"] for record in selected],
    }


def calibrate(records: list[dict], minimum_additions: int = MINIMUM_ADDITIONS,
        require_strict_admission: bool = False) -> tuple[dict, dict]:
    if not records:
        raise ValueError("NO_CALIBRATION_RECORDS")
    scores = sorted({record["topScore"] for record in records})
    margins = [float("-inf"), *sorted({record["margin"] for record in records
        if math.isfinite(record["margin"])})]
    best = None
    for minimum_score in scores:
        for minimum_margin in margins:
            metrics = threshold_metrics(records, minimum_score, minimum_margin)
            if (metrics["additions"] < minimum_additions or
                metrics["incorrectAdditions"] != 0 or metrics["controlChanges"] != 0):
                continue
            key = (metrics["correctAdditions"], minimum_margin, minimum_score)
            if best is None or key > best[0]:
                best = (key, minimum_score, minimum_margin, metrics)
    if best is None:
        raise ValueError("NO_ZERO_REGRESSION_POLICY")
    _, minimum_score, minimum_margin, metrics = best
    policy = {
        "schemaVersion": SCHEMA,
        "language": "ru",
        "score": "combinedScore",
        "admission": "complete-local-source-morphology-absent-with-competing-or-full-completion" +
            ("-and-strict-admission" if require_strict_admission else ""),
        "requireStrictAdmission": require_strict_admission,
        "minimumScore": minimum_score,
        "minimumMargin": minimum_margin,
        "minimumAdditions": minimum_additions,
        "zeroNewIncorrectRequired": True,
        "zeroNewControlChangesRequired": True,
    }
    return policy, metrics


def _row_map(rows: list[dict], observations: list[dict], split: str) -> list[tuple[dict, dict]]:
    selected = [row for row in rows if row["split"] == split]
    if ([row["id"] for row in selected] != [item.get("id") for item in observations] or
        any(item.get("split") != split or item.get("status") != "COMPLETE" for item in observations)):
        raise ValueError("OBSERVATION_IDENTITY")
    return list(zip(selected, observations, strict=True))


def compact_records(rows: list[dict], observations: list[dict], split: str,
        require_strict_admission: bool = False) -> list[dict]:
    records = []
    for row, observation in _row_map(rows, observations, split):
        if row["language"] != "ru":
            continue
        scores = observation.get("compactScores")
        if not isinstance(scores, list):
            raise ValueError("COMPACT_SCORES_MISSING")
        if not scores:
            continue
        if observation.get("localDecision") is not None:
            raise ValueError("COMPACT_OVERLAPS_ACTIVE_POLICY")
        source = observation.get("compactSourceMorphology")
        if not isinstance(source, dict) or source.get("available") is not True:
            raise ValueError("SOURCE_MORPHOLOGY_UNAVAILABLE")
        if source.get("present") is True:
            continue
        full_completion = observation.get("fullTokenGeneration", {}).get("completion")
        if not structurally_eligible(len(scores), full_completion):
            continue
        if any(not math.isfinite(item.get("combinedScore", math.nan)) for item in scores):
            raise ValueError("NONFINITE_COMPACT_SCORE")
        order = sorted(range(len(scores)), key=lambda index: (-scores[index]["combinedScore"], index))
        top = scores[order[0]]
        if require_strict_admission and top.get("strictAdmissionAllowed") is not True:
            continue
        second = scores[order[1]]["combinedScore"] if len(order) > 1 else float("-inf")
        expected = normalize(row.get("expectedSpelling", row["typed"]))
        correct = (row["cohort"] == "typo" and not row["noAuto"] and
            normalize(top["canonicalKey"]) == expected)
        records.append({
            "id": row["id"], "family": row["family"], "cohort": row["cohort"],
            "topScore": top["combinedScore"], "margin": top["combinedScore"] - second,
            "candidate": top["canonicalKey"], "correct": correct,
            "control": row["cohort"] in {"correct", "protected"},
        })
    return records


def active_metrics(rows: list[dict], observations: list[dict], split: str) -> dict:
    changes = correct = controls = 0
    for row, observation in _row_map(rows, observations, split):
        if row["language"] != "ru" or observation.get("localDecision") is None:
            continue
        correction = (observation.get("autoEdit") or {}).get("correctionGeneration")
        if correction is None:
            continue
        changes += 1
        expected = normalize(row.get("expectedSpelling", row["typed"]))
        is_correct = (row["cohort"] == "typo" and not row["noAuto"] and
            normalize(observation["localDecision"]) == expected)
        correct += int(is_correct)
        controls += int(row["cohort"] in {"correct", "protected"})
    return automatic_metrics(changes, correct, controls)


def combined_metrics(active: dict, additions: dict) -> dict:
    return automatic_metrics(active["changes"] + additions["additions"],
        active["correct"] + additions["correctAdditions"],
        active["controlChanges"] + additions["controlChanges"])


def bindings(rows_path: Path, observations_path: Path) -> dict:
    paths = [rows_path, observations_path, Path(__file__), ASSETS / "ru-ranker.bin",
        ASSETS / "ru-ranking-context.bin"]
    return {str(path.resolve().relative_to(REPO)): sha256(path) for path in paths}


def calibration_command(args: argparse.Namespace) -> None:
    rows_path = Path(args.rows).resolve(strict=True)
    observations_path = Path(args.observations).resolve(strict=True)
    rows = read_jsonl(rows_path)
    observations = read_jsonl(observations_path)
    records = compact_records(rows, observations, "calibration", args.require_strict_admission)
    policy, metrics = calibrate(records, args.minimum_additions, args.require_strict_admission)
    active = active_metrics(rows, observations, "calibration")
    proposed = combined_metrics(active, metrics)
    decision = promotion_decision(active, proposed, metrics["additions"], args.minimum_additions)
    if not decision["promotionApproved"]:
        raise ValueError("CALIBRATION_PROMOTION_REFUSED")
    write_json(Path(args.output), {**policy, "stage": "frozen-before-holdout",
        "bindings": bindings(rows_path, observations_path), "calibration": {
            "records": len(records), "additions": {key: value for key, value in metrics.items()
                if key != "selectedIds"}, "active": active, "proposed": proposed,
            "decision": decision}})


def evaluation_command(args: argparse.Namespace) -> None:
    rows_path = Path(args.rows).resolve(strict=True)
    observations_path = Path(args.observations).resolve(strict=True)
    policy_path = Path(args.policy).resolve(strict=True)
    policy = json.loads(policy_path.read_text())
    if (policy.get("schemaVersion") != SCHEMA or policy.get("stage") != "frozen-before-holdout" or
        policy.get("score") != "combinedScore"):
        raise ValueError("INVALID_FROZEN_POLICY")
    frozen_paths = [Path(__file__), ASSETS / "ru-ranker.bin",
        ASSETS / "ru-ranking-context.bin"]
    for path in frozen_paths:
        key = str(path.resolve().relative_to(REPO))
        if policy["bindings"].get(key) != sha256(path):
            raise ValueError(f"FROZEN_INPUT_DRIFT:{key}")
    if sha256(observations_path) in policy["bindings"].values():
        raise ValueError("HOLDOUT_REUSES_CALIBRATION_OBSERVATIONS")
    rows = read_jsonl(rows_path)
    observations = read_jsonl(observations_path)
    require_strict_admission = policy.get("requireStrictAdmission")
    if not isinstance(require_strict_admission, bool):
        raise ValueError("INVALID_FROZEN_POLICY")
    records = compact_records(rows, observations, "holdout", require_strict_admission)
    additions = threshold_metrics(records, policy["minimumScore"], policy["minimumMargin"])
    active = active_metrics(rows, observations, "holdout")
    proposed = combined_metrics(active, additions)
    decision = promotion_decision(active, proposed, additions["additions"],
        policy["minimumAdditions"])
    report = {"schemaVersion": SCHEMA, "stage": "holdout-promotion-decision",
        "policySha256": sha256(policy_path), "bindings": bindings(rows_path, observations_path),
        "holdout": {"records": len(records), "additions": {key: value
            for key, value in additions.items() if key != "selectedIds"}, "active": active,
            "proposed": proposed, "decision": decision}}
    write_json(Path(args.output), report)
    if not decision["promotionApproved"]:
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    calibration = commands.add_parser("calibrate")
    calibration.add_argument("--rows", required=True)
    calibration.add_argument("--observations", required=True)
    calibration.add_argument("--output", required=True)
    calibration.add_argument("--minimum-additions", type=int, default=MINIMUM_ADDITIONS)
    calibration.add_argument("--require-strict-admission", action="store_true")
    calibration.set_defaults(run=calibration_command)
    evaluation = commands.add_parser("evaluate")
    evaluation.add_argument("--rows", required=True)
    evaluation.add_argument("--observations", required=True)
    evaluation.add_argument("--policy", required=True)
    evaluation.add_argument("--output", required=True)
    evaluation.set_defaults(run=evaluation_command)
    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
