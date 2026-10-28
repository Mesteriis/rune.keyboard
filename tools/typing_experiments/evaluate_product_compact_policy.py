#!/usr/bin/env python3
"""Verify Kotlin product replay preserves baseline and applies only qualified additions."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GATE_PATH = ROOT / "tools/eval/smart-typing-0.3/pipeline/evaluate_compact_autocorrection.py"
SPEC = importlib.util.spec_from_file_location("product_compact_gate", GATE_PATH)
gate = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(gate)


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def compact_selection(observation: dict) -> str | None:
    if observation.get("localDecision") is not None or observation.get("automaticAdmissionAllowed") is not True:
        return None
    generation = observation.get("fullTokenGeneration") or {}
    candidates = generation.get("compactAlternatives") or []
    candidate = observation.get("automaticAdmissionCandidate")
    if not isinstance(candidate, str) or not any(item.get("terminalKey") == candidate for item in candidates):
        return None
    view = observation.get("candidateView") or {}
    selected = next((item for item in view.get("candidates", [])
                     if item.get("id") == view.get("selectedCandidateId")), None)
    if selected is None or selected.get("role") != "CORRECTION" or selected.get("text", "").casefold() != candidate.casefold():
        return None
    edit = observation.get("autoEdit") or {}
    return candidate if edit.get("correctionGeneration") is not None else None


def compact_proposal(observation: dict) -> str | None:
    """Read a frozen compact proposal while release qualification intentionally blocks mutation."""
    if observation.get("localDecision") is not None:
        return None
    candidate = observation.get("compactPolicyCandidate")
    generation = observation.get("fullTokenGeneration") or {}
    alternatives = generation.get("compactAlternatives") or []
    if not isinstance(candidate, str) or not any(item.get("terminalKey") == candidate for item in alternatives):
        return None
    view = observation.get("candidateView") or {}
    selected = next((item for item in view.get("candidates", [])
                     if item.get("id") == view.get("selectedCandidateId")), None)
    return candidate if (selected is not None and selected.get("role") == "CORRECTION" and
                         selected.get("text", "").casefold() == candidate.casefold()) else None


def nearest_rank(values: list[int], percentile: float) -> int:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(percentile * len(ordered)) - 1)]


def generation_latency(product: list[dict]) -> dict:
    def summarize(observations: list[dict]) -> dict:
        if not observations:
            return {"rows": 0, "p50Nanos": None, "p95Nanos": None, "maxNanos": None}
        timings = [item.get("fullTokenGenerationNanos") for item in observations]
        if any(not isinstance(value, int) or value < 0 for value in timings):
            raise ValueError("MISSING_GENERATION_TIMING")
        return {"rows": len(timings), "p50Nanos": nearest_rank(timings, 0.50),
                "p95Nanos": nearest_rank(timings, 0.95), "maxNanos": max(timings)}

    compact_pool = [item for item in product
                    if (item.get("fullTokenGeneration") or {}).get("compactAlternatives")]
    compact_selected = [item for item in product if item.get("compactPolicyCandidate") is not None]
    return {"all": summarize(product), "compactPool": summarize(compact_pool),
            "compactSelected": summarize(compact_selected)}


def evaluate_legacy_preservation(rows: list[dict], legacy: list[dict], product: list[dict],
                                 minimum_new_correct: int) -> dict:
    ids = [row["id"] for row in rows]
    if ([item.get("id") for item in legacy] != ids or [item.get("id") for item in product] != ids or
            any(item.get("status") != "COMPLETE" for item in legacy + product)):
        raise ValueError("LEGACY_OBSERVATION_IDENTITY")
    legacy_selected = {item["id"]: selected for item in legacy
                       if (selected := compact_selection(item)) is not None}
    product_selected = {item["id"]: selected for item in product
                        if (selected := compact_selection(item)) is not None}
    changed = [{"id": identifier, "legacy": selected, "product": product_selected.get(identifier)}
               for identifier, selected in legacy_selected.items()
               if product_selected.get(identifier) != selected]
    rows_by_id = {row["id"]: row for row in rows}
    additions = []
    for identifier, selected in product_selected.items():
        if identifier in legacy_selected:
            continue
        row = rows_by_id[identifier]
        expected = row.get("expectedSpelling", row["typed"]).casefold()
        correct = row["cohort"] == "typo" and not row["noAuto"] and selected.casefold() == expected
        additions.append({"id": identifier, "selected": selected, "correct": correct,
                          "control": row["cohort"] in {"correct", "protected"}})
    correct = sum(item["correct"] for item in additions)
    incorrect = sum(not item["correct"] for item in additions)
    controls = sum(item["control"] for item in additions)
    approved = not changed and correct >= minimum_new_correct and incorrect == 0 and controls == 0
    return {"legacySelections": len(legacy_selected), "productSelections": len(product_selected),
            "changedLegacySelections": changed, "newSelections": len(additions),
            "correctNewSelections": correct, "incorrectNewSelections": incorrect,
            "newControlChanges": controls, "promotionApproved": approved,
            "rollbackRequired": not approved}


def evaluate(rows: list[dict], baseline: list[dict], product: list[dict], minimum_additions: int,
             selector=compact_selection) -> dict:
    ids = [row["id"] for row in rows]
    if ([item.get("id") for item in baseline] != ids or [item.get("id") for item in product] != ids or
            any(item.get("status") != "COMPLETE" for item in baseline + product)):
        raise ValueError("OBSERVATION_IDENTITY")
    if any(left.get("localDecision") != right.get("localDecision")
           for left, right in zip(baseline, product, strict=True)):
        raise ValueError("BASELINE_LOCAL_DECISION_CHANGED")
    active_before = gate.active_metrics(rows, baseline, "holdout")
    active_after = gate.active_metrics(rows, product, "holdout")
    if active_after != active_before:
        raise ValueError("BASELINE_METRICS_CHANGED")
    additions = []
    for row, observation in zip(rows, product, strict=True):
        candidate = selector(observation)
        if candidate is None:
            continue
        expected = row.get("expectedSpelling", row["typed"]).casefold()
        correct = row["cohort"] == "typo" and not row["noAuto"] and candidate.casefold() == expected
        additions.append({"id": row["id"], "family": row["family"], "correct": correct,
                          "control": row["cohort"] in {"correct", "protected"}})
    metrics = {"additions": len(additions), "correctAdditions": sum(x["correct"] for x in additions),
        "incorrectAdditions": sum(not x["correct"] for x in additions),
        "controlChanges": sum(x["control"] for x in additions),
        "distinctCorrectFamilies": len({row["family"] for row in additions if row["correct"]})}
    proposed = gate.combined_metrics(active_before, metrics)
    decision = gate.promotion_decision(active_before, proposed, metrics["additions"], minimum_additions)
    return {"baseline": active_before, "additions": metrics, "product": proposed,
            "generationLatency": generation_latency(product), "decision": decision}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--product", type=Path, required=True)
    parser.add_argument("--legacy-product", type=Path)
    parser.add_argument("--proposal-only", action="store_true",
        help="score the frozen compact proposal while release qualification blocks editor mutation")
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows_path, baseline_path, product_path, policy_path = (
        args.rows.resolve(strict=True), args.baseline.resolve(strict=True),
        args.product.resolve(strict=True), args.policy.resolve(strict=True))
    paths = [rows_path, baseline_path, product_path, policy_path]
    legacy_path = args.legacy_product.resolve(strict=True) if args.legacy_product else None
    if legacy_path is not None:
        paths.append(legacy_path)
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    minimum_additions = policy.get("minimumAdditions",
        policy.get("promotionRule", {}).get("minimumNewCorrectChanges"))
    if not isinstance(minimum_additions, int) or minimum_additions < 1:
        raise ValueError("MINIMUM_ADDITIONS")
    rows, baseline, product = (gate.read_jsonl(path)
                               for path in (rows_path, baseline_path, product_path))
    result = evaluate(rows, baseline, product, minimum_additions,
                      compact_proposal if args.proposal_only else compact_selection)
    if legacy_path is not None:
        preservation = evaluate_legacy_preservation(rows, gate.read_jsonl(legacy_path), product,
                                                    minimum_additions)
        result["legacyPreservation"] = preservation
        if not preservation["promotionApproved"]:
            result["decision"]["promotionApproved"] = False
            result["decision"]["rollbackRequired"] = True
            result["decision"]["failures"] = sorted(set(
                result["decision"].get("failures", []) + ["LEGACY_SELECTION_REGRESSION"]))
    implementation_paths = [Path(__file__).resolve(), GATE_PATH.resolve()]
    report = {"schemaVersion": 1, "stage": "kotlin-product-compact-promotion-decision",
              "bindings": {str(path.relative_to(ROOT)): sha256(path)
                           for path in paths + implementation_paths}, **result}
    gate.write_json(args.output, report)
    print(json.dumps(result, ensure_ascii=False))
    if not result["decision"]["promotionApproved"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
