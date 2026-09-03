#!/usr/bin/env python3
"""Apply frozen deterministic and combined policies once to product spelling holdout."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import calibrate_combined as combined_ranker
import calibrate_deterministic as deterministic_ranker
from deterministic_policy import Weights, Thresholds, choose, propose
import export_calibration as calibration
import export_product_holdout as holdout
import score_product_holdout as scoring


def decide(generation: dict, score: dict | None, combined: dict, fallback: dict) -> tuple[int, bool]:
    policy = combined.get("policy")
    model = combined_ranker.model_proposal(generation, Weights(**policy["weights"]),
        policy["modelWeight"], score) if policy else None
    if model is not None:
        return choose(model, Thresholds(**policy["thresholds"])), True
    policy = fallback.get("policy")
    deterministic = propose(generation, Weights(**policy["weights"])) if policy else None
    return choose(deterministic, Thresholds(**policy["thresholds"]) if policy else None), False


def metrics(rows: list[dict], generated: list[dict], decisions: list[int], ev,
            used_model: list[bool] | None = None, scores: dict | None = None) -> dict:
    labels = deterministic_ranker.annotations(rows, generated)
    changed = [index for index, value in enumerate(decisions) if value]
    correct = sum(decisions[index] in labels[index][0] for index in changed)
    false_changes = sum(labels[index][1] for index in changed)
    negatives = sum(negative for _, negative in labels)
    typos = [(row, result) for row, result in zip(rows, generated, strict=True)
             if row["cohort"] == "typo"]
    recall = sum(row["expectedSpelling"] in [result["original"],
                 *(item["text"] for item in result["alternatives"])] for row, result in typos)
    result = {
        "rows": len(rows), "typoRows": len(typos), "negativeRows": negatives,
        "automaticReplacements": len(changed), "correctReplacements": correct,
        "incorrectReplacements": len(changed) - correct,
        "precision": ev.rate(correct, len(changed)),
        "falseChange": ev.rate(false_changes, negatives),
        "coverage": ev.rate(len(changed), len(rows)),
        "abstention": ev.rate(len(rows) - len(changed), len(rows)),
        "candidateRecall": ev.rate(recall, len(typos)),
        "originalAlwaysAvailable": all(row["typed"] == generation["original"]
                                       for row, generation in zip(rows, generated, strict=True)),
    }
    result["gate"] = {
        "minimum300": len(changed) >= 300,
        "precisionAtLeast99Percent": bool(changed and correct * 100 >= len(changed) * 99),
        "falseChangeAtMost0_5Percent": bool(negatives and false_changes * 200 <= negatives),
    }
    result["gate"]["pass"] = all(result["gate"].values()) and result["originalAlwaysAvailable"]
    if used_model is not None:
        result["modelAvailableRows"] = sum(used_model)
        result["deterministicFallbackRows"] = len(rows) - sum(used_model)
        result["modelErrors"] = sum("error" in (scores or {}).get(row["id"], {}) for row in rows)
    return result


def run(args) -> bool:
    output = Path(args.output).resolve()
    calibration.require(output.is_relative_to(calibration.REPO / "build") and not output.exists(),
                        "FRESH_BUILD_OUTPUT")
    export_path = Path(args.holdout_export).resolve(strict=True)
    rows, generated, receipt = scoring.load_verified(export_path)
    combined_path = Path(args.combined_config).resolve(strict=True)
    deterministic_path = Path(args.deterministic_config).resolve(strict=True)
    combined, deterministic, _ = holdout.verified_configs(
        combined_path, deterministic_path, Path(args.calibration_export).resolve(strict=True))
    calibration.require(receipt["combinedConfigSha256"] == combined["configSha256"]
                        and receipt["deterministicConfigSha256"] == deterministic["configSha256"],
                        "HOLDOUT_CONFIG_LINK")
    requests = scoring.requests_from(rows, generated)
    score_dir = Path(args.scoring).resolve(strict=True)
    complete = json.loads((score_dir / "complete.json").read_text())
    calibration.require(complete["scores"] == complete["requests"] == len(requests)
                        and complete["scoresSha256"] == calibration.sha(score_dir / "scores.jsonl")
                        and complete["holdoutGeneratorReceiptSha256"] == calibration.sha(export_path / "provenance.json")
                        and complete["combinedConfigSha256"] == combined["configSha256"], "COMPLETE_HOLDOUT_SCORES")
    ev = holdout.evaluator()
    _, scores = ev.load_cache(score_dir / "scores.jsonl", requests, complete["identity"])
    calibration.require(len(scores) == len(requests), "INCOMPLETE_HOLDOUT_SCORES")

    report = {"split": "holdout", "holdoutExecuted": True, "thresholdsFittedOnHoldout": False,
              "autoReplaceEnabled": False, "languages": {}}
    for language in ("en", "ru", "es"):
        pairs = [(row, generation) for row, generation in zip(rows, generated, strict=True)
                 if row["language"] == language]
        language_rows, language_generated = map(list, zip(*pairs))
        fallback_policy = deterministic["languages"][language]
        combined_policy = combined["languages"][language]
        deterministic_decisions = []
        combined_decisions, used_model = [], []
        for row, generation in zip(language_rows, language_generated, strict=True):
            policy = fallback_policy.get("policy")
            proposal = propose(generation, Weights(**policy["weights"])) if policy else None
            deterministic_decisions.append(choose(proposal,
                Thresholds(**policy["thresholds"]) if policy else None))
            decision, model_used = decide(generation, scores.get(row["id"]),
                                          combined_policy, fallback_policy)
            combined_decisions.append(decision)
            used_model.append(model_used)
        report["languages"][language] = {
            "deterministic": metrics(language_rows, language_generated, deterministic_decisions, ev),
            "modelAssisted": metrics(language_rows, language_generated, combined_decisions, ev,
                                      used_model, scores),
        }
    report["allLanguagesPass"] = all(value["modelAssisted"]["gate"]["pass"]
                                      for value in report["languages"].values())
    output.mkdir(parents=True)
    calibration.write_json(output / "report.json", report)
    calibration.write_json(output / "provenance.json", {
        "scope": "final-product-spelling-holdout", "holdoutExecuted": True,
        "thresholdsFittedOnHoldout": False,
        "combinedConfigSha256": combined["configSha256"],
        "deterministicConfigSha256": deterministic["configSha256"],
        "holdoutGeneratorReceiptSha256": calibration.sha(export_path / "provenance.json"),
        "holdoutScoresCompleteSha256": calibration.sha(score_dir / "complete.json"),
        "holdoutScoresSha256": complete["scoresSha256"],
        "reportSha256": calibration.sha(output / "report.json"),
        "sources": {str(path.resolve().relative_to(calibration.REPO)): calibration.sha(path.resolve()) for path in
                    (Path(__file__), Path(combined_ranker.__file__), Path(deterministic_ranker.__file__),
                     Path(__file__).with_name("deterministic_policy.py"), calibration.CORPUS / "evaluate.py")},
    })
    print("PASS" if report["allLanguagesPass"] else "FAIL")
    return report["allLanguagesPass"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("holdout-export", "scoring", "combined-config", "deterministic-config",
                   "calibration-export", "output"):
        parser.add_argument("--" + option, required=True)
    sys.exit(0 if run(parser.parse_args()) else 2)
