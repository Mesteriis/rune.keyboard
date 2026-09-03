#!/usr/bin/env python3
"""Export actual production candidates for frozen spelling holdout rows only."""
from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import os
from pathlib import Path
import subprocess

import export_calibration as calibration


HERE = Path(__file__).resolve().parent


def evaluator():
    spec = importlib.util.spec_from_file_location("product_holdout_evaluator", calibration.CORPUS / "evaluate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verified_configs(combined_path: Path, deterministic_path: Path, calibration_export: Path) -> tuple[dict, dict, dict]:
    ev = evaluator()
    combined = json.loads(combined_path.read_text())
    deterministic = json.loads(deterministic_path.read_text())
    for value, scope in ((combined, "combined-calibration-only"),
                         (deterministic, "deterministic-calibration-only")):
        content = {k: v for k, v in value.items() if k != "configSha256"}
        calibration.require(ev.digest(content) == value.get("configSha256") and value.get("scope") == scope
                            and value.get("holdoutQualified") is False, "FROZEN_CONFIG")
    # The combined calibration consumed the older deterministic config as immutable data and
    # records the later executable ranker sources that applied both combined and fallback policy.
    # Require that later source snapshot; the older config's own source map remains hash-covered
    # by its canonical config digest but is intentionally historical.
    calibration.require(all(calibration.sha(calibration.REPO / name) == digest
                            for name, digest in combined["sources"].items()), "FROZEN_SOURCE_DRIFT")
    calibration.require(combined["fallbackConfigSha256"] == deterministic["configSha256"]
                        and combined["maximumAlternatives"] == deterministic["maximumAlternatives"],
                        "CONFIG_LINK")
    receipt_path = calibration_export / "provenance.json"
    receipt = json.loads(receipt_path.read_text())
    calibration.require(calibration.sha(receipt_path) == deterministic["generatorReceiptSha256"]
                        and receipt["maximumAlternatives"] == combined["maximumAlternatives"]
                        and receipt.get("sourceOverrides") == {} and receipt.get("harnessWidthArgument") is True,
                        "CALIBRATION_EXPORT_LINK")
    calibration.require(all(calibration.sha(calibration.REPO / name) == digest
                            for name, digest in receipt["sources"].items()), "PRODUCTION_SOURCE_DRIFT")
    return combined, deterministic, receipt


def holdout_rows() -> tuple[object, list[dict]]:
    ev = evaluator()
    corpus = ev.load_corpus()
    ev.validate(corpus)
    rows = [row for row in corpus if row["split"] == "holdout" and row["task"] == "spelling"]
    calibration.require(len(rows) == 6000 and all(row["split"] == "holdout" for row in rows), "HOLDOUT_ROWS")
    return ev, rows


def summary(rows: list[dict], generated: list[dict], ev) -> dict:
    languages = {}
    for language in ("en", "ru", "es"):
        pairs = [(row, result) for row, result in zip(rows, generated, strict=True)
                 if row["language"] == language]
        typos = [(row, result) for row, result in pairs if row["cohort"] == "typo"]
        recall = sum(row["expectedSpelling"] in [result["original"],
                     *(item["text"] for item in result["alternatives"])] for row, result in typos)
        languages[language] = {
            "rows": len(pairs), "typoRows": len(typos),
            "candidateRecall": ev.rate(recall, len(typos)),
            "originalAvailable": all(result["original"] == row["typed"] for row, result in pairs),
            "retrievalAllowsAutoReplace": sum(not result["prohibitsAutoReplace"]
                                                and bool(result["alternatives"]) for _, result in pairs),
        }
    return {"split": "holdout", "holdoutExecuted": True, "decisionPolicyApplied": False,
            "autoReplaceEnabled": False, "languages": languages}


def run(args) -> None:
    output = Path(args.output).resolve()
    calibration.require(output.is_relative_to(calibration.REPO / "build") and not output.exists(),
                        "FRESH_BUILD_OUTPUT_REQUIRED")
    combined_path = Path(args.combined_config).resolve(strict=True)
    deterministic_path = Path(args.deterministic_config).resolve(strict=True)
    calibration_export = Path(args.calibration_export).resolve(strict=True)
    combined, deterministic, frozen_receipt = verified_configs(
        combined_path, deterministic_path, calibration_export)
    ev, rows = holdout_rows()

    index = Path(args.index_dir).resolve(strict=True)
    rank = Path(args.rank_dir).resolve(strict=True)
    assets = [index / f"{lang}{suffix}" for lang in ("en", "ru", "es")
              for suffix in (".trie", ".trie.lengths")]
    assets += [rank / f"{lang}.ranks" for lang in ("en", "ru", "es")]
    asset_hashes = {path.name: calibration.sha(path) for path in assets}
    calibration.require(asset_hashes == frozen_receipt["assets"], "FROZEN_ASSET_DRIFT")

    sources = [calibration.REPO / (calibration.PRODUCTION + path) for path in calibration.SOURCES]
    sources += [HERE / "CandidateExport.kt"]
    source_hashes = {str(path.relative_to(calibration.REPO)): calibration.sha(path) for path in sources}
    calibration.require(source_hashes == frozen_receipt["sources"], "FROZEN_GENERATOR_DRIFT")

    toolchain = json.loads((calibration.LEXICON /
        "weighted-qualification/manifests/reproduction-toolchain.json").read_text())
    jars = []
    for item in toolchain["jars"]:
        found = list((Path(args.gradle_cache) / item["group"] / item["artifact"] /
                      item["version"]).glob("*/*.jar"))
        calibration.require(len(found) == 1 and calibration.sha(found[0]) == item["sha256"],
                            "PINNED_CACHED_TOOLCHAIN_REQUIRED")
        jars.append(found[0])
    version = subprocess.run([args.java, "-version"], capture_output=True, timeout=15, check=True)
    calibration.require(b'version "17.' in version.stderr, "JAVA_17_REQUIRED")

    output.mkdir(parents=True)
    inputs = output / "inputs.tsv"
    with inputs.open("x", encoding="ascii") as stream:
        for index_value, row in enumerate(rows):
            token = base64.b64encode(row["typed"].encode()).decode("ascii")
            stream.write(f'{index_value}\t{row["language"]}\t{token}\n')
    binary = output / "generator.jar"
    command = [args.java, "-XX:ActiveProcessorCount=2", "-Xmx768m", "-cp",
               os.pathsep.join(map(str, jars)), "org.jetbrains.kotlin.cli.jvm.K2JVMCompiler",
               "-no-stdlib", "-no-reflect", "-jvm-target", "17", "-classpath",
               os.pathsep.join(map(str, jars[1:3])), "-d", str(binary), *map(str, sources)]
    with (output / "compile.log").open("xb") as log:
        subprocess.run(command, stdout=log, stderr=log, timeout=120, check=True)
    command = [args.java, "-XX:ActiveProcessorCount=2", "-Xmx768m", "-cp",
               os.pathsep.join(map(str, [binary, *jars[1:3]])),
               "io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateExport",
               str(inputs), str(index), str(rank), str(combined["maximumAlternatives"])]
    with (output / "actual.tsv").open("xb") as data, (output / "run.log").open("xb") as log:
        subprocess.run(command, stdout=data, stderr=log, timeout=600, check=True)
    generated = calibration.parse_output((output / "actual.tsv").read_text(), rows)
    calibration.require(all(len(item["alternatives"]) <= combined["maximumAlternatives"]
                            for item in generated), "REQUESTED_WIDTH")
    with (output / "candidates.jsonl").open("x", encoding="utf-8") as stream:
        for item in generated:
            stream.write(json.dumps(item, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")
    calibration.write_json(output / "summary.json", summary(rows, generated, ev))

    calibration.require(source_hashes == {str(path.relative_to(calibration.REPO)): calibration.sha(path)
                                          for path in sources}
                        and asset_hashes == {path.name: calibration.sha(path) for path in assets},
                        "EXECUTION_INPUT_DRIFT")
    calibration.write_json(output / "provenance.json", {
        "scope": "product-spelling-holdout-candidates", "holdoutExecuted": True,
        "holdoutRows": ev.digest(rows), "maximumAlternatives": combined["maximumAlternatives"],
        "combinedConfigSha256": combined["configSha256"],
        "deterministicConfigSha256": deterministic["configSha256"],
        "calibrationGeneratorReceiptSha256": calibration.sha(calibration_export / "provenance.json"),
        "sources": source_hashes, "assets": asset_hashes,
        "corpusManifest": calibration.sha(calibration.CORPUS / "manifest.json"),
        "toolchainManifest": calibration.sha(calibration.LEXICON /
            "weighted-qualification/manifests/reproduction-toolchain.json"),
        "binary": calibration.sha(binary), "inputs": calibration.sha(inputs),
        "actual": calibration.sha(output / "actual.tsv"),
        "candidates": calibration.sha(output / "candidates.jsonl"),
        "summary": calibration.sha(output / "summary.json"),
        "exporter": calibration.sha(Path(__file__)), "freshExecution": True,
        "hostTimingIsNotDeviceMeasurement": True,
    })
    print("Frozen product holdout candidate export complete; no thresholds were fitted.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("output", "combined-config", "deterministic-config", "calibration-export",
                   "index-dir", "rank-dir", "java", "gradle-cache"):
        parser.add_argument("--" + option, required=True)
    run(parser.parse_args())
