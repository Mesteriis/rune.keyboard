#!/usr/bin/env python3
"""Freeze a stricter margin after a disclosed holdout rejects a candidate."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import abstaining_ranker as base  # noqa: E402
import augmented_abstaining_ranker as augmented  # noqa: E402


def select_margin(record_sets: list[list[dict]], minimum_score: float,
                  current_margin: float, minimum_additions: int) -> tuple[float, list[dict]]:
    bad_margins = [record["margin"] for records in record_sets for record in records
        if record["topScore"] >= minimum_score and record["margin"] >= current_margin and
        (not record["correct"] or record["control"])]
    margin = math.nextafter(max(bad_margins), math.inf) if bad_margins else current_margin
    metrics = [base.gate.threshold_metrics(records, minimum_score, margin)
               for records in record_sets]
    for result in metrics:
        if (result["additions"] < minimum_additions or result["incorrectAdditions"] != 0 or
                result["controlChanges"] != 0):
            raise ValueError("NO_SAFE_MARGIN_WITH_REQUIRED_COVERAGE")
    return margin, metrics


def parse_evidence(value: str) -> tuple[Path, Path, str]:
    fields = value.split("::")
    if len(fields) != 3 or fields[2] not in {"calibration", "holdout"}:
        raise argparse.ArgumentTypeError("evidence must be ROWS::OBSERVATIONS::SPLIT")
    return Path(fields[0]).resolve(strict=True), Path(fields[1]).resolve(strict=True), fields[2]


def refreeze(policy_path: Path, evidence: list[tuple[Path, Path, str]], output: Path) -> dict:
    policy_path = policy_path.resolve(strict=True)
    output = output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / "build"):
        raise ValueError("FRESH_BUILD_OUTPUT_REQUIRED")
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    model_path, context_model = base.verify_policy(policy)
    retrieval = policy.get("candidateRetrieval", {})
    supplement_path = (ROOT / retrieval["supplement"]).resolve(strict=True)
    morphology_path = (ROOT / retrieval["morphology"]).resolve(strict=True)
    supplement, ranks = augmented.rare.read_supplement(supplement_path)
    record_sets = []
    labels = []
    with augmented.DictionaryIndex(morphology_path) as morphology:
        augmenter = augmented.Augmenter(morphology, supplement, ranks)
        augmented.install_group_hooks(augmenter)
        for rows, observations, split in evidence:
            groups = augmented.augmented_product_groups(rows, observations, split, augmenter)
            record_sets.append(base.threshold_records(model_path, groups, context_model))
            labels.append({"rows": str(rows.relative_to(ROOT)),
                           "observations": str(observations.relative_to(ROOT)),
                           "split": split, "records": len(groups)})
    margin, metrics = select_margin(record_sets, policy["minimumScore"],
                                    policy["minimumMargin"], policy["minimumAdditions"])
    inputs = [policy_path, Path(__file__), *(path for item in evidence for path in item[:2])]
    refined = dict(policy)
    refined["minimumMargin"] = margin
    refined["bindings"] = dict(policy["bindings"])
    refined["bindings"].update({str(path.relative_to(ROOT)): base.sha256(path) for path in inputs})
    refined["refinement"] = {
        "kind": "disclosed-evidence-zero-regression-margin",
        "basePolicy": str(policy_path.relative_to(ROOT)),
        "basePolicySha256": base.sha256(policy_path),
        "priorMinimumMargin": policy["minimumMargin"],
        "evidence": [{**label, "metrics": {key: value for key, value in result.items()
                                             if key != "selectedIds"}}
                     for label, result in zip(labels, metrics, strict=True)],
        "futureUnseenHoldoutRequired": True,
    }
    output.mkdir(parents=True)
    base.write_json(output / "frozen-policy.json", refined)
    return refined


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--evidence", type=parse_evidence, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    policy = refreeze(args.policy, args.evidence, args.output)
    print(json.dumps({"minimumScore": policy["minimumScore"],
                      "minimumMargin": policy["minimumMargin"],
                      "policySha256": base.sha256(Path(args.output) / "frozen-policy.json")},
                     sort_keys=True))


if __name__ == "__main__":
    main()
