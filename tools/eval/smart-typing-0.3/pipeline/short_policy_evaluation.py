#!/usr/bin/env python3
"""Frozen short-frequency candidate-policy experiment; never production qualification.

export -> score-calibration -> calibration-report -> freeze-policy ->
score-holdout -> replay-report. Scoring and controller admission reuse the pinned
final-product evaluator. Every request is freshly scored, with unchanged weights.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("_short_policy_base", HERE / "final_product_replay.py")
base = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(base)
EXPERIMENT = "revealed-data-short-frequency-candidate-policy-acceptance-v1"
GENERATOR = Path("app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/lexicon/CandidateGenerator.kt")
PROBE = base.REPO / "build/smart-typing-0.3/retrieval-probe-20260906/short-frequency-01"
ORIGINAL = base.REPO / GENERATOR
VARIANT = PROBE / "sources" / GENERATOR
PATCH = PROBE / "variant.patch"
PINS = {
    HERE / "final_product_replay.py": "88d72471eb76384ce7cd063e311b49d1394ea7588cace3381f58d3cc9beea745",
    ORIGINAL: "61eb889e1d327f9933e4c189227c93baf2f89b4f08bad41db538d9bfdf354370",
    VARIANT: "8799e9068983c5796518be0335bf5333e07930975aa13442e19ed28b6ce378a2",
    PATCH: "f1d97cbbf169a2a3ebcefda85b4f5d811b8c0715ba17175598bf51aac9b9920f",
}
_compile_inputs = base.compile_inputs
_immutable_bindings = base.immutable_bindings
_write_json = base.write_json


def policy_identity():
    for path, expected in PINS.items():
        base.require(path.is_file() and base.sha256(path) == expected, f"POLICY_SOURCE_DRIFT:{path.name}")
    return {"experiment": EXPERIMENT, "policyChanged": True,
        "qualification": "hypothetical CURRENT admission for experiment only",
        "acceptanceScope": "revealed-data candidate-policy acceptance",
        "productionPromotionApproved": False, "coefficientsChanged": False,
        "thresholdFittingPerformed": False, "maximumAlternatives": 3,
        "maximumStates": 8192, "maximumVerifiedTerminals": 64,
        "files": {base.path_key(path): base.sha256(path) for path in [Path(__file__), *PINS]}}


def compile_inputs(java):
    policy_identity()
    sources, jars, android = _compile_inputs(java)
    base.require(sources.count(ORIGINAL) == 1 and VARIANT not in sources, "GENERATOR_SOURCE_CLOSURE")
    return [VARIANT if path == ORIGINAL else path for path in sources], jars, android


def immutable_bindings(java, sources, jars, android, rows):
    identity = policy_identity()
    result = _immutable_bindings(java, sources, jars, android, rows)
    result["files"].update(identity["files"])
    result["candidatePolicy"] = identity
    result["qualification"] = identity["qualification"]
    return result


def write_json(path, value):
    # These are protocol receipts, not source/config files. Keep the original
    # cache identities and hash chain; add explicit experimental provenance.
    _write_json(path, {**value, "candidatePolicy": policy_identity(), "policyChanged": True})


def score_complete_receipt(*args, **kwargs):
    return {**_score_complete_receipt(*args, **kwargs),
        "candidatePolicy": policy_identity(), "policyChanged": True}


def before_holdout(root):
    base.require(not (root / "holdout-scores").exists() and
                 not (root / "policy-freeze.json").exists(), "CALIBRATION_BEFORE_FREEZE_AND_HOLDOUT")


def admit_calibration_report(root, export):
    path = root / "calibration-report.json"
    base.require(path.is_file(), "CALIBRATION_REPORT_REQUIRED")
    receipt = json.loads(path.read_text())
    base.require(receipt.get("complete") is True and receipt["candidatePolicy"] == policy_identity() and receipt["policyChanged"] is True
        and receipt["experiment"] == EXPERIMENT and receipt["split"] == "calibration"
        and receipt["exportReceiptSha256"] == base.sha256(root / "export-receipt.json")
        and receipt["scoresCompleteSha256"] == base.sha256(root / "calibration-scores/complete.json")
        and receipt["holdoutObservedForSelection"] is False, "CALIBRATION_REPORT_IDENTITY")
    required = {"deliveries-calibration.tsv", "deliveries-calibration.jsonl",
                "replay-calibration-ready.jsonl", "replay-calibration-ready.log",
                "replay-calibration-unavailable.jsonl", "replay-calibration-unavailable.log",
                "row-evidence-calibration.jsonl"}
    base.require(set(receipt["artifacts"]) == required, "CALIBRATION_ARTIFACT_INVENTORY")
    for name, expected in receipt["artifacts"].items():
        base.require(base.sha256(root / name) == expected, "CALIBRATION_REPORT_ARTIFACT_DRIFT")
    rows = split_rows(root, "calibration")
    evaluated, summaries = [], {}
    for mode in ("ready", "unavailable"):
        observations = base.read_jsonl(root / f"replay-calibration-{mode}.jsonl")
        base.require(len(observations) == 6000 and
            [item["id"] for item in observations] == [row["id"] for row in rows] and
            all(item["split"] == "calibration" for item in observations), "CALIBRATION_REPLAY_ROWS")
        items = [evidence(row, item, "calibration", mode) for row, item in zip(rows, observations)]
        evaluated.extend(items)
        summaries[mode] = base.summarize_rows(items)
    for values in summaries["ready"]["languages"].values():
        values["candidatePolicyPointGates"] = base.product_policy_gates(values)
    base.require(receipt["summaries"] == summaries, "CALIBRATION_SUMMARY_MISMATCH")
    base.require(base.read_jsonl(root / "row-evidence-calibration.jsonl") == evaluated,
                 "CALIBRATION_EVIDENCE_MISMATCH")
    requests = base.read_jsonl(root / "requests-calibration.jsonl")
    _, scores = base.admit_score_stage(root, "calibration", export)
    deliveries = [base.delivery_for(request, scores[request["id"]]) for request in requests]
    base.require(base.read_jsonl(root / "deliveries-calibration.jsonl") == deliveries and
        (root / "deliveries-calibration.tsv").read_text() ==
        "".join(base.delivery_tsv_line(item) + "\n" for item in deliveries), "CALIBRATION_DELIVERY_MISMATCH")
    return receipt


def policy_freeze_receipt(root, calibration_complete):
    export = base.load_export(root)
    admit_calibration_report(root, export)
    return {"schemaVersion": base.SCHEMA, "complete": True, "experiment": EXPERIMENT,
        "stage": "changed-candidate-policy-freeze", "policyChanged": True,
        "candidatePolicy": policy_identity(), "coefficientsChanged": False,
        "thresholdFittingPerformed": False, "holdoutObservedForSelection": False,
        "combinedConfigSha256": base.sha256(base.COMBINED_CONFIG),
        "deterministicConfigSha256": base.sha256(base.DETERMINISTIC_CONFIG),
        "calibrationReportSha256": base.sha256(root / "calibration-report.json"),
        "calibrationCompleteSha256": base.sha256(root / "calibration-scores/complete.json"),
        "calibrationScoresSha256": calibration_complete["scoresSha256"],
        "exportReceiptSha256": base.sha256(root / "export-receipt.json")}


def evidence(row, observation, split, mode):
    base.require(observation["status"] == "COMPLETE", f"REPLAY_ROW_ERROR:{row['id']}:{mode}")
    after = observation["afterBoundary"]["text"]
    prefix = row["prefix"] + " " if row["prefix"] else ""
    raw = prefix + row["typed"] + " "
    expected = prefix + row.get("expectedSpelling", row["typed"]) + " "
    auto = observation.get("autoEdit")
    generation = (auto or {}).get("correctionGeneration")
    canonical = bool(generation and any(item["kind"] == "CANONICAL_CASE" for item in generation["alternatives"]))
    spelling = bool(auto and generation and not canonical)
    original = base.original_retention(observation, row["typed"])
    return {"input": row, "split": split, "mode": mode, "observation": observation,
        "evaluation": {"modelRequested": observation.get("actualModelRequest") is not None,
            "modelError": observation.get("modelAdmission") == "MATCHED_SCORING_ERROR",
            "modelRefused": str(observation.get("modelAdmission", "")).startswith("REFUSED"),
            "originalRetained": original["retained"], "actualOriginal": original["actualOriginal"],
            "corpusTokenMatchesActualOriginal": original["corpusTokenMatchesActualOriginal"],
            "candidateRecall": any(item["text"] == row.get("expectedSpelling") for item in
                observation.get("actualRequestGeneration", {}).get("alternatives", [])) if row["cohort"] == "typo" else None,
            "spellingAutoEdit": spelling, "canonicalAutoEdit": bool(auto) and canonical,
            "mechanicalChange": observation["inputChangedByTyping"] or (bool(auto) and generation is None),
            "fullFinalTextChanged": after != raw,
            "correctFinalReplacement": spelling and not row["noAuto"] and after == expected,
            "undoExact": observation["restoredBeforeBoundaryExactly"]}}


def split_rows(root, split):
    # Filter before label inspection; calibration never computes holdout metrics.
    rows = [row for row in base.read_jsonl(root / "rows.jsonl") if row["split"] == split]
    expected = base.Counter({(language, cohort): count for language in base.LANGUAGES
                             for cohort, count in base.COHORT_COUNTS.items()})
    base.require(len(rows) == 6000 and len({row["id"] for row in rows}) == 6000
        and base.Counter((row["language"], row["cohort"]) for row in rows) == expected, "REPLAY_SPLIT_ROWS")
    return rows


def replay_split(args, split):
    root = Path(args.root).resolve(strict=True)
    export = base.load_export(root)
    freeze_sha = None
    if split == "calibration":
        before_holdout(root)
    else:
        base.admit_policy_freeze(root, export)
        freeze_sha = base.sha256(root / "policy-freeze.json")
    complete, scores = base.admit_score_stage(root, split, export, freeze_sha)
    java = base.select_bound_java(export)
    _, jars, android = compile_inputs(java)
    rows = split_rows(root, split)
    requests = base.read_jsonl(root / f"requests-{split}.jsonl")
    deliveries = [base.delivery_for(request, scores[request["id"]]) for request in requests]
    tsv = root / f"deliveries-{split}.tsv"
    with tsv.open("x", encoding="ascii") as stream:
        for item in deliveries:
            stream.write(base.delivery_tsv_line(item) + "\n")
    base.write_jsonl(root / f"deliveries-{split}.jsonl", deliveries)
    all_evidence, summaries, commands = [], {}, {}
    artifacts = [tsv, root / f"deliveries-{split}.jsonl"]
    for mode in ("ready", "unavailable"):
        output = root / f"replay-{split}-{mode}.jsonl"
        commands[mode] = base.run_harness(root, java, jars, android,
            root / "final-product-spelling-replay.jar", root / "inputs.tsv", output, mode,
            tsv if mode == "ready" else None, split)
        observations = base.read_jsonl(output)
        base.require(len(observations) == len(rows) and
            [item["id"] for item in observations] == [row["id"] for row in rows] and
            all(item["split"] == split for item in observations), "REPLAY_ROWS")
        evaluated = [evidence(row, item, split, mode) for row, item in zip(rows, observations)]
        all_evidence.extend(evaluated)
        summaries[mode] = base.summarize_rows(evaluated)
        artifacts.extend([output, root / f"{output.stem}.log"])
    for values in summaries["ready"]["languages"].values():
        values["candidatePolicyPointGates"] = base.product_policy_gates(values)
    base.require(all(item["model"]["refusals"] == 0 for item in summaries["ready"]["languages"].values()), "MODEL_REFUSALS")
    base.require(all(item["ordinarySpelling"]["automaticChanges"] == 0 for item in
                     summaries["unavailable"]["languages"].values()), "UNQUALIFIED_DETERMINISTIC_AUTO_REPLACE")
    evidence_path = root / f"row-evidence-{split}.jsonl"
    base.write_jsonl(evidence_path, all_evidence)
    artifacts.append(evidence_path)
    base.verify_bound_files(export)
    write_json(root / f"{split}-report.json", {"schemaVersion": base.SCHEMA, "complete": True,
        "experiment": EXPERIMENT, "split": split, "summaries": summaries,
        "exportReceiptSha256": base.sha256(root / "export-receipt.json"),
        "scoresCompleteSha256": base.sha256(root / f"{split}-scores/complete.json"),
        "policyFreezeSha256": freeze_sha, "holdoutObservedForSelection": False,
        "releaseApproved": False, "thresholdFittingPerformed": False,
        "artifacts": {path.name: base.sha256(path) for path in artifacts}, "commands": commands,
        "limits": ["Revealed-data candidate-policy acceptance; hypothetical CURRENT admission only.",
                   "No automatic production promotion or unseen qualification.",
                   "Host JVM and independent editor; physical and release gates remain separate."]})


# Local module instance only: ordinary evaluator imports and files stay unchanged.
base.EXPERIMENT = EXPERIMENT
base.compile_inputs = compile_inputs
base.immutable_bindings = immutable_bindings
base.write_json = write_json
_score_complete_receipt = base.score_complete_receipt
base.score_complete_receipt = score_complete_receipt
base.policy_freeze_receipt = policy_freeze_receipt


def main():
    parser = base.parser()
    sub = next(action for action in parser._actions if isinstance(action, base.argparse._SubParsersAction))
    sub.add_parser("calibration-report").add_argument("--root", required=True)
    args = parser.parse_args()
    policy_identity()
    if args.stage == "export":
        base.export_stage(args)
    elif args.stage.startswith("score-"):
        if args.stage == "score-calibration":
            before_holdout(Path(args.root))
        base.score_stage(args, args.stage.removeprefix("score-"))
    elif args.stage == "freeze-policy":
        before_holdout(Path(args.root))
        base.freeze_policy(args)
    else:
        replay_split(args, "calibration" if args.stage == "calibration-report" else "holdout")


if __name__ == "__main__":
    main()
