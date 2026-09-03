#!/usr/bin/env python3
"""Export and evaluate the exact seven-way production contextual suggestion rule."""
from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import export_calibration as shared
from score_product_holdout import score_requests


HERE = Path(__file__).resolve().parent
ENGINE = shared.REPO / "app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/punctuation/ContextualPunctuationEngine.kt"
LANGUAGE = shared.REPO / "app/src/main/java/io/github/mesteriis/rune/keyboard/ime/model/KeyboardState.kt"
HARNESS = HERE / "ContextualExport.kt"
BOUNDARIES = [" ", ", ", ": ", "; ", ". ", "? ", "! "]


def evaluator():
    spec = importlib.util.spec_from_file_location("contextual_evaluator", shared.CORPUS / "evaluate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def corpus_rows() -> list[dict]:
    ev = evaluator()
    corpus = ev.load_corpus()
    ev.validate(corpus)
    rows = [row for row in corpus if row["task"] == "punctuation"]
    shared.require(len(rows) == 1200, "CONTEXTUAL_ROWS")
    return rows


def parse_output(text: str, rows: list[dict]) -> list[dict]:
    results, count = [], 0
    for line in text.splitlines():
        fields = line.split("\t")
        if fields[0] == "R":
            shared.require(len(fields) == 3 and int(fields[1]) == len(results), "ROW_ID")
            shared.require(not results or len(results[-1]["variants"]) == count, "VARIANT_COUNT")
            count = int(fields[2])
            results.append({"id": rows[len(results)]["id"], "variants": []})
        elif fields[0] == "C":
            shared.require(len(fields) == 5 and results and int(fields[1]) == len(results) - 1,
                           "VARIANT_OWNER")
            variant_id = int(fields[2])
            boundary, continuation = map(shared.decoded, fields[3:5])
            shared.require(variant_id == len(results[-1]["variants"]), "VARIANT_ID")
            results[-1]["variants"].append({"id": variant_id, "boundary": boundary,
                                             "continuation": continuation})
        else:
            raise ValueError("UNEXPECTED_RECORD")
    shared.require(len(results) == len(rows) and len(results[-1]["variants"]) == count,
                   "INCOMPLETE_OUTPUT")
    for row, result in zip(rows, results, strict=True):
        shared.require([item["boundary"] for item in result["variants"]] == BOUNDARIES,
                       "PRODUCTION_BOUNDARIES")
        result.update({"split": row["split"], "language": row["language"],
            "prefix": row["prefix"], "ambiguous": row["ambiguous"],
            "expectedCandidate": BOUNDARIES.index(row["expectedBoundary"])})
    return results


def toolchain(gradle_cache: Path) -> list[Path]:
    manifest = json.loads((shared.LEXICON /
        "weighted-qualification/manifests/reproduction-toolchain.json").read_text())
    jars = []
    for item in manifest["jars"]:
        found = list((gradle_cache / item["group"] / item["artifact"] / item["version"]).glob("*/*.jar"))
        shared.require(len(found) == 1 and shared.sha(found[0]) == item["sha256"], "PINNED_TOOLCHAIN")
        jars.append(found[0])
    return jars


def export_run(args) -> None:
    output = Path(args.output).resolve()
    shared.require(output.is_relative_to(shared.REPO / "build") and not output.exists(), "FRESH_OUTPUT")
    rows = corpus_rows()
    sources = [LANGUAGE, ENGINE, HARNESS]
    source_hashes = {str(path.relative_to(shared.REPO)): shared.sha(path) for path in sources}
    jars = toolchain(Path(args.gradle_cache))
    version = subprocess.run([args.java, "-version"], capture_output=True, check=True, timeout=15)
    shared.require(b'version "17.' in version.stderr, "JAVA_17")
    output.mkdir(parents=True)
    inputs = output / "inputs.tsv"
    with inputs.open("x", encoding="ascii") as stream:
        for index, row in enumerate(rows):
            values = [base64.b64encode(row[key].encode()).decode("ascii") for key in ("prefix", "currentWord")]
            stream.write(f'{index}\t{row["language"]}\t{values[0]}\t{values[1]}\n')
    binary = output / "contextual-export.jar"
    command = [args.java, "-XX:ActiveProcessorCount=2", "-Xmx512m", "-cp", os.pathsep.join(map(str, jars)),
        "org.jetbrains.kotlin.cli.jvm.K2JVMCompiler", "-no-stdlib", "-no-reflect", "-jvm-target", "17",
        "-classpath", os.pathsep.join(map(str, jars[1:3])), "-d", str(binary), *map(str, sources)]
    with (output / "compile.log").open("xb") as log:
        subprocess.run(command, stdout=log, stderr=log, check=True, timeout=120)
    command = [args.java, "-XX:ActiveProcessorCount=2", "-Xmx512m", "-cp",
        os.pathsep.join(map(str, [binary, *jars[1:3]])),
        "io.github.mesteriis.rune.keyboard.smarttyping.punctuation.ContextualExport", str(inputs)]
    with (output / "actual.tsv").open("xb") as data, (output / "run.log").open("xb") as log:
        subprocess.run(command, stdout=data, stderr=log, check=True, timeout=120)
    results = parse_output((output / "actual.tsv").read_text(), rows)
    with (output / "rows.jsonl").open("x", encoding="utf-8") as stream:
        for result in results:
            stream.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    shared.require(source_hashes == {str(path.relative_to(shared.REPO)): shared.sha(path) for path in sources},
                   "SOURCE_DRIFT")
    shared.write_json(output / "provenance.json", {"scope": "production-contextual-export",
        "corpusManifest": shared.sha(shared.CORPUS / "manifest.json"), "rows": evaluator().digest(rows),
        "sources": source_hashes, "inputs": shared.sha(inputs), "actual": shared.sha(output / "actual.tsv"),
        "records": shared.sha(output / "rows.jsonl"), "binary": shared.sha(binary),
        "exporter": shared.sha(Path(__file__)), "holdoutScored": False})
    print("Exported 1200 exact production contextual rows; no model scoring.")


def load_export(directory: Path) -> list[dict]:
    receipt = json.loads((directory / "provenance.json").read_text())
    shared.require(receipt["scope"] == "production-contextual-export"
        and shared.sha(directory / "inputs.tsv") == receipt["inputs"]
        and shared.sha(directory / "actual.tsv") == receipt["actual"]
        and shared.sha(directory / "rows.jsonl") == receipt["records"]
        and all(shared.sha(shared.REPO / name) == digest for name, digest in receipt["sources"].items()),
        "EXPORT_IDENTITY")
    records = [json.loads(line) for line in (directory / "rows.jsonl").read_text().splitlines()]
    shared.require(len(records) == 1200, "EXPORT_ROWS")
    return records


def requests(records: list[dict], split: str) -> list[dict]:
    selected = [record for record in records if record["split"] == split]
    shared.require(len(selected) == 600, "SPLIT_ROWS")
    return [{"id": record["id"], "split": split, "prefix": record["prefix"],
             "candidates": [item["continuation"] for item in record["variants"]]} for record in selected]


def verified_model(config_path: Path, runner: Path, model: Path) -> dict:
    config = json.loads(config_path.read_text())
    content = {key: value for key, value in config.items() if key != "configSha256"}
    ev = evaluator()
    shared.require(ev.digest(content) == config["configSha256"], "SPELLING_CONFIG")
    identity = config["modelIdentity"]
    shared.require(shared.sha(runner) == identity["runnerSha256"]
                   and shared.sha(model) == identity["modelSha256"], "MODEL_IDENTITY")
    return identity


def score_run(args) -> None:
    export_dir = Path(args.export).resolve(strict=True)
    records = load_export(export_dir)
    selected = requests(records, args.split)
    output = Path(args.output).resolve()
    shared.require(output.is_relative_to(shared.REPO / "build"), "BUILD_OUTPUT")
    runner, model = Path(args.runner).resolve(strict=True), Path(args.model).resolve(strict=True)
    verified_model(Path(args.model_config).resolve(strict=True), runner, model)
    ev = evaluator()
    identity = ev.cache_identity(selected, runner, model)
    export_receipt = shared.sha(export_dir / "provenance.json")
    frozen = None
    if args.split == "holdout":
        shared.require(args.frozen_config is not None, "FROZEN_CONTEXTUAL_CONFIG_REQUIRED")
        frozen = json.loads(Path(args.frozen_config).read_text())
        content = {key: value for key, value in frozen.items() if key != "configSha256"}
        shared.require(ev.digest(content) == frozen["configSha256"]
                       and frozen["exportReceiptSha256"] == export_receipt
                       and frozen["engineSha256"] == shared.sha(ENGINE)
                       and frozen["qualitySourceSha256"] == shared.sha(Path(__file__)),
                       "FROZEN_CONTEXTUAL_CONFIG")
    output.mkdir(parents=True, exist_ok=True)
    run_input = {"scope": f"contextual-{args.split}-scores", "split": args.split,
        "requests": len(selected), "identity": identity, "exportReceiptSha256": export_receipt,
        "frozenConfigSha256": frozen and frozen["configSha256"]}
    info = output / "run-input.json"
    if info.exists(): shared.require(json.loads(info.read_text()) == run_input, "RESUME_IDENTITY")
    else: shared.write_json(info, run_input)
    score_requests(selected, runner, model, output / "scores.jsonl", ev, args.limit)
    _, scores = ev.load_cache(output / "scores.jsonl", selected, identity)
    if len(scores) == len(selected) and not (output / "complete.json").exists():
        shared.write_json(output / "complete.json", {**run_input, "scores": len(scores),
            "runtimeErrors": sum("error" in value for value in scores.values()),
            "scoresSha256": shared.sha(output / "scores.jsonl")})
    print(f"Validated {len(scores)}/{len(selected)} contextual {args.split} responses.")


def decisions(records: list[dict], scores: dict) -> list[int]:
    result = []
    for record in records:
        score = scores.get(record["id"])
        if score is None or "error" in score:
            result.append(0)
            continue
        means = {item["id"]: item["sumLogProbability"] / item["scoredTokenCount"]
                 for item in score["scores"]}
        shared.require(set(means) == set(range(7)), "SCORE_IDS")
        winner = max(range(1, 7), key=lambda item: (means[item], -item))
        result.append(winner if means[winner] > means[0] else 0)
    return result


def metrics(records: list[dict], scores: dict) -> dict:
    ev = evaluator()
    chosen = decisions(records, scores)
    unambiguous = [index for index, row in enumerate(records) if not row["ambiguous"]]
    ambiguous = [index for index, row in enumerate(records) if row["ambiguous"]]
    suggestions = [index for index in unambiguous if chosen[index] != 0]
    correct = sum(chosen[index] == records[index]["expectedCandidate"] for index in suggestions)
    return {"rows": len(records), "unambiguousRows": len(unambiguous), "ambiguousRows": len(ambiguous),
        "suggestions": len(suggestions), "correctSuggestions": correct,
        "suggestionPrecision": ev.rate(correct, len(suggestions)),
        "unambiguousTop1Coverage": ev.rate(correct, len(unambiguous)),
        "unambiguousAbstention": ev.rate(sum(chosen[index] == 0 for index in unambiguous), len(unambiguous)),
        "ambiguousNonSpaceSuggestion": ev.rate(sum(chosen[index] != 0 for index in ambiguous), len(ambiguous)),
        "runtimeErrors": sum("error" in scores.get(row["id"], {}) for row in records),
        "automaticReplacements": 0}


def load_scores(directory: Path, selected: list[dict]) -> tuple[dict, dict]:
    complete = json.loads((directory / "complete.json").read_text())
    shared.require(complete["scores"] == complete["requests"] == len(selected)
                   and complete["scoresSha256"] == shared.sha(directory / "scores.jsonl"), "COMPLETE_SCORES")
    _, scores = evaluator().load_cache(directory / "scores.jsonl", selected, complete["identity"])
    shared.require(len(scores) == len(selected), "SCORE_COUNT")
    return complete, scores


def freeze_run(args) -> None:
    export_dir = Path(args.export).resolve(strict=True)
    all_records = load_export(export_dir)
    records = [row for row in all_records if row["split"] == "calibration"]
    selected = requests(all_records, "calibration")
    complete, scores = load_scores(Path(args.scoring).resolve(strict=True), selected)
    output = Path(args.output).resolve()
    shared.require(output.is_relative_to(shared.REPO / "build") and not output.exists(), "FRESH_OUTPUT")
    report = {language: metrics([row for row in records if row["language"] == language], scores)
              for language in ("en", "ru", "es")}
    config = {"schemaVersion": 1, "scope": "contextual-fixed-rule-calibration",
        "selectionRule": "best non-original average log probability strictly greater than Original; stable lower ID",
        "minimumDelta": 0.0, "thresholdSearchPerformed": False,
        "exportReceiptSha256": shared.sha(export_dir / "provenance.json"),
        "calibrationCompleteSha256": shared.sha(Path(args.scoring) / "complete.json"),
        "calibrationScoresSha256": complete["scoresSha256"],
        "modelIdentity": complete["identity"], "calibrationMetrics": report,
        "engineSha256": shared.sha(ENGINE), "qualitySourceSha256": shared.sha(Path(__file__))}
    output.mkdir(parents=True)
    ev = evaluator()
    shared.write_json(output / "config.json", {**config, "configSha256": ev.digest(config)})
    print("Frozen the pre-existing production contextual rule; no threshold search.")


def report_run(args) -> None:
    export_dir = Path(args.export).resolve(strict=True)
    all_records = load_export(export_dir)
    records = [row for row in all_records if row["split"] == "holdout"]
    selected = requests(all_records, "holdout")
    complete, scores = load_scores(Path(args.scoring).resolve(strict=True), selected)
    config = json.loads(Path(args.frozen_config).read_text())
    ev = evaluator()
    content = {key: value for key, value in config.items() if key != "configSha256"}
    shared.require(ev.digest(content) == config["configSha256"]
                   and complete["frozenConfigSha256"] == config["configSha256"]
                   and config["engineSha256"] == shared.sha(ENGINE)
                   and config["qualitySourceSha256"] == shared.sha(Path(__file__)), "FROZEN_CONFIG")
    report = {"split": "holdout", "automaticReplacements": 0, "thresholdsFittedOnHoldout": False,
        "languages": {language: metrics([row for row in records if row["language"] == language], scores)
                      for language in ("en", "ru", "es")}}
    output = Path(args.output).resolve()
    shared.require(output.is_relative_to(shared.REPO / "build") and not output.exists(), "FRESH_OUTPUT")
    output.mkdir(parents=True)
    shared.write_json(output / "report.json", report)
    shared.write_json(output / "provenance.json", {"scope": "contextual-suggestion-holdout",
        "configSha256": config["configSha256"], "scoresSha256": complete["scoresSha256"],
        "reportSha256": shared.sha(output / "report.json"), "holdoutExecuted": True})
    print("Contextual suggestion holdout complete; no automatic application evaluated.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export_parser = commands.add_parser("export")
    for option in ("output", "java", "gradle-cache"): export_parser.add_argument("--" + option, required=True)
    score_parser = commands.add_parser("score")
    for option in ("export", "output", "model-config", "runner", "model"):
        score_parser.add_argument("--" + option, required=True)
    score_parser.add_argument("--split", choices=("calibration", "holdout"), required=True)
    score_parser.add_argument("--frozen-config")
    score_parser.add_argument("--limit", type=int)
    freeze_parser = commands.add_parser("freeze")
    for option in ("export", "scoring", "output"): freeze_parser.add_argument("--" + option, required=True)
    report_parser = commands.add_parser("report")
    for option in ("export", "scoring", "frozen-config", "output"):
        report_parser.add_argument("--" + option, required=True)
    args = parser.parse_args()
    {"export": export_run, "score": score_run, "freeze": freeze_run, "report": report_run}[args.command](args)


if __name__ == "__main__":
    main()
