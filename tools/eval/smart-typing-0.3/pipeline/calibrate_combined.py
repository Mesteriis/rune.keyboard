"""Calibration-only combination of generated features and verified numeric model scores."""
import argparse
from dataclasses import asdict
import itertools
import json
import math
from pathlib import Path

import calibrate_deterministic as base
from deterministic_policy import Weights, Thresholds, Proposal, propose, choose
import export_calibration as export
from score_generated import requests_from

MODEL_WEIGHTS = (1, 2, 4, 8)


def model_proposal(generation: dict, weights: Weights, model_weight: int, scores: dict | None) -> Proposal | None:
    if generation["prohibitsAutoReplace"] or not generation["alternatives"] or scores is None or "error" in scores:
        return None
    means = {}
    for score in scores["scores"]:
        if score["scoredTokenCount"] <= 0:
            return None
        means[score["id"]] = score["sumLogProbability"] / score["scoredTokenCount"]
    if set(means) != {0, *(c["id"] for c in generation["alternatives"])}:
        raise ValueError("MODEL_CANDIDATE_IDS")
    ranked = []
    for candidate in generation["alternatives"]:
        single = propose({**generation, "alternatives": [candidate]}, weights)
        penalty = single.penalty - model_weight * (means[candidate["id"]] - means[0])
        if not math.isfinite(penalty):
            return None
        ranked.append((penalty, candidate["id"]))
    ranked.sort()
    return Proposal(ranked[0][1], ranked[0][0], ranked[1][0] if len(ranked) > 1 else None, len(generation["original"]))


def fit(rows: list[dict], generated: list[dict], scores: dict,
        minimum_precision_percent: int = 99) -> dict:
    export.require(minimum_precision_percent in (95, 97, 99), "PRECISION_PROFILE")
    export.require(rows and all(r["split"] == "calibration" for r in rows), "CALIBRATION_ONLY")
    labels = base.annotations(rows, generated)
    negatives = sum(negative for _, negative in labels)
    best_key = None
    best = None
    trials = 0
    for values in itertools.product(*(base.GRID[n] for n in ("edit", "frequency", "repetition", "fallback", "length"))):
        weights = Weights(*values)
        for model_weight in MODEL_WEIGHTS:
            proposals = [model_proposal(g, weights, model_weight, scores.get(r["id"]))
                         for r, g in zip(rows, generated, strict=True)]
            for limits in itertools.product(*(base.GRID[n] for n in ("original_penalty", "minimum_margin", "minimum_length"))):
                thresholds = Thresholds(*limits)
                replaced, correct, changed = base.counts(proposals, labels, thresholds)
                trials += 1
                if replaced and correct * 100 >= replaced * minimum_precision_percent and negatives and changed * 200 <= negatives:
                    key = (correct, -(replaced - correct), thresholds.minimum_margin,
                           thresholds.minimum_length, -thresholds.original_penalty, -model_weight)
                    if best_key is None or key > best_key:
                        best_key = key
                        best = {"weights": asdict(weights), "modelWeight": model_weight, "thresholds": asdict(thresholds)}
    return {"policy": best, "trials": trials}


def metrics(rows: list[dict], generated: list[dict], scores: dict, combined: dict, fallback: dict) -> dict:
    ev = base.evaluator()
    labels = base.annotations(rows, generated)
    decisions = []
    used_model = []
    policy = combined["policy"]
    deterministic = fallback["policy"]
    for row, generation in zip(rows, generated, strict=True):
        proposal = model_proposal(generation, Weights(**policy["weights"]), policy["modelWeight"], scores.get(row["id"])) if policy else None
        if proposal is not None:
            decisions.append(choose(proposal, Thresholds(**policy["thresholds"])))
            used_model.append(True)
        else:
            p = propose(generation, Weights(**deterministic["weights"])) if deterministic else None
            decisions.append(choose(p, Thresholds(**deterministic["thresholds"]) if deterministic else None))
            used_model.append(False)
    def subset_metrics(indices):
        changed = [i for i in indices if decisions[i]]
        return {"provisionalReplacements": len(changed),
                "precision": ev.rate(sum(decisions[i] in labels[i][0] for i in changed), len(changed)),
                "falseChange": ev.rate(sum(labels[i][1] for i in changed), sum(negative for _, negative in labels))}
    result = subset_metrics(range(len(rows)))
    result.update({"rows": len(rows), "coverage": ev.rate(result["provisionalReplacements"], len(rows)),
                   "abstention": ev.rate(len(rows) - result["provisionalReplacements"], len(rows)),
                   "model": subset_metrics([i for i, value in enumerate(used_model) if value]),
                   "fallback": subset_metrics([i for i, value in enumerate(used_model) if not value]),
                   "modelErrors": sum("error" in scores.get(r["id"], {}) for r in rows),
                   "holdoutQualified": False})
    return result


def run(args) -> None:
    output = Path(args.output).resolve()
    export.require(output.is_relative_to(export.REPO / "build") and not output.exists(), "FRESH_BUILD_OUTPUT")
    rows, generated, receipt = base.load_verified(
        Path(args.compiled_export), Path(getattr(args, "corpus", export.CORPUS)))
    minimum_precision_percent = getattr(args, "minimum_precision_percent", 99)
    export.require(minimum_precision_percent in (95, 97, 99), "PRECISION_PROFILE")
    ev = base.evaluator()
    requests = requests_from(rows, generated)
    scoring = Path(args.scoring)
    complete = json.loads((scoring / "complete.json").read_text())
    export.require(complete["scores"] == len(requests) and complete["requests"] == len(requests), "COMPLETE_MODEL_RUN")
    export.require(complete["scoresSha256"] == export.sha(scoring / "scores.jsonl"), "MODEL_CACHE_DIGEST")
    export.require(complete["generatorReceiptSha256"] == export.sha(Path(args.compiled_export) / "provenance.json"), "GENERATOR_IDENTITY")
    _, scores = ev.load_cache(scoring / "scores.jsonl", requests, complete["identity"])
    export.require(len(scores) == len(requests), "INCOMPLETE_MODEL_CACHE")
    fallback = json.loads(Path(args.deterministic_config).read_text())
    content = {k: v for k, v in fallback.items() if k != "configSha256"}
    export.require(ev.digest(content) == fallback["configSha256"] and fallback["maximumAlternatives"] == receipt["maximumAlternatives"]
                   and fallback["generatorReceiptSha256"] == complete["generatorReceiptSha256"], "FALLBACK_IDENTITY")
    source_paths = [Path(__file__), Path(base.__file__), Path(__file__).with_name("deterministic_policy.py"),
                    export.EVALUATOR_ROOT / "evaluate.py"]
    sources = {str(p.relative_to(export.REPO)): export.sha(p) for p in source_paths}
    output.mkdir(parents=True)
    fits, reports = {}, {}
    for language in ("en", "ru", "es"):
        subset, candidates = map(list, zip(*[(r, g) for r, g in zip(rows, generated, strict=True) if r["language"] == language]))
        fits[language] = fit(subset, candidates, scores, minimum_precision_percent)
        reports[language] = metrics(subset, candidates, scores, fits[language], fallback["languages"][language])
    export.require(sources == {p: export.sha(export.REPO / p) for p in sources}, "SOURCE_DRIFT")
    config = {"schemaVersion": 1, "scope": "combined-calibration-only", "holdoutQualified": False,
              "maximumAlternatives": receipt["maximumAlternatives"], "grid": base.GRID, "modelWeights": MODEL_WEIGHTS,
              "sources": sources, "modelCacheSha256": complete["scoresSha256"],
              "modelIdentity": complete["identity"], "fallbackConfigSha256": fallback["configSha256"], "languages": fits}
    if minimum_precision_percent != 99:
        config["minimumPrecisionPercent"] = minimum_precision_percent
    export.write_json(output / "config.json", {**config, "configSha256": ev.digest(config)})
    export.write_json(output / "report.json", {"split": "calibration", "holdoutExecuted": False, "autoReplaceEnabled": False,
        "languages": reports, "availabilityAssumption": "Every valid model result is available; missing/error results use deterministic fallback.",
        "limitations": ["Offline ideal-availability calibration, not physical boundary coverage.",
                        "Correlated authored rows; Wilson intervals are descriptive."]})
    print("Combined calibration complete; no holdout qualification or automatic replacement enabled.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("compiled-export", "scoring", "deterministic-config", "output"):
        parser.add_argument("--" + option, required=True)
    parser.add_argument("--corpus", default=export.CORPUS)
    parser.add_argument("--minimum-precision-percent", type=int, choices=(95, 97, 99), default=99)
    run(parser.parse_args())
