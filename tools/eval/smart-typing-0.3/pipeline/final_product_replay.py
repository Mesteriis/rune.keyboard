#!/usr/bin/env python3
"""Source-bound fixed-policy spelling replay through the current controller.

Stages are deliberately sequential: export, score-calibration, freeze-policy,
score-holdout, replay-report.  Export and policy freeze never call the model.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
import gzip
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
CORPUS = REPO / "tools/eval/smart-typing-0.3"
ASSETS = REPO / "app/src/main/assets"
HARNESS = HERE / "FinalProductSpellingReplay.kt"
SOURCE_MANIFEST = HERE / "final_product_replay_sources.json"
TOOLCHAIN = REPO / "tools/lexicon/smart-typing-0.3/weighted-qualification/manifests/reproduction-toolchain.json"
DETERMINISTIC_CONFIG = HERE / "qualification-config/deterministic-width-4.json"
COMBINED_CONFIG = HERE / "qualification-config/combined.json"
RUNNER = REPO / "build/smart-typing-0.3/native-current-20260906/rune-score"
MODEL = REPO / "build/smart-typing-0.3/model/rune-text-v1-0.1.0-q4_k_m.gguf"
RUNNER_SHA256 = "bc3f78bdf3ac41009a7603ca5dd6b6c4d5e8d6c2bdcaf3a692cfd95a3b3d2553"
MODEL_SHA256 = "7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4"
MODEL_BYTES = 396704416
SCHEMA = 1
EXPERIMENT = "revealed-data-fixed-policy-reproduction"
LANGUAGES = ("en", "ru", "es")
COHORT_COUNTS = {"typo": 1000, "correct": 700, "protected": 300}
ERROR_CODES = {"INVALID_REQUEST", "INVALID_UTF8", "TOO_MANY_CANDIDATES", "CONTEXT_TOO_LONG",
    "CANCELLED", "TOKENIZE_FAILED", "CONTEXT_CREATE_FAILED", "SCORING_FAILED",
    "INSUFFICIENT_CONTEXT"}
JDK_RUNTIME_INVENTORY = ("bin/java", "release", "lib/libjli.dylib", "lib/modules",
                         "lib/server/libjvm.dylib")


def fail(code: str) -> None:
    raise ValueError(code)


def require(condition: bool, code: str) -> None:
    if not condition:
        fail(code)


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode()


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def sha256(path: Path | str) -> str:
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path: Path, value) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                                allow_nan=False) + "\n")


def write_jsonl(path: Path, values: list[dict]) -> None:
    with path.open("x", encoding="utf-8") as stream:
        for value in values:
            stream.write(canonical(value).decode() + "\n")


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream]


def path_key(path: Path) -> str:
    path = path.resolve(strict=True)
    return str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path)


def resolve_key(key: str) -> Path:
    path = Path(key)
    return path if path.is_absolute() else REPO / path


def verify_bound_files(receipt: dict) -> None:
    files = receipt.get("files") or receipt.get("bindings", {}).get("files")
    require(isinstance(files, dict) and files, "BOUND_FILES_MISSING")
    for key, expected in files.items():
        path = resolve_key(key)
        require(path.is_file() and sha256(path) == expected, f"BOUND_FILE_DRIFT:{key}")


def evaluator():
    spec = importlib.util.spec_from_file_location("final_product_replay_evaluator", CORPUS / "evaluate.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def load_original_spelling_rows() -> tuple[object, list[dict], dict]:
    manifest_path = CORPUS / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    require(set(manifest.get("files", {})) >= {
        "spelling-en.jsonl", "spelling-ru.jsonl", "spelling-es.jsonl", "protected-tokens.jsonl"
    }, "CORPUS_MANIFEST_FILES")
    for name, expected in manifest["files"].items():
        require(sha256(CORPUS / name) == expected, f"CORPUS_FILE_DRIFT:{name}")
    ev = evaluator()
    all_rows = ev.load_corpus(CORPUS)
    ev.validate(all_rows)
    rows = [row for row in all_rows if row["task"] == "spelling"]
    require(len(rows) == 12000 and len({row["id"] for row in rows}) == 12000, "SPELLING_ROW_IDENTITIES")
    actual = Counter((row["split"], row["language"], row["cohort"]) for row in rows)
    expected = Counter({(split, language, cohort): count
                        for split in ("calibration", "holdout")
                        for language in LANGUAGES for cohort, count in COHORT_COUNTS.items()})
    require(actual == expected, "SPELLING_PARTITIONS")
    return ev, rows, manifest


def asset_paths() -> list[Path]:
    paths = []
    for language in LANGUAGES:
        paths += [ASSETS / f"smarttyping/lexicon/{language}.trie",
                  ASSETS / f"smarttyping/lexicon/{language}.trie.lengths",
                  ASSETS / f"smarttyping/lexicon/frequency/{language}.ranks",
                  ASSETS / f"smarttyping/lexicon/case/{language}.case"]
    require(len(paths) == 12 and all(path.is_file() for path in paths), "TWELVE_PACKAGED_ASSETS")
    return paths


def final_product_sources() -> list[Path]:
    manifest = json.loads(SOURCE_MANIFEST.read_text())
    require(manifest.get("schemaVersion") == 1 and isinstance(manifest.get("sources"), list),
            "SOURCE_MANIFEST")
    paths = [(REPO / value).resolve(strict=True) for value in manifest["sources"]]
    require(len(paths) > 20 and len(set(paths)) == len(paths) and all(path.is_relative_to(REPO) for path in paths),
            "SOURCE_MANIFEST_PATHS")
    require(all("/results/" not in str(path) for path in paths), "SOURCE_MANIFEST_ARCHIVE")
    return paths


def compile_inputs(java: Path) -> tuple[list[Path], list[Path], Path]:
    source_paths = final_product_sources()
    diagnostics = REPO / "app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/diagnostics/TypingDiagnostics.kt"
    if diagnostics not in source_paths:
        source_paths.append(diagnostics)
    source_paths.append(HARNESS)
    require(all(path.is_file() for path in source_paths), "COMPILE_SOURCE_MISSING")
    manifest = json.loads(TOOLCHAIN.read_text())
    jars = []
    cache = Path.home() / ".gradle/caches/modules-2/files-2.1"
    for item in manifest["jars"]:
        found = list((cache / item["group"] / item["artifact"] / item["version"]).glob("*/*.jar"))
        require(len(found) == 1 and sha256(found[0]) == item["sha256"], "PINNED_KOTLIN_CACHE")
        jars.append(found[0])
    version = subprocess.run([str(java), "-version"], capture_output=True, timeout=15, check=True)
    require(b'version "17.' in version.stderr, "JAVA_17_REQUIRED")
    android_home = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    require(android_home is not None, "ANDROID_HOME_MISSING")
    android = Path(android_home) / "platforms/android-37.0/android.jar"
    require(android.is_file(), "ANDROID_COMPILE_STUB_MISSING")
    return source_paths, jars, android


def immutable_bindings(java: Path, sources: list[Path], jars: list[Path], android: Path,
                       rows: list[dict]) -> dict:
    corpus_manifest = json.loads((CORPUS / "manifest.json").read_text())
    java_runtime = java_runtime_binding(java)
    java_home = Path(java_runtime["home"])
    java_runtime_files = [java_home / relative for relative in JDK_RUNTIME_INVENTORY]
    fixed = [CORPUS / "manifest.json", *(CORPUS / name for name in corpus_manifest["files"]),
             CORPUS / "evaluate.py", Path(__file__), SOURCE_MANIFEST, TOOLCHAIN,
             DETERMINISTIC_CONFIG, COMBINED_CONFIG, RUNNER, MODEL, *java_runtime_files, android,
             *asset_paths(), *jars, *sources]
    files = {path_key(path): sha256(path) for path in fixed}
    require(files[path_key(RUNNER)] == RUNNER_SHA256, "RUNNER_IDENTITY")
    require(files[path_key(MODEL)] == MODEL_SHA256 and MODEL.stat().st_size == MODEL_BYTES,
            "MODEL_IDENTITY")
    current = (REPO / "app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/correction/SpellingQualification.kt").read_text()
    settings = (REPO / "app/src/main/java/io/github/mesteriis/rune/keyboard/settings/KeyboardSettings.kt").read_text()
    calibrated = (REPO / "app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/correction/CalibratedSpellingPolicy.kt").read_text()
    require("SpellingSource.GENERAL_LOCAL -> false" in current and
            "SpellingSource.MODEL -> ModelRuntimeQualification.CURRENT" in current and
            "QualificationArtifacts.allowsLocal(language, QualificationArtifacts.local())" in current,
            "CURRENT_QUALIFICATION_CONTRACT")
    require("val DEFAULT = KeyboardSettings(" in settings and
            "autocorrectionMode: AutocorrectionMode = AutocorrectionMode.HIGH_CONFIDENCE" in settings,
            "DEFAULT_SETTINGS_CONTRACT")
    require("const val MAXIMUM_ALTERNATIVES = 3" in calibrated, "MAXIMUM_ALTERNATIVES_CONTRACT")
    return {
        "files": files,
        "rowsSha256": digest(rows),
        "rowIdentitySha256": digest([{"id": row["id"], "split": row["split"]} for row in rows]),
        "assets": {path_key(path): sha256(path) for path in asset_paths()},
        "runner": {"path": path_key(RUNNER), "sha256": RUNNER_SHA256},
        "model": {"path": path_key(MODEL), "bytes": MODEL_BYTES, "sha256": MODEL_SHA256},
        "javaRuntime": java_runtime,
        "qualification": "SpellingQualification.CURRENT",
        "settings": "KeyboardSettings.DEFAULT",
        "maximumAlternatives": 3,
        "existingNumericalObservationsReused": [],
    }


def java_runtime_binding(java: Path) -> dict:
    executable = Path(java).resolve(strict=True)
    java_home = executable.parents[1]
    require(executable == java_home / "bin/java", "JDK_JAVA_LAYOUT")
    files = {relative: sha256(java_home / relative) for relative in JDK_RUNTIME_INVENTORY
             if (java_home / relative).is_file()}
    require(tuple(files) == JDK_RUNTIME_INVENTORY, "JDK_RUNTIME_INVENTORY")
    return {"schemaVersion": 1, "home": str(java_home), "executable": path_key(executable),
        "inventory": list(JDK_RUNTIME_INVENTORY), "files": files,
        "distributionSha256": digest(files)}


def select_bound_java(export_receipt: dict, requested: Path | None = None) -> Path:
    runtime = export_receipt.get("bindings", {}).get("javaRuntime", {})
    require(set(runtime) == {"schemaVersion", "home", "executable", "inventory", "files",
                             "distributionSha256"}
            and runtime["schemaVersion"] == 1
            and tuple(runtime["inventory"]) == JDK_RUNTIME_INVENTORY
            and set(runtime["files"]) == set(JDK_RUNTIME_INVENTORY), "BOUND_JAVA_RUNTIME")
    home = Path(runtime["home"]).resolve(strict=True)
    bound = resolve_key(runtime["executable"]).resolve(strict=True)
    require(bound == home / "bin/java", "BOUND_JAVA_EXECUTABLE")
    if requested is not None:
        require(Path(requested).resolve(strict=True) == bound, "ALTERNATE_JAVA_RUNTIME")
    for relative, expected in runtime["files"].items():
        path = (home / relative).resolve(strict=True)
        require(path.is_relative_to(home) and sha256(path) == expected,
                f"BOUND_JAVA_DISTRIBUTION_DRIFT:{relative}")
    require(digest(runtime["files"]) == runtime["distributionSha256"],
            "BOUND_JAVA_DISTRIBUTION_IDENTITY")
    return bound


def runner_request(item: dict) -> dict:
    return {"id": item["id"], "prefix": item["prefix"], "candidates": item["continuations"]}


def request_manifest(observations: list[dict], split: str) -> list[dict]:
    selected = []
    for observation in observations:
        if observation["split"] != split or observation.get("actualModelRequest") is None:
            continue
        request = observation["actualModelRequest"]
        selected.append({"id": observation["id"], "split": split,
            "sessionId": request["sessionId"], "revision": request["revision"],
            "requestId": request["requestId"], "language": observation["language"],
            "prefix": request["prefix"], "candidateIds": request["candidateIds"],
            "continuations": request["continuations"]})
    require(len(selected) == len({item["id"] for item in selected}), "DUPLICATE_REQUEST_IDS")
    return selected


def cache_identity_for_requests(requests: list[dict], runner_sha: str, model_sha: str,
                                source_sha: str, config_sha: str) -> dict:
    return {"protocol": "rune-score-jsonl-v1", "requestsSha256": digest(requests),
        "payloadSha256": digest([runner_request(item) for item in requests]),
        "runnerSha256": runner_sha, "modelSha256": model_sha,
        "sourceSha256": source_sha, "configSha256": config_sha}


def validate_response(request: dict, response: dict) -> None:
    require(type(response) is dict and response.get("id") == request["id"], "RESPONSE_ID")
    if "error" in response:
        require(set(response) == {"id", "error"} and response["error"] in ERROR_CODES, "ERROR_RECORD")
        return
    require(set(response) == {"id", "scores", "durationMillis"}
            and isinstance(response["scores"], list), "RESPONSE_SHAPE")
    duration = response["durationMillis"]
    require(type(duration) in (int, float) and math.isfinite(duration) and duration >= 0,
            "INVALID_DURATION")
    require(len(response["scores"]) == len(request["candidateIds"]), "RESPONSE_CANDIDATE_COUNT")
    require(all(type(score) is dict and
                set(score) == {"id", "sumLogProbability", "scoredTokenCount"}
                for score in response["scores"]), "RESPONSE_SCORE_SHAPE")
    require(all(type(score["id"]) is int for score in response["scores"])
            and [score["id"] for score in response["scores"]] == request["candidateIds"],
            "RESPONSE_CANDIDATE_ORDER")
    for score in response["scores"]:
        value, count = score["sumLogProbability"], score["scoredTokenCount"]
        require(type(value) in (int, float) and math.isfinite(value) and value <= 0,
                "INVALID_NUMERIC_SCORE")
        require(type(count) is int and 1 <= count <= 255, "INVALID_TOKEN_COUNT")


def validate_complete_cache(requests: list[dict], header: dict, records: list[dict],
                            identity: dict) -> dict[str, dict]:
    require(header == {"cacheIdentity": identity}, "CACHE_IDENTITY")
    by_request = {item["id"]: item for item in requests}
    require(len(by_request) == len(requests), "DUPLICATE_REQUEST_MANIFEST")
    by_id = {}
    for record in records:
        identifier = record.get("id") if isinstance(record, dict) else None
        require(identifier in by_request and identifier not in by_id, "DUPLICATE_OR_FOREIGN_RESPONSE")
        validate_response(by_request[identifier], record)
        by_id[identifier] = record
    require(set(by_id) == set(by_request), "MISSING_RESPONSES")
    return by_id


def delivery_for(request: dict, response: dict) -> dict:
    common = {key: request[key] for key in ("id", "split", "language", "sessionId", "revision",
                                             "requestId", "prefix", "candidateIds", "continuations")}
    if "error" in response:
        return {**common, "code": "UNAVAILABLE", "error": response["error"], "scores": []}
    return {**common, "code": "OK", "durationMillis": response["durationMillis"],
            "scores": response["scores"]}


def delivery_tsv_line(item: dict) -> str:
    numeric = ";".join(f'{score["id"]},{score["sumLogProbability"]},{score["scoredTokenCount"]}'
                       for score in item["scores"])
    continuations = ",".join(base64.b64encode(value.encode()).decode()
                             for value in item["continuations"])
    return "\t".join([base64.b64encode(item["id"].encode()).decode(), item["split"],
        item["language"], str(item["sessionId"]), str(item["revision"]),
        str(item["requestId"]), base64.b64encode(item["prefix"].encode()).decode(),
        ",".join(map(str, item["candidateIds"])), continuations, item["code"], numeric or "NONE"])


def expected_score_identity(export_receipt: dict, requests: list[dict]) -> dict:
    return cache_identity_for_requests(requests, RUNNER_SHA256, MODEL_SHA256,
        export_receipt["sourceFreezeSha256"], sha256(COMBINED_CONFIG))


def score_complete_receipt(split: str, requests: list[dict], records: list[dict], identity: dict,
                           scores_sha: str, export_receipt_sha: str,
                           policy_freeze_sha: str | None) -> dict:
    return {"schemaVersion": SCHEMA, "complete": True, "split": split,
        "experiment": EXPERIMENT, "requests": len(requests), "responses": len(records),
        "errors": sum("error" in item for item in records), "identity": identity,
        "scoresSha256": scores_sha, "exportReceiptSha256": export_receipt_sha,
        "policyFreezeSha256": policy_freeze_sha, "retries": 0,
        "thresholdFittingPerformed": False}


def admit_score_stage(root: Path, split: str, export_receipt: dict,
                      policy_freeze_sha: str | None = None) -> tuple[dict, dict[str, dict]]:
    require(split in ("calibration", "holdout"), "SCORE_SPLIT")
    requests = read_jsonl(root / f"requests-{split}.jsonl")
    require(requests and all(item.get("split") == split for item in requests), "REQUEST_SPLIT")
    expected_identity = expected_score_identity(export_receipt, requests)
    complete_path = root / f"{split}-scores/complete.json"
    cache_path = root / f"{split}-scores/scores.jsonl"
    complete = json.loads(complete_path.read_text())
    cache = read_jsonl(cache_path)
    require(bool(cache), "EMPTY_SCORE_CACHE")
    scores = validate_complete_cache(requests, cache[0], cache[1:], expected_identity)
    expected_complete = score_complete_receipt(split, requests, cache[1:], expected_identity,
        sha256(cache_path), sha256(root / "export-receipt.json"), policy_freeze_sha)
    require(complete == expected_complete, f"SCORE_COMPLETE_RECEIPT:{split}")
    return complete, scores


def policy_freeze_receipt(root: Path, calibration_complete: dict) -> dict:
    return {"schemaVersion": SCHEMA, "complete": True, "experiment": EXPERIMENT,
        "stage": "unchanged-policy-freeze", "policyChanged": False,
        "thresholdFittingPerformed": False, "holdoutObservedForSelection": False,
        "productionPolicy": {"qualification": "SpellingQualification.CURRENT",
            "settings": "KeyboardSettings.DEFAULT", "maximumAlternatives": 3},
        "combinedConfigSha256": sha256(COMBINED_CONFIG),
        "deterministicConfigSha256": sha256(DETERMINISTIC_CONFIG),
        "calibrationCompleteSha256": sha256(root / "calibration-scores/complete.json"),
        "calibrationScoresSha256": calibration_complete["scoresSha256"],
        "exportReceiptSha256": sha256(root / "export-receipt.json")}


def admit_policy_freeze(root: Path, export_receipt: dict) -> dict:
    calibration_complete, _ = admit_score_stage(root, "calibration", export_receipt)
    expected = policy_freeze_receipt(root, calibration_complete)
    actual = json.loads((root / "policy-freeze.json").read_text())
    require(actual == expected, "POLICY_FREEZE_RECEIPT")
    return actual


def fixed_policy_gates(correct: int, changed: int, false_changes: int, negative: int,
                       spelling_changes: int, mechanical_changes: int = 0,
                       original_retained: int | None = None, total_rows: int | None = None,
                       undo_exact: int | None = None, undo_total: int | None = None) -> dict:
    del mechanical_changes
    precision = changed > 0 and correct * 100 >= changed * 95
    false_change = negative > 0 and false_changes * 200 <= negative
    volume = spelling_changes >= 300
    original = total_rows is None or original_retained == total_rows
    undo = (undo_total if undo_total is not None else total_rows) is None or undo_exact == (
        undo_total if undo_total is not None else total_rows)
    return {"precisionPass": precision, "falseChangePass": false_change,
        "volumePass": volume, "originalAlwaysAvailablePass": original,
        "exactImmediateUndoPass": undo,
        "allPass": precision and false_change and volume and original and undo}


def product_policy_gates(metrics: dict) -> dict:
    ordinary = metrics["ordinarySpelling"]
    aggregate = metrics["aggregateFinalText"]["falseChanges"]
    ordinary_false = ordinary["falseChanges"]
    gates = fixed_policy_gates(ordinary["correctChanges"], ordinary["automaticChanges"],
        aggregate["numerator"], aggregate["denominator"], ordinary["automaticChanges"],
        metrics["mechanical"]["changedRows"], metrics["originalRetention"]["numerator"],
        metrics["originalRetention"]["denominator"], metrics["exactUndo"]["numerator"],
        metrics["exactUndo"]["denominator"])
    ordinary_pass = (ordinary_false["denominator"] > 0 and
        ordinary_false["numerator"] * 200 <= ordinary_false["denominator"])
    gates["ordinarySpellingFalseChangePass"] = ordinary_pass
    gates["aggregateFalseChangePass"] = gates.pop("falseChangePass")
    gates["allPass"] = gates["allPass"] and ordinary_pass
    return gates


def holdout_release_approved(languages: dict) -> bool:
    return set(languages) == set(LANGUAGES) and all(
        values.get("fixedPointPolicyGates", {}).get("allPass") is True
        for values in languages.values())


def original_retention(observation: dict, corpus_token: str) -> dict:
    actual = observation.get("actualOriginal")
    originals = [item for item in observation.get("candidateView", {}).get("candidates", [])
                 if item.get("role") == "ORIGINAL"]
    applicable = type(actual) is str and bool(actual)
    retained = (len(originals) == 1 and originals[0].get("text") == actual and
                bool(originals[0].get("id"))) if applicable else None
    return {"applicable": applicable, "retained": retained, "actualOriginal": actual,
            "corpusTokenMatchesActualOriginal": corpus_token == actual}


def rate(numerator: int, denominator: int) -> dict:
    if denominator == 0:
        interval = value = None
    else:
        value = numerator / denominator
        z = 1.959963984540054
        center = (value + z * z / (2 * denominator)) / (1 + z * z / denominator)
        radius = z * math.sqrt(value * (1 - value) / denominator +
                               z * z / (4 * denominator * denominator)) / (1 + z * z / denominator)
        interval = [max(0.0, center - radius), min(1.0, center + radius)]
    return {"numerator": numerator, "denominator": denominator, "value": value,
            "wilson95RowDescriptive": interval}


def summarize_rows(rows: list[dict]) -> dict:
    def one(items: list[dict]) -> dict:
        evs = [item["evaluation"] for item in items]
        spelling = [ev for ev in evs if ev["spellingAutoEdit"]]
        negatives = [item for item in items if item["input"]["cohort"] != "typo"]
        false_spelling = sum(item["evaluation"]["spellingAutoEdit"] for item in negatives)
        correct = sum(ev["correctFinalReplacement"] for ev in spelling)
        def change_metrics(key: str, count_name: str) -> dict:
            count = sum(ev[key] for ev in evs)
            return {count_name: count,
                "falseChanges": rate(sum(item["evaluation"][key] for item in negatives), len(negatives)),
                "falseChangesByCohort": {cohort: rate(
                    sum(item["evaluation"][key] for item in items if item["input"]["cohort"] == cohort),
                    sum(item["input"]["cohort"] == cohort for item in items))
                    for cohort in ("correct", "protected")}}
        cohorts = {}
        for cohort in ("typo", "correct", "protected"):
            cohort_items = [item for item in items if item["input"]["cohort"] == cohort]
            cohort_changes = sum(item["evaluation"]["spellingAutoEdit"] for item in cohort_items)
            cohorts[cohort] = {"rows": len(cohort_items), "spellingAutomaticChanges": cohort_changes,
                "coverage": rate(cohort_changes, len(cohort_items)),
                "abstention": rate(len(cohort_items)-cohort_changes, len(cohort_items))}
        automatic = [ev for ev in evs if ev["spellingAutoEdit"] or ev["canonicalAutoEdit"] or ev["mechanicalChange"]]
        return {"rows": len(items),
            "cohorts": cohorts,
            "ordinarySpelling": {"automaticChanges": len(spelling),
                "correctChanges": correct, "precision": rate(correct, len(spelling)),
                "falseChanges": rate(false_spelling, len(negatives)),
                "falseChangesByCohort": {cohort: rate(
                    sum(item["evaluation"]["spellingAutoEdit"] for item in items
                        if item["input"]["cohort"] == cohort),
                    sum(item["input"]["cohort"] == cohort for item in items))
                    for cohort in ("correct", "protected")}},
            "canonical": change_metrics("canonicalAutoEdit", "automaticChanges"),
            "mechanical": change_metrics("mechanicalChange", "changedRows"),
            "aggregateFinalText": change_metrics("fullFinalTextChanged", "changedRows"),
            "candidateRecall": rate(sum(ev["candidateRecall"] is True for ev in evs),
                                    sum(ev["candidateRecall"] is not None for ev in evs)),
            "originalRetention": rate(sum(ev["originalRetained"] is True for ev in evs
                                         if ev.get("originalApplicable", True)),
                                     sum(ev.get("originalApplicable", True) for ev in evs)),
            "exactUndo": rate(sum(ev["undoExact"] for ev in automatic), len(automatic)),
            "coverage": rate(len(spelling), len(items)), "abstention": rate(len(items)-len(spelling), len(items)),
            "model": {"requests": sum(ev["modelRequested"] for ev in evs),
                "errors": sum(ev["modelError"] for ev in evs),
                "refusals": sum(ev["modelRefused"] for ev in evs),
                "noRequests": sum(not ev["modelRequested"] for ev in evs)}}
    return {"languages": {lang: one([item for item in rows if item["input"]["language"] == lang])
                          for lang in LANGUAGES}, "overall": one(rows)}


def compile_harness(root: Path, java: Path, sources: list[Path], jars: list[Path], android: Path) -> tuple[Path, list[str]]:
    jar = root / "final-product-spelling-replay.jar"
    command = [str(java), "-XX:ActiveProcessorCount=2", "-Xmx768m", "-cp", os.pathsep.join(map(str, jars)),
        "org.jetbrains.kotlin.cli.jvm.K2JVMCompiler", "-no-stdlib", "-no-reflect", "-jvm-target", "17",
        "-classpath", os.pathsep.join(map(str, [jars[1], jars[2], android])), "-d", str(jar),
        *map(str, sources)]
    with (root / "compile.log").open("xb") as log:
        subprocess.run(command, stdout=log, stderr=log, timeout=180, check=True)
    return jar, command


def run_harness(root: Path, java: Path, jars: list[Path], android: Path, jar: Path,
                inputs: Path, output: Path, mode: str, replies: Path | None = None,
                target_split: str = "all") -> list[str]:
    classpath = os.pathsep.join(map(str, [jar, jars[1], jars[2], android]))
    command = [str(java), "-XX:ActiveProcessorCount=2", "-Xmx768m", "-cp", classpath,
        "io.github.mesteriis.rune.keyboard.smarttyping.session.FinalProductSpellingReplay",
        str(inputs), str(ASSETS), mode, target_split]
    if replies is not None:
        command.append(str(replies))
    with output.open("xb") as data, (root / f"{output.stem}.log").open("xb") as log:
        subprocess.run(command, stdout=data, stderr=log, timeout=1200, check=True)
    return command


def export_stage(args) -> None:
    root = Path(args.root).resolve()
    require(root.is_relative_to(REPO / "build") and not root.exists(), "FRESH_BUILD_ROOT_REQUIRED")
    java = Path(args.java).resolve(strict=True)
    ev, rows, manifest = load_original_spelling_rows()
    sources, jars, android = compile_inputs(java)
    bindings = immutable_bindings(java, sources, jars, android, rows)
    root.mkdir(parents=True)
    write_json(root / "source-freeze.json", {"schemaVersion": SCHEMA, "experiment": EXPERIMENT,
        "stage": "export-freeze", "bindings": bindings, "corpusManifest": manifest,
        "thresholdFittingPerformed": False, "modelCalls": 0})
    write_jsonl(root / "rows.jsonl", rows)
    inputs = root / "inputs.tsv"
    with inputs.open("x", encoding="ascii") as stream:
        for index, row in enumerate(rows):
            enc = lambda value: base64.b64encode(value.encode()).decode("ascii")
            stream.write("\t".join([str(index), enc(row["id"]), row["split"], row["language"],
                                     enc(row["prefix"]), enc(row["typed"])]) + "\n")
    jar, compile_command = compile_harness(root, java, sources, jars, android)
    observations_path = root / "observations.jsonl"
    execute_command = run_harness(root, java, jars, android, jar, inputs, observations_path, "export")
    observations = read_jsonl(observations_path)
    require(len(observations) == len(rows) and [item["id"] for item in observations] == [row["id"] for row in rows],
            "EXPORT_ROW_COMPLETENESS")
    require(all(item["status"] == "EXPORTED" and item["maximumAlternatives"] == 3
                and item["autocorrectionMode"] == "HIGH_CONFIDENCE"
                and item["currentQualificationWithModel"] is True
                and item["currentQualificationWithoutModel"] is False for item in observations),
            "CURRENT_POLICY_EXPORT")
    requests = {}
    for split in ("calibration", "holdout"):
        split_rows = [row for row in rows if row["split"] == split]
        require(len(split_rows) == 6000, "SPLIT_ROW_COUNT")
        selected = request_manifest(observations, split)
        requests[split] = selected
        write_jsonl(root / f"requests-{split}.jsonl", selected)
        no_request_ids = [item["id"] for item in observations
                          if item["split"] == split and item.get("actualModelRequest") is None]
        write_jsonl(root / f"no-requests-{split}.jsonl", [{"id": value, "split": split} for value in no_request_ids])
    verify_bound_files({"files": bindings["files"]})
    artifacts = {path.name: sha256(path) for path in root.iterdir() if path.is_file()}
    write_json(root / "export-receipt.json", {"schemaVersion": SCHEMA, "experiment": EXPERIMENT,
        "stage": "export-freeze", "complete": True, "rows": len(rows),
        "splitRows": {"calibration": 6000, "holdout": 6000},
        "requests": {split: len(values) for split, values in requests.items()},
        "noRequests": {split: 6000-len(values) for split, values in requests.items()},
        "fragmentRequests": {split: sum(item.get("requestToken") not in (None, item["typed"])
            for item in observations if item["split"] == split) for split in ("calibration", "holdout")},
        "bindings": bindings, "sourceFreezeSha256": sha256(root / "source-freeze.json"),
        "artifacts": artifacts, "commands": {"compile": compile_command, "export": execute_command},
        "labelsEnteredHarnessOrModelRequests": False, "labelsRetainedForPythonOnlyJoin": True,
        "thresholdFittingPerformed": False,
        "modelCalls": 0, "freshScoringRequiredForEveryRequest": True,
        "expectedHoldoutRequestCountUsedAsFilter": False})
    print(json.dumps({"rows": 12000, "requests": {k: len(v) for k, v in requests.items()},
                      "noRequests": {k: 6000-len(v) for k, v in requests.items()}, "modelCalls": 0}, indent=2))


def load_export(root: Path) -> dict:
    receipt = json.loads((root / "export-receipt.json").read_text())
    require(receipt.get("complete") is True and receipt.get("experiment") == EXPERIMENT
            and receipt.get("modelCalls") == 0, "EXPORT_RECEIPT")
    verify_bound_files(receipt)
    require(sha256(root / "source-freeze.json") == receipt["sourceFreezeSha256"], "SOURCE_FREEZE_DRIFT")
    for name, expected in receipt["artifacts"].items():
        require(sha256(root / name) == expected, f"EXPORT_ARTIFACT_DRIFT:{name}")
    return receipt


def score_stage(args, split: str) -> None:
    root = Path(args.root).resolve(strict=True)
    export_receipt = load_export(root)
    policy_freeze_sha = None
    if split == "holdout":
        admit_policy_freeze(root, export_receipt)
        policy_freeze_sha = sha256(root / "policy-freeze.json")
    requests = read_jsonl(root / f"requests-{split}.jsonl")
    identity = expected_score_identity(export_receipt, requests)
    output = root / f"{split}-scores"
    output.mkdir(exist_ok=False)
    cache = output / "scores.jsonl"
    with cache.open("x", encoding="utf-8") as stream:
        stream.write(canonical({"cacheIdentity": identity}).decode() + "\n")
    process = subprocess.Popen([str(RUNNER), str(MODEL)], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)
    selector = selectors.DefaultSelector(); selector.register(process.stdout, selectors.EVENT_READ)
    pending = bytearray()
    records = []
    try:
        with cache.open("a", encoding="utf-8") as stream:
            for ordinal, request in enumerate(requests, 1):
                process.stdin.write(canonical(runner_request(request)) + b"\n"); process.stdin.flush()
                deadline = time.monotonic() + args.timeout
                while b"\n" not in pending:
                    wait = deadline-time.monotonic()
                    if wait <= 0 or not selector.select(wait):
                        raise TimeoutError(f"runner timeout at {request['id']}")
                    block = os.read(process.stdout.fileno(), 65536)
                    require(bool(block), f"RUNNER_CLOSED:{request['id']}")
                    pending.extend(block); require(len(pending) <= 65536, "RUNNER_RESPONSE_BOUND")
                line, _, tail = pending.partition(b"\n"); pending = bytearray(tail)
                response = json.loads(line); validate_response(request, response)
                stream.write(canonical(response).decode()+"\n"); stream.flush(); records.append(response)
                if ordinal % 100 == 0: print(f"scored {ordinal}/{len(requests)}", file=sys.stderr, flush=True)
    finally:
        selector.close()
        if process.stdin: process.stdin.close()
        if process.poll() is None: process.terminate()
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired: process.kill(); process.wait()
        if process.stdout: process.stdout.close()
    validate_complete_cache(requests, {"cacheIdentity": identity}, records, identity)
    verify_bound_files(export_receipt)
    write_json(output / "complete.json", score_complete_receipt(split, requests, records, identity,
        sha256(cache), sha256(root / "export-receipt.json"), policy_freeze_sha))


def freeze_policy(args) -> None:
    root = Path(args.root).resolve(strict=True); export = load_export(root)
    complete, _ = admit_score_stage(root, "calibration", export)
    verify_bound_files(export)
    write_json(root / "policy-freeze.json", policy_freeze_receipt(root, complete))


def replay_report(args) -> None:
    # The model-free export is the review boundary. This stage is implemented for
    # the subsequent authorized execution and refuses anything but two complete caches.
    root = Path(args.root).resolve(strict=True); export = load_export(root)
    freeze_path = root / "policy-freeze.json"
    freeze = admit_policy_freeze(root, export)
    java = select_bound_java(export)
    _, jars, android = compile_inputs(java)
    all_evidence = []
    for split in ("calibration", "holdout"):
        requests = read_jsonl(root / f"requests-{split}.jsonl")
        _, scores = admit_score_stage(root, split, export,
            sha256(freeze_path) if split == "holdout" else None)
        deliveries = [delivery_for(request, scores[request["id"]]) for request in requests]
        delivery_path = root / f"deliveries-{split}.jsonl"; write_jsonl(delivery_path, deliveries)
        # A TSV adapter keeps JSON and expected labels out of Kotlin.
        tsv = root / f"deliveries-{split}.tsv"
        with tsv.open("x", encoding="ascii") as stream:
            for item in deliveries:
                stream.write(delivery_tsv_line(item) + "\n")
        for mode in ("ready", "unavailable"):
            out = root / f"replay-{split}-{mode}.jsonl"
            run_harness(root, java, jars, android,
                root / "final-product-spelling-replay.jar", root / "inputs.tsv", out, mode,
                tsv if mode == "ready" else None, split)
    verify_bound_files(export)
    # Join/evaluation is intentionally strict and label-bearing only in Python.
    _, rows, _ = load_original_spelling_rows(); by_id = {row["id"]: row for row in rows}
    for split in ("calibration", "holdout"):
        modes = {mode: {item["id"]: item for item in read_jsonl(root / f"replay-{split}-{mode}.jsonl")
                        if item["split"] == split} for mode in ("ready", "unavailable")}
        expected_ids = {row["id"] for row in rows if row["split"] == split}
        require(all(set(values) == expected_ids for values in modes.values()), "REPLAY_ROWS")
        for mode, observations in modes.items():
            for identifier, observation in observations.items():
                row = by_id[identifier]
                require(observation["status"] == "COMPLETE", f"REPLAY_ROW_ERROR:{identifier}:{mode}")
                after = observation["afterBoundary"]["text"]
                raw = (row["prefix"] + " " if row["prefix"] else "") + row["typed"] + " "
                expected = (row["prefix"] + " " if row["prefix"] else "") + row.get("expectedSpelling", row["typed"]) + " "
                auto = observation.get("autoEdit"); generation = (auto or {}).get("correctionGeneration")
                canonical = bool(generation and any(item["kind"] == "CANONICAL_CASE"
                    for item in generation["alternatives"]))
                spelling = bool(auto and generation and not canonical)
                original = original_retention(observation, row["typed"])
                all_evidence.append({"input": row, "split": split, "mode": mode, "observation": observation,
                    "evaluation": {"modelRequested": observation.get("actualModelRequest") is not None,
                        "modelError": observation.get("modelAdmission") == "MATCHED_SCORING_ERROR",
                        "modelRefused": str(observation.get("modelAdmission", "")).startswith("REFUSED"),
                        "originalApplicable": original["applicable"],
                        "originalRetained": original["retained"],
                        "actualOriginal": original["actualOriginal"],
                        "corpusTokenMatchesActualOriginal": original["corpusTokenMatchesActualOriginal"],
                        "candidateRecall": any(item["text"] == row.get("expectedSpelling") for item in
                            observation.get("actualRequestGeneration", {}).get("alternatives", []))
                            if row["cohort"] == "typo" else None,
                        "spellingAutoEdit": spelling, "canonicalAutoEdit": bool(auto) and canonical,
                        "mechanicalChange": observation["inputChangedByTyping"] or (bool(auto) and generation is None),
                        "fullFinalTextChanged": after != raw,
                        "correctFinalReplacement": spelling and not row["noAuto"] and after == expected,
                        "undoExact": observation["restoredBeforeBoundaryExactly"]}})
    ready_holdout = [item for item in all_evidence if item["split"] == "holdout" and item["mode"] == "ready"]
    unavailable_holdout = [item for item in all_evidence if item["split"] == "holdout" and item["mode"] == "unavailable"]
    ready_calibration = [item for item in all_evidence if item["split"] == "calibration" and item["mode"] == "ready"]
    unavailable_calibration = [item for item in all_evidence if item["split"] == "calibration" and item["mode"] == "unavailable"]
    summary = summarize_rows(ready_holdout)
    unavailable_summary = summarize_rows(unavailable_holdout)
    for language, values in summary["languages"].items():
        values["fixedPointPolicyGates"] = product_policy_gates(values)
    require(all(item["model"]["refusals"] == 0 for item in summary["languages"].values()), "MODEL_REFUSALS")
    require(all(item["ordinarySpelling"]["automaticChanges"] == 0
                for item in unavailable_summary["languages"].values()), "UNQUALIFIED_DETERMINISTIC_AUTO_REPLACE")
    write_jsonl(root / "row-evidence.jsonl", all_evidence)
    write_json(root / "report.json", {"schemaVersion": SCHEMA, "experiment": EXPERIMENT,
        "releaseApproved": holdout_release_approved(summary["languages"]),
        "thresholdFittingPerformed": False, "modelResponsesMissing": 0,
        "calibrationModelReady": summarize_rows(ready_calibration),
        "calibrationModelUnavailable": summarize_rows(unavailable_calibration),
        "holdoutModelReady": summary, "holdoutModelUnavailable": unavailable_summary,
        "limits": ["Source-bound fixed-policy reproduction from a clean checkout.",
            "Host JVM BreakIterator and independent editor; phone timing and asynchronous availability are separate.",
            "Wilson intervals are descriptive row intervals; point integer ratios decide gates."]})


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="stage", required=True)
    export = sub.add_parser("export"); export.add_argument("--root", required=True)
    export.add_argument("--java", default="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/java")
    for name in ("score-calibration", "score-holdout"):
        score = sub.add_parser(name); score.add_argument("--root", required=True); score.add_argument("--timeout", type=float, default=60)
    freeze = sub.add_parser("freeze-policy"); freeze.add_argument("--root", required=True)
    report = sub.add_parser("replay-report"); report.add_argument("--root", required=True)
    return result


def main() -> None:
    args = parser().parse_args()
    if args.stage == "export": export_stage(args)
    elif args.stage == "score-calibration": score_stage(args, "calibration")
    elif args.stage == "freeze-policy": freeze_policy(args)
    elif args.stage == "score-holdout": score_stage(args, "holdout")
    else: replay_report(args)


if __name__ == "__main__":
    main()
