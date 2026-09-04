"""Fit a provisional deterministic policy on verified calibration exports only."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import importlib.util
import itertools
import json
from pathlib import Path

import export_calibration as export
from deterministic_policy import Weights, Thresholds, propose, choose

HERE = Path(__file__).resolve().parent
GRID = {
    "edit": [2, 4, 8], "frequency": [0, 1, 2], "repetition": [0, 2],
    "fallback": [0, 4], "length": [0, 1],
    "original_penalty": [8, 12, 16, 20, 24, 28, 32, 40, 48, 64],
    "minimum_margin": [1, 2, 4, 8, 12], "minimum_length": [1, 5, 9],
}


def evaluator():
    spec = importlib.util.spec_from_file_location("prepared_evaluator", HERE.parent / "evaluate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_verified(directory: Path, corpus_directory: Path = export.CORPUS) -> tuple[list[dict], list[dict], dict]:
    receipt = json.loads((directory / "provenance.json").read_text())
    export.require(receipt.get("sourceOverrides") == {} and receipt.get("harnessWidthArgument") is True,
                   "PRODUCTION_EXPORT_REQUIRED")
    maximum = receipt["maximumAlternatives"]
    export.require(type(maximum) is int and maximum in (1, 3, 7), "CANDIDATE_WIDTH")
    for name, key in [("candidates.jsonl", "candidates"), ("actual.tsv", "actual"), ("inputs.tsv", "inputs"),
                      ("generator.jar", "binary")]:
        export.require(export.sha(directory / name) == receipt[key], "EXPORT_DIGEST")
    export.require(all(export.sha(export.REPO / path) == digest for path, digest in receipt["sources"].items()),
                   "PRODUCTION_SOURCE_DRIFT")
    corpus_directory = Path(corpus_directory).resolve(strict=True)
    relative_corpus = str(corpus_directory.relative_to(export.REPO)) if corpus_directory.is_relative_to(export.REPO) else None
    recorded_corpus = receipt.get("corpusDirectory")
    export.require(relative_corpus is not None and (recorded_corpus == relative_corpus
                   or recorded_corpus is None and corpus_directory == export.CORPUS.resolve()),
                   "CORPUS_DIRECTORY")
    manifest = json.loads((corpus_directory / "manifest.json").read_text())
    export.require(export.sha(corpus_directory / "manifest.json") == receipt["corpusManifest"], "CORPUS_MANIFEST")
    for name, digest in manifest["files"].items():
        export.require(export.sha(corpus_directory / name) == digest, "CORPUS_DIGEST")
    ev = evaluator()
    corpus = ev.load_corpus(corpus_directory)
    ev.validate(corpus)
    rows = [r for r in corpus if r["split"] == "calibration" and r["task"] == "spelling"]
    export.require(len(rows) == 6000 and ev.digest(rows) == receipt["calibrationRows"], "CALIBRATION_ROWS")
    generated = export.parse_output((directory / "actual.tsv").read_text(), rows)
    stored = [json.loads(line) for line in (directory / "candidates.jsonl").read_text().splitlines()]
    export.require(generated == stored and all(len(g["alternatives"]) <= maximum for g in generated), "GENERATOR_RECORDS")
    return rows, generated, receipt


def annotations(rows: list[dict], generated: list[dict]) -> list[tuple[set[int], bool]]:
    """Labels enter only evaluation; noAuto is counted as an error, never used as a runtime veto."""
    labels = []
    for row, generation in zip(rows, generated, strict=True):
        expected = row.get("expectedSpelling") if row["cohort"] == "typo" and not row["noAuto"] else None
        good = {c["id"] for c in generation["alternatives"]
                if expected is not None and c["text"] == expected}
        labels.append((good, row["cohort"] != "typo"))
    return labels


def counts(proposals: list, labels: list, thresholds: Thresholds | None) -> tuple[int, int, int]:
    replaced = correct = false_change = 0
    for proposal, (good, negative) in zip(proposals, labels, strict=True):
        selected = choose(proposal, thresholds)
        if selected:
            replaced += 1
            correct += selected in good
            false_change += negative
    return replaced, correct, false_change


def fit(rows: list[dict], generated: list[dict]) -> dict:
    export.require(rows and all(r["split"] == "calibration" for r in rows), "CALIBRATION_ONLY")
    labels = annotations(rows, generated)
    negatives = sum(negative for _, negative in labels)
    best_key = None
    best = None
    trials = 0
    weight_names = ("edit", "frequency", "repetition", "fallback", "length")
    threshold_names = ("original_penalty", "minimum_margin", "minimum_length")
    for values in itertools.product(*(GRID[name] for name in weight_names)):
        weights = Weights(*values)
        proposals = [propose(g, weights) for g in generated]
        for limits in itertools.product(*(GRID[name] for name in threshold_names)):
            thresholds = Thresholds(*limits)
            replaced, correct, changed = counts(proposals, labels, thresholds)
            trials += 1
            # Exact integer gates; Wilson intervals are reported descriptively, not thresholded.
            if replaced and correct * 100 >= replaced * 99 and negatives and changed * 200 <= negatives:
                # Maximize correct changes, then fewer errors, then stronger evidence margin.
                key = (correct, -(replaced - correct), thresholds.minimum_margin,
                       thresholds.minimum_length, -thresholds.original_penalty)
                if best_key is None or key > best_key:
                    best_key = key
                    best = {"weights": asdict(weights), "thresholds": asdict(thresholds)}
    return {"policy": best, "trials": trials}


def metrics(rows: list[dict], generated: list[dict], fitted: dict) -> dict:
    ev = evaluator()
    labels = annotations(rows, generated)
    policy = fitted["policy"]
    proposals = [propose(g, Weights(**policy["weights"])) for g in generated] if policy else [None] * len(rows)
    thresholds = Thresholds(**policy["thresholds"]) if policy else None
    replaced, correct, changed = counts(proposals, labels, thresholds)
    typos = [(r, g) for r, g in zip(rows, generated, strict=True) if r["cohort"] == "typo"]
    recall = sum(r["expectedSpelling"] in [g["original"]] + [c["text"] for c in g["alternatives"]] for r, g in typos)
    return {"rows": len(rows), "uniqueInputs": len({r["typed"] for r in rows}),
            "provisionalReplacements": replaced, "precision": ev.rate(correct, replaced),
            "falseChange": ev.rate(changed, sum(negative for _, negative in labels)),
            "coverage": ev.rate(replaced, len(rows)), "abstention": ev.rate(len(rows) - replaced, len(rows)),
            "candidateRecall": ev.rate(recall, len(typos)),
            "calibrationCountAtLeast300": replaced >= 300, "holdoutQualified": False}


def run(args) -> None:
    output = Path(args.output).resolve()
    export.require(output.is_relative_to(export.REPO / "build") and not output.exists(), "FRESH_BUILD_OUTPUT")
    sources = {str(p.relative_to(export.REPO)): export.sha(p) for p in
               [Path(__file__), HERE / "deterministic_policy.py", HERE / "export_calibration.py", HERE.parent / "evaluate.py"]}
    rows, generated, receipt = load_verified(Path(args.compiled_export).resolve(strict=True),
                                             Path(getattr(args, "corpus", export.CORPUS)))
    output.mkdir(parents=True)
    fits, reports = {}, {}
    for language in ("en", "ru", "es"):
        pairs = [(r, g) for r, g in zip(rows, generated, strict=True) if r["language"] == language]
        subset, candidates = map(list, zip(*pairs))
        fits[language] = fit(subset, candidates)
        reports[language] = metrics(subset, candidates, fits[language])
    export.require(sources == {p: export.sha(export.REPO / p) for p in sources}, "SOURCE_DRIFT")
    ev = evaluator()
    config = {"schemaVersion": 1, "scope": "deterministic-calibration-only", "holdoutQualified": False,
              "maximumAlternatives": receipt["maximumAlternatives"], "grid": GRID, "sources": sources,
              "generatorReceiptSha256": export.sha(Path(args.compiled_export) / "provenance.json"),
              "calibrationRowsSha256": receipt["calibrationRows"], "languages": fits}
    export.write_json(output / "config.json", {**config, "configSha256": ev.digest(config)})
    export.write_json(output / "report.json", {"split": "calibration", "modelUsed": False,
        "holdoutExecuted": False, "autoReplaceEnabled": False, "languages": reports,
        "limitations": ["Repeated lexical families/panels; Wilson intervals are row-descriptive only.",
                        "Fitting uses only calibration; these policies do not authorize production AutoReplace."]})
    print("Deterministic calibration complete; holdout and production AutoReplace remain unqualified.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiled-export", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--corpus", default=export.CORPUS)
    run(parser.parse_args())
