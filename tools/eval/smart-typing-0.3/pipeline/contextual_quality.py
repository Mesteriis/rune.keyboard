#!/usr/bin/env python3
"""Export and evaluate the exact seven-way production contextual suggestion rule."""
from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import math
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
POLICY = ENGINE.with_name("ContextualPunctuationPolicy.kt")
PROBE = HERE / "ContextualPolicyProbe.kt"
TOOLCHAIN_MANIFEST = shared.LEXICON / "weighted-qualification/manifests/reproduction-toolchain.json"
BOUNDARIES = [" ", ", ", ": ", "; ", ". ", "? ", "! "]
ORIGINAL_ADVANTAGE = 0.5
RIVAL_ADVANTAGE = 4.0


def policy_binding() -> dict:
    return {"schemaVersion": 2, "policySourceSha256": shared.sha(POLICY),
        "qualitySourceSha256": shared.sha(Path(__file__)),
        "policy": {"version": 2, "rule": "total-log-probability-margins",
            "originalAdvantage": ORIGINAL_ADVANTAGE, "originalComparison": ">",
            "rivalAdvantage": RIVAL_ADVANTAGE, "rivalComparison": ">=",
            "tieOrder": "ascending-candidate-id", "tokenCountRange": [1, 255]}}


def require_binding(receipt: dict, code: str) -> None:
    binding = policy_binding()
    shared.require(evaluator().digest({key: receipt.get(key) for key in binding}) == evaluator().digest(binding), code)


def choose(expected_ids: list[int], scores: list[dict]) -> int:
    """Numeric mirror of the production kernel; zero means abstention/Original."""
    integer = lambda value: type(value) is int and -(2**31) <= value < 2**31
    if (not isinstance(expected_ids, list) or not 2 <= len(expected_ids) <= 8
            or any(not integer(value) or value < 0 for value in expected_ids)
            or 0 not in expected_ids or len(set(expected_ids)) != len(expected_ids)
            or not isinstance(scores, list) or len(scores) != len(expected_ids)):
        return 0
    for item in scores:
        if not isinstance(item, dict): return 0
        identifier, total, count = (item.get(key) for key in ("id", "sumLogProbability", "scoredTokenCount"))
        if (not integer(identifier) or type(total) not in (int, float)
                or not integer(count) or not 1 <= count <= 255): return 0
        try:
            if not math.isfinite(total) or total > 0: return 0
        except OverflowError:
            return 0
    if {item["id"] for item in scores} != set(expected_ids): return 0
    totals = {item["id"]: float(item["sumLogProbability"]) for item in scores}
    ordered = sorted((identifier for identifier in expected_ids if identifier != 0),
                     key=lambda identifier: (-totals[identifier], identifier))
    if len(ordered) < 2: return 0
    winner, rival = ordered[:2]
    return winner if (totals[winner] - totals[0] > ORIGINAL_ADVANTAGE
                      and totals[winner] - totals[rival] >= RIVAL_ADVANTAGE) else 0


def parity_cases() -> list[dict]:
    """Fixed synthetic numeric contracts only; no corpus or model input is read."""
    def case(ids=(0, 1, 2), totals=(-8.0, -1.0, -5.0), counts=(1, 1, 1), mode="ok"):
        return {"ids": list(ids), "mode": mode, "scores": [
            {"id": identifier, "sumLogProbability": total, "scoredTokenCount": count}
            for identifier, total, count in zip(ids, totals, counts)]}
    cases = [case(totals=(-2.0, -3.0, -10.0), counts=(1, 2, 1)), case(counts=(1, 1, 255))]
    for size in (7, 8):
        cases.append(case(tuple(range(size)), tuple(-1.0 if i == 1 else -8.0 for i in range(size)), (1,) * size))
    for original in (-0.5, -1.0, -1.25, -1.5, math.nextafter(-1.5, -math.inf)):
        cases.append(case(totals=(original, -1.0, -5.0)))
    for rival in (-1.0, math.nextafter(-5.0, math.inf), -5.0, math.nextafter(-5.0, -math.inf)):
        cases.append(case(totals=(-8.0, -1.0, rival)))
    cases += [case(totals=(-8.0, 0.0, -5.0)), case(totals=(0.0, 0.0, 0.0)),
              case(totals=(0.0, 0.0, 0.0), counts=(0, 0, 0))]
    # Expected IDs and returned score order vary independently; IDs are opaque to the kernel.
    orders = [(0, 7, 3), (3, 0, 7), (7, 3, 0)]
    for expected in orders:
        for returned in orders:
            item = case(returned, tuple({0: -8.0, 7: -1.0, 3: -5.0}[i] for i in returned))
            item["ids"] = list(expected)
            cases.append(item)
    for ids in ([], [0], [0, 1], [1, 2, 3], [0, 1, 1], [0, 1, -1], list(range(9)), [0, True, 2]):
        item = case(); item["ids"] = ids; cases.append(item)
    for position in range(3):
        for key, values in (("id", [-1, 9, True]),
                            ("sumLogProbability", [math.nan, math.inf, -math.inf, 0.1, True]),
                            ("scoredTokenCount", [0, -1, 256, True])):
            for value in values:
                item = case(); item["scores"][position][key] = value; cases.append(item)
        item = case(); del item["scores"][position]["sumLogProbability"]; cases.append(item)
    for scores in ([], case()["scores"][:-1], case()["scores"] + [case()["scores"][0]],
                   [case()["scores"][0], case()["scores"][1], case()["scores"][1]]):
        item = case(); item["scores"] = scores; cases.append(item)
    cases += [case(mode="error"), case(mode="missing"), {"ids": [], "scores": [], "mode": "excluded"}]
    return cases


def parity_input(cases: list[dict]) -> str:
    def number(value):
        if type(value) is bool: return "true" if value else "false"
        if isinstance(value, float) and not math.isfinite(value):
            return "NaN" if math.isnan(value) else "Infinity" if value > 0 else "-Infinity"
        return str(value) if value is not None else "_"
    return "".join(f'{index}\t{item["mode"]}\t' +
        (",".join(map(number, item["ids"])) or "_") + "\t" +
        (";".join(",".join(number(score.get(key)) for key in
            ("id", "sumLogProbability", "scoredTokenCount")) for score in item["scores"]) or "_") + "\n"
        for index, item in enumerate(cases))


def parity_expected(cases: list[dict]) -> str:
    result = []
    for index, item in enumerate(cases):
        if item["mode"] == "ok":
            chosen = choose(item["ids"], item["scores"])
        else:
            record = {"id": "synthetic", "variants": [{"id": i} for i in item["ids"]]}
            replies = {"synthetic": {"error": "SCORING_FAILED"}} if item["mode"] == "error" else {}
            chosen = decisions([record], replies)[0]
        result.append(f"{index}\t{chosen}\n")
    return "".join(result)


def probe_commands(java: Path, jars: list[Path], output: Path) -> tuple[list[str], list[str]]:
    binary = output / "contextual-policy-probe.jar"
    return ([str(java), "-XX:ActiveProcessorCount=2", "-Xmx512m", "-cp", os.pathsep.join(map(str, jars)),
        "org.jetbrains.kotlin.cli.jvm.K2JVMCompiler", "-no-stdlib", "-no-reflect", "-jvm-target", "17",
        "-classpath", os.pathsep.join(map(str, jars[1:3])), "-d", str(binary), str(POLICY), str(PROBE)],
        [str(java), "-XX:ActiveProcessorCount=2", "-Xmx512m", "-cp",
        os.pathsep.join(map(str, [binary, *jars[1:3]])),
        "io.github.mesteriis.rune.keyboard.smarttyping.punctuation.ContextualPolicyProbe", str(output / "inputs.tsv")])


def verification_run(args) -> None:
    output = Path(args.output).resolve()
    shared.require(output.is_relative_to(shared.REPO / "build") and not output.exists(), "FRESH_OUTPUT")
    jars = toolchain(Path(args.gradle_cache).resolve(strict=True))
    java = Path(args.java).resolve(strict=True)
    binding = policy_binding()
    probe_hash = shared.sha(PROBE)
    jar_hashes = {str(path.resolve()): shared.sha(path) for path in jars}
    java_hash = shared.sha(java)
    version = subprocess.run([str(java), "-version"], capture_output=True, check=True, timeout=15)
    shared.require(b'version "17.' in version.stderr, "JAVA_17")
    output.mkdir(parents=True)
    cases = parity_cases()
    (output / "inputs.tsv").write_text(parity_input(cases), encoding="ascii")
    (output / "expected.tsv").write_text(parity_expected(cases), encoding="ascii")
    (output / "java-version.txt").write_bytes(version.stderr)
    compile_command, run_command = probe_commands(java, jars, output)
    with (output / "compile.log").open("xb") as log:
        subprocess.run(compile_command, stdout=log, stderr=log, check=True, timeout=120)
    with (output / "actual.tsv").open("xb") as data, (output / "run.log").open("xb") as log:
        subprocess.run(run_command, stdout=data, stderr=log, check=True, timeout=120)
    shared.require((output / "actual.tsv").read_text() == parity_expected(cases), "POLICY_PARITY")
    shared.require(binding == policy_binding() and probe_hash == shared.sha(PROBE)
        and java_hash == shared.sha(java) and jar_hashes == {str(path.resolve()): shared.sha(path) for path in jars},
        "VERIFICATION_SOURCE_DRIFT")
    receipt = {**binding, "scope": "contextual-production-policy-parity", "cases": len(cases),
        "probeSha256": probe_hash, "toolchainManifestSha256": shared.sha(TOOLCHAIN_MANIFEST),
        "java": str(java), "javaSha256": java_hash, "jars": jar_hashes,
        "gradleCache": str(Path(args.gradle_cache).resolve()),
        "compileCommand": compile_command, "runCommand": run_command,
        "files": {name: shared.sha(output / name) for name in VERIFICATION_FILES},
        "holdoutScored": False, "syntheticOnly": True}
    shared.write_json(output / "verification.json", {**receipt, "receiptSha256": evaluator().digest(receipt)})
    print(f"Verified {len(cases)} synthetic cases against the actual production Kotlin policy; no quality evaluation.")


VERIFICATION_FILES = ("inputs.tsv", "expected.tsv", "actual.tsv", "contextual-policy-probe.jar",
                      "java-version.txt", "compile.log", "run.log")


def load_verification(directory: Path) -> dict:
    directory = directory.resolve(strict=True)
    shared.require(directory.is_relative_to(shared.REPO / "build"), "VERIFICATION_SCOPE")
    receipt = json.loads((directory / "verification.json").read_text())
    content = {key: value for key, value in receipt.items() if key != "receiptSha256"}
    shared.require(evaluator().digest(content) == receipt.get("receiptSha256"), "VERIFICATION_RECEIPT")
    require_binding(receipt, "VERIFICATION_POLICY")
    shared.require(receipt.get("scope") == "contextual-production-policy-parity"
        and receipt.get("syntheticOnly") is True and receipt.get("holdoutScored") is False
        and receipt.get("probeSha256") == shared.sha(PROBE)
        and receipt.get("toolchainManifestSha256") == shared.sha(TOOLCHAIN_MANIFEST)
        and receipt.get("files") == {name: shared.sha(directory / name) for name in VERIFICATION_FILES},
        "VERIFICATION_IDENTITY")
    jars = toolchain(Path(receipt["gradleCache"]))
    compile_command, run_command = probe_commands(Path(receipt["java"]), jars, directory)
    shared.require(receipt["jars"] == {str(path.resolve()): shared.sha(path) for path in jars}
        and shared.sha(Path(receipt["java"])) == receipt["javaSha256"]
        and receipt.get("compileCommand") == compile_command and receipt.get("runCommand") == run_command
        and 'version "17.' in (directory / "java-version.txt").read_text(), "VERIFICATION_TOOLCHAIN")
    cases = parity_cases()
    shared.require(receipt["cases"] == len(cases)
        and (directory / "inputs.tsv").read_text() == parity_input(cases)
        and (directory / "expected.tsv").read_text() == parity_expected(cases)
        and (directory / "actual.tsv").read_text() == parity_expected(cases), "VERIFICATION_OUTPUT")
    return receipt


def evaluator():
    spec = importlib.util.spec_from_file_location("contextual_evaluator",
                                                  shared.EVALUATOR_ROOT / "evaluate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def corpus_rows(corpus_directory: Path = shared.CORPUS) -> list[dict]:
    ev = evaluator()
    corpus = ev.load_corpus(Path(corpus_directory).resolve(strict=True))
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
            shared.require(count == 0 or 2 <= count <= 8, "VARIANT_COUNT")
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
        boundaries = [item["boundary"] for item in result["variants"]]
        shared.require(not boundaries or boundaries == BOUNDARIES,
                       "PRODUCTION_BOUNDARIES")
        result.update({"split": row["split"], "language": row["language"],
            "prefix": row["prefix"], "ambiguous": row["ambiguous"],
            "expectedCandidate": BOUNDARIES.index(row["expectedBoundary"])})
    return results


def toolchain(gradle_cache: Path) -> list[Path]:
    manifest = json.loads(TOOLCHAIN_MANIFEST.read_text())
    jars = []
    for item in manifest["jars"]:
        found = list((gradle_cache / item["group"] / item["artifact"] / item["version"]).glob("*/*.jar"))
        shared.require(len(found) == 1 and shared.sha(found[0]) == item["sha256"], "PINNED_TOOLCHAIN")
        jars.append(found[0])
    return jars


def export_run(args) -> None:
    output = Path(args.output).resolve()
    shared.require(output.is_relative_to(shared.REPO / "build") and not output.exists(), "FRESH_OUTPUT")
    corpus_directory = Path(getattr(args, "corpus", shared.CORPUS)).resolve(strict=True)
    shared.require(corpus_directory.is_relative_to(shared.REPO), "CORPUS_SCOPE")
    rows = corpus_rows(corpus_directory)
    sources = [LANGUAGE, ENGINE, HARNESS, POLICY]
    binding = policy_binding()
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
    shared.require(binding == policy_binding(), "POLICY_DRIFT")
    shared.write_json(output / "provenance.json", {**binding, "scope": "production-contextual-export",
        "corpusManifest": shared.sha(corpus_directory / "manifest.json"),
        "corpusDirectory": str(corpus_directory.relative_to(shared.REPO)),
        "rows": evaluator().digest(rows),
        "sources": source_hashes, "inputs": shared.sha(inputs), "actual": shared.sha(output / "actual.tsv"),
        "records": shared.sha(output / "rows.jsonl"), "binary": shared.sha(binary),
        "exporter": shared.sha(Path(__file__)), "holdoutScored": False})
    print("Exported 1200 exact production contextual rows; no model scoring.")


def load_export(directory: Path) -> list[dict]:
    receipt = json.loads((directory / "provenance.json").read_text())
    require_binding(receipt, "EXPORT_POLICY")
    shared.require(receipt["scope"] == "production-contextual-export"
        and shared.sha(directory / "inputs.tsv") == receipt["inputs"]
        and shared.sha(directory / "actual.tsv") == receipt["actual"]
        and shared.sha(directory / "rows.jsonl") == receipt["records"]
        and shared.sha(directory / "contextual-export.jar") == receipt["binary"]
        and receipt["sources"] == {str(path.relative_to(shared.REPO)): shared.sha(path)
                                   for path in (LANGUAGE, ENGINE, HARNESS, POLICY)}
        and receipt["exporter"] == shared.sha(Path(__file__)),
        "EXPORT_IDENTITY")
    records = [json.loads(line) for line in (directory / "rows.jsonl").read_text().splitlines()]
    shared.require(len(records) == 1200, "EXPORT_ROWS")
    return records


def requests(records: list[dict], split: str) -> list[dict]:
    selected = [record for record in records if record["split"] == split]
    shared.require(len(selected) == 600, "SPLIT_ROWS")
    return [{"id": record["id"], "split": split, "prefix": record["prefix"],
             "candidates": [item["continuation"] for item in record["variants"]]}
            for record in selected if record["variants"]]


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
    model_identity = verified_model(Path(args.model_config).resolve(strict=True), runner, model)
    ev = evaluator()
    expected_bytes = getattr(args, "expected_model_bytes", None)
    expected_bytes = ev.MODEL_SIZE if expected_bytes is None else expected_bytes
    identity = ev.cache_identity(selected, runner, model, model_identity["modelSha256"],
                                 expected_bytes)
    export_receipt = shared.sha(export_dir / "provenance.json")
    frozen = None
    if args.split == "holdout":
        shared.require(args.frozen_config is not None, "FROZEN_CONTEXTUAL_CONFIG_REQUIRED")
        frozen = load_frozen(Path(args.frozen_config), export_receipt)
        require_backend(frozen["modelIdentity"], identity)
    output.mkdir(parents=True, exist_ok=True)
    run_input = {**policy_binding(), "scope": f"contextual-{args.split}-scores", "split": args.split,
        "requests": len(selected), "identity": identity, "exportReceiptSha256": export_receipt,
        "frozenConfigSha256": frozen and frozen["configSha256"]}
    info = output / "run-input.json"
    if info.exists(): shared.require(json.loads(info.read_text()) == run_input, "RESUME_IDENTITY")
    else:
        shared.require(not (output / "scores.jsonl").exists() and not (output / "complete.json").exists(),
                       "ORPHAN_SCORE_ARTIFACTS")
        shared.write_json(info, run_input)
    score_requests(selected, runner, model, output / "scores.jsonl", ev, args.limit,
                   model_identity["modelSha256"], expected_bytes)
    require_binding(run_input, "SCORING_SOURCE_DRIFT")
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
        variants = record.get("variants", [])
        if not variants:
            shared.require(score is None, "EXCLUDED_ROW_SCORED")
            result.append(0)
            continue
        if score is None or not isinstance(score, dict) or "error" in score:
            result.append(0)
            continue
        result.append(choose([item.get("id") if isinstance(item, dict) else None for item in variants], score.get("scores")))
    return result


def metrics(records: list[dict], scores: dict) -> dict:
    ev = evaluator()
    chosen = decisions(records, scores)
    unambiguous = [index for index, row in enumerate(records) if not row["ambiguous"]]
    ambiguous = [index for index, row in enumerate(records) if row["ambiguous"]]
    suggestions = [index for index in unambiguous if chosen[index] != 0]
    correct = sum(chosen[index] == records[index]["expectedCandidate"] for index in suggestions)
    return {"rows": len(records), "unambiguousRows": len(unambiguous), "ambiguousRows": len(ambiguous),
        "productionExcludedRows": sum(not row.get("variants") for row in records),
        "suggestions": len(suggestions), "correctSuggestions": correct,
        "suggestionPrecision": ev.rate(correct, len(suggestions)),
        "unambiguousTop1Coverage": ev.rate(correct, len(unambiguous)),
        "unambiguousAbstention": ev.rate(sum(chosen[index] == 0 for index in unambiguous), len(unambiguous)),
        "ambiguousNonSpaceSuggestion": ev.rate(sum(chosen[index] != 0 for index in ambiguous), len(ambiguous)),
        "runtimeErrors": sum("error" in scores.get(row["id"], {}) for row in records),
        "automaticReplacements": 0}


def load_scores(directory: Path, selected: list[dict]) -> tuple[dict, dict]:
    complete = json.loads((directory / "complete.json").read_text())
    require_binding(complete, "SCORES_POLICY")
    shared.require(complete.get("split") in ("calibration", "holdout")
        and complete.get("scope") == f'contextual-{complete["split"]}-scores', "SCORES_SCOPE")
    shared.require(json.loads((directory / "run-input.json").read_text()) ==
        {key: value for key, value in complete.items() if key not in ("scores", "runtimeErrors", "scoresSha256")},
        "SCORES_RECEIPT")
    shared.require(complete["scores"] == complete["requests"] == len(selected)
                   and complete["scoresSha256"] == shared.sha(directory / "scores.jsonl"), "COMPLETE_SCORES")
    _, scores = evaluator().load_cache(directory / "scores.jsonl", selected, complete["identity"])
    shared.require(len(scores) == len(selected), "SCORE_COUNT")
    return complete, scores


def require_backend(calibration: dict, holdout: dict) -> None:
    shared.require(all(calibration.get(key) is not None and calibration.get(key) == holdout.get(key)
                       for key in ("protocol", "runnerSha256", "modelSha256")), "FROZEN_MODEL_IDENTITY")


def load_frozen(path: Path, export_receipt: str) -> dict:
    config = json.loads(path.read_text())
    content = {key: value for key, value in config.items() if key != "configSha256"}
    shared.require(evaluator().digest(content) == config.get("configSha256"), "FROZEN_CONFIG_DIGEST")
    require_binding(config, "FROZEN_POLICY")
    shared.require(config.get("scope") == "contextual-calibrated-total-rule"
        and config.get("thresholdSearchPerformed") is False
        and config.get("exportReceiptSha256") == export_receipt
        and config.get("engineSha256") == shared.sha(ENGINE), "FROZEN_CONTEXTUAL_CONFIG")
    verification_dir = shared.REPO / config["policyVerificationDirectory"]
    load_verification(verification_dir)
    shared.require(shared.sha(verification_dir / "verification.json") == config["policyVerificationSha256"],
                   "FROZEN_VERIFICATION")
    return config


def freeze_run(args) -> None:
    verification_dir = Path(args.policy_verification).resolve(strict=True)
    load_verification(verification_dir)
    export_dir = Path(args.export).resolve(strict=True)
    all_records = load_export(export_dir)
    records = [row for row in all_records if row["split"] == "calibration"]
    selected = requests(all_records, "calibration")
    complete, scores = load_scores(Path(args.scoring).resolve(strict=True), selected)
    export_receipt = shared.sha(export_dir / "provenance.json")
    require_binding(complete, "CALIBRATION_POLICY")
    shared.require(complete.get("split") == "calibration" and complete.get("frozenConfigSha256") is None
        and complete.get("exportReceiptSha256") == export_receipt, "CALIBRATION_IDENTITY")
    output = Path(args.output).resolve()
    shared.require(output.is_relative_to(shared.REPO / "build") and not output.exists(), "FRESH_OUTPUT")
    report = {language: metrics([row for row in records if row["language"] == language], scores)
              for language in ("en", "ru", "es")}
    config = {**policy_binding(), "scope": "contextual-calibrated-total-rule",
        "thresholdSearchPerformed": False,
        "policyVerificationDirectory": str(verification_dir.relative_to(shared.REPO)),
        "policyVerificationSha256": shared.sha(verification_dir / "verification.json"),
        "exportReceiptSha256": export_receipt,
        "calibrationCompleteSha256": shared.sha(Path(args.scoring) / "complete.json"),
        "calibrationScoresSha256": complete["scoresSha256"],
        "modelIdentity": complete["identity"], "calibrationMetrics": report,
        "engineSha256": shared.sha(ENGINE), "qualitySourceSha256": shared.sha(Path(__file__))}
    output.mkdir(parents=True)
    ev = evaluator()
    shared.write_json(output / "config.json", {**config, "configSha256": ev.digest(config)})
    print("Frozen verified production contextual totals and calibration-selected margins; no threshold search.")


def report_run(args) -> None:
    export_dir = Path(args.export).resolve(strict=True)
    all_records = load_export(export_dir)
    records = [row for row in all_records if row["split"] == "holdout"]
    selected = requests(all_records, "holdout")
    complete, scores = load_scores(Path(args.scoring).resolve(strict=True), selected)
    export_receipt = shared.sha(export_dir / "provenance.json")
    config = load_frozen(Path(args.frozen_config), export_receipt)
    shared.require(complete.get("split") == "holdout" and complete["frozenConfigSha256"] == config["configSha256"]
                   and complete.get("exportReceiptSha256") == export_receipt, "FROZEN_CONFIG")
    require_backend(config["modelIdentity"], complete["identity"])
    report = {**policy_binding(), "split": "holdout", "automaticReplacements": 0, "thresholdsFittedOnHoldout": False,
        "languages": {language: metrics([row for row in records if row["language"] == language], scores)
                      for language in ("en", "ru", "es")}}
    output = Path(args.output).resolve()
    shared.require(output.is_relative_to(shared.REPO / "build") and not output.exists(), "FRESH_OUTPUT")
    output.mkdir(parents=True)
    shared.write_json(output / "report.json", report)
    shared.write_json(output / "provenance.json", {**policy_binding(), "scope": "contextual-suggestion-holdout",
        "configSha256": config["configSha256"], "scoresSha256": complete["scoresSha256"],
        "policyVerificationSha256": config["policyVerificationSha256"],
        "exportReceiptSha256": export_receipt,
        "reportSha256": shared.sha(output / "report.json"), "holdoutExecuted": True})
    print("Contextual suggestion holdout complete; no automatic application evaluated.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    verification_parser = commands.add_parser("verify-policy")
    for option in ("output", "java", "gradle-cache"):
        verification_parser.add_argument("--" + option, required=True)
    export_parser = commands.add_parser("export")
    for option in ("output", "java", "gradle-cache"): export_parser.add_argument("--" + option, required=True)
    export_parser.add_argument("--corpus", default=shared.CORPUS)
    score_parser = commands.add_parser("score")
    for option in ("export", "output", "model-config", "runner", "model"):
        score_parser.add_argument("--" + option, required=True)
    score_parser.add_argument("--split", choices=("calibration", "holdout"), required=True)
    score_parser.add_argument("--frozen-config")
    score_parser.add_argument("--limit", type=int)
    score_parser.add_argument("--expected-model-bytes", type=int)
    freeze_parser = commands.add_parser("freeze")
    for option in ("export", "scoring", "output", "policy-verification"):
        freeze_parser.add_argument("--" + option, required=True)
    report_parser = commands.add_parser("report")
    for option in ("export", "scoring", "frozen-config", "output"):
        report_parser.add_argument("--" + option, required=True)
    args = parser.parse_args()
    {"verify-policy": verification_run, "export": export_run, "score": score_run,
     "freeze": freeze_run, "report": report_run}[args.command](args)


if __name__ == "__main__":
    main()
