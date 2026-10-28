#!/usr/bin/env python3
"""Replay the frozen v8 external holdout without passing labels to Kotlin."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import export_external_spelling_replay as common  # noqa: E402


EXPECTED_COUNTS = Counter(typo=1_000, correct=700)


def validate_rows(rows: list[dict]) -> None:
    if len(rows) != 1_700 or Counter(row.get("cohort") for row in rows) != EXPECTED_COUNTS:
        raise ValueError("HOLDOUT_COUNTS")
    if len({row.get("id") for row in rows}) != len(rows) or len({row.get("family") for row in rows}) != len(rows):
        raise ValueError("HOLDOUT_DISJOINTNESS")
    if any(row.get("language") != "ru" or row.get("split") != "holdout" or
           row.get("task") != "spelling" or row.get("corpusVersion") != 8 for row in rows):
        raise ValueError("HOLDOUT_SCOPE")
    if any((row["cohort"] == "typo") != isinstance(row.get("expectedSpelling"), str)
           for row in rows):
        raise ValueError("HOLDOUT_LABELS")


def validate_manifest(manifest_path: Path, rows_path: Path, parquet_path: Path,
                      rows: list[dict]) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = {"schemaVersion": 1, "corpusVersion": 8,
                "scope": "independent-ru-spelling-holdout-v8",
                "frozenBeforeScoring": True, "containsPersonalMessages": False,
                "labelsRetainedForPythonOnly": True}
    if any(manifest.get(key) != value for key, value in required.items()):
        raise ValueError("HOLDOUT_MANIFEST")
    if manifest.get("files", {}).get("rows.jsonl") != common.sha256(rows_path):
        raise ValueError("HOLDOUT_ROWS_IDENTITY")
    source = manifest.get("source", {})
    if parquet_path.stat().st_size != source.get("bytes") or common.sha256(parquet_path) != source.get("sha256"):
        raise ValueError("HOLDOUT_SOURCE_IDENTITY")
    for section in (manifest.get("sources", {}), manifest.get("exclusions", {}).get("files", {})):
        if not section:
            raise ValueError("HOLDOUT_BINDINGS")
        for key, expected in section.items():
            if common.sha256(common.resolve_bound_path(key).resolve(strict=True)) != expected:
                raise ValueError(f"HOLDOUT_BINDING_DRIFT:{key}")
    validate_rows(rows)
    return manifest


def export(rows_path: Path, manifest_path: Path, parquet_path: Path, policy_path: Path,
           output: Path, java: Path) -> dict:
    rows_path, manifest_path, parquet_path, policy_path = (
        rows_path.resolve(strict=True), manifest_path.resolve(strict=True),
        parquet_path.resolve(strict=True), policy_path.resolve(strict=True))
    output = output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / "build"):
        raise ValueError("FRESH_BUILD_OUTPUT_REQUIRED")
    rows = common.read_jsonl(rows_path)
    manifest = validate_manifest(manifest_path, rows_path, parquet_path, rows)
    replay = common.load_replay()
    java = java.resolve(strict=True)
    sources, jars, android = replay.compile_inputs(java)
    runtime = replay.java_runtime_binding(java)
    runtime_files = [Path(runtime["home"]) / relative for relative in runtime["inventory"]]
    fixed = [rows_path, manifest_path, parquet_path, policy_path, Path(__file__),
             Path(common.__file__), common.REPLAY_PATH, replay.SOURCE_MANIFEST, replay.TOOLCHAIN,
             android, *runtime_files, *sources, *jars, *replay.asset_paths(),
             *replay.compact_asset_paths()]
    bindings = {common.path_key(path): common.sha256(path) for path in fixed}
    output.mkdir(parents=True)
    replay.write_json(output / "source-freeze.json", {
        "schemaVersion": 1, "scope": "external-ru-spelling-local-replay-v8",
        "frozenCandidatePolicy": {"path": common.path_key(policy_path),
                                  "sha256": common.sha256(policy_path)},
        "holdoutManifest": manifest,
        "bindings": {"files": bindings, "javaRuntime": runtime},
        "labelsEnteredHarness": False, "modelCalls": 0})
    inputs = output / "inputs.tsv"
    with inputs.open("x", encoding="ascii") as stream:
        stream.writelines(common.label_free_input_lines(rows))
    jar, compile_command = replay.compile_harness(output, java, sources, jars, android)
    observations_path = output / "observations.jsonl"
    execute_command = replay.run_harness(output, java, jars, android, jar, inputs,
                                         observations_path, "unavailable", target_split="all")
    observations = common.read_jsonl(observations_path)
    if [item.get("id") for item in observations] != [row["id"] for row in rows]:
        raise ValueError("REPLAY_ROW_IDENTITY")
    if any(item.get("status") != "COMPLETE" or item.get("split") != "holdout" or
           item.get("language") != "ru" for item in observations):
        raise ValueError("REPLAY_INCOMPLETE")
    replay.verify_bound_files({"files": bindings})
    artifacts = {path.name: common.sha256(path) for path in output.iterdir() if path.is_file()}
    receipt = {"schemaVersion": 1, "scope": "external-ru-spelling-local-replay-v8",
        "complete": True, "rows": len(rows), "observations": len(observations),
        "modelCalls": 0, "modelMode": "explicit-unavailable", "labelsEnteredHarness": False,
        "labelsRetainedForPythonOnlyJoin": True, "rowsSha256": common.sha256(rows_path),
        "manifestSha256": common.sha256(manifest_path), "policySha256": common.sha256(policy_path),
        "sourceFreezeSha256": common.sha256(output / "source-freeze.json"),
        "bindings": {"files": bindings, "javaRuntime": runtime}, "artifacts": artifacts,
        "commands": {"compile": compile_command, "replay": execute_command}}
    replay.write_json(output / "receipt.json", receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("rows", "manifest", "parquet", "policy", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--java", type=Path,
        default=Path("/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/java"))
    args = parser.parse_args()
    receipt = export(args.rows, args.manifest, args.parquet, args.policy, args.output, args.java)
    print(json.dumps({key: receipt[key] for key in ("rows", "observations", "modelCalls",
                                                    "policySha256")}, sort_keys=True))


if __name__ == "__main__":
    main()
