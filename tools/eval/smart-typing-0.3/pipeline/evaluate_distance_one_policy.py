#!/usr/bin/env python3
"""Run and qualify the current local distance-one policy on corpus v2."""
from __future__ import annotations

import argparse
import base64
from collections import Counter
import hashlib
import json
from pathlib import Path
import unicodedata

import final_product_replay as replay


REPO = Path(__file__).resolve().parents[4]
CORPUS = REPO / "tools/eval/smart-typing-0.3/qualification-v2/corpus"
LANGUAGES = ("en", "ru", "es")
QUALIFIED = {"en": False, "ru": True, "es": True}


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def load_rows() -> tuple[list[dict], dict]:
    manifest_path = CORPUS / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for name, expected in manifest["files"].items():
        if sha256(CORPUS / name) != expected:
            raise ValueError(f"CORPUS_FILE_DRIFT:{name}")
    rows = []
    for language in LANGUAGES:
        rows.extend(read_jsonl(CORPUS / f"spelling-{language}.jsonl"))
    rows.extend(read_jsonl(CORPUS / "protected-tokens.jsonl"))
    if len(rows) != 12_000 or len({row["id"] for row in rows}) != len(rows):
        raise ValueError("ROW_IDENTITIES")
    counts = Counter((row["split"], row["language"], row["cohort"]) for row in rows)
    expected = Counter({(split_name, language, cohort): count
        for split_name in ("calibration", "holdout") for language in LANGUAGES
        for cohort, count in (("typo", 1000), ("correct", 700), ("protected", 300))})
    if counts != expected:
        raise ValueError("ROW_PARTITIONS")
    return rows, manifest


def evaluate(rows: list[dict], observations: list[dict]) -> dict:
    if len(rows) != len(observations) or [row["id"] for row in rows] != [o["id"] for o in observations]:
        raise ValueError("OBSERVATION_IDENTITY")
    evidence = []
    for row, observation in zip(rows, observations):
        if observation.get("status") != "COMPLETE":
            raise ValueError(f"ROW_NOT_COMPLETE:{row['id']}")
        decision = observation.get("localDecision")
        after = observation["afterBoundary"]["text"]
        correction = (observation.get("autoEdit") or {}).get("correctionGeneration")
        changed = correction is not None
        expected = unicodedata.normalize("NFKC", row.get("expectedSpelling", row["typed"])).casefold()
        correct = changed and decision == expected and row["cohort"] == "typo" and not row["noAuto"]
        original = any(item.get("role") == "ORIGINAL" and item.get("text") == row["typed"]
            for item in observation.get("candidateView", {}).get("candidates", []))
        evidence.append({"id": row["id"], "split": row["split"], "language": row["language"],
            "cohort": row["cohort"], "family": row["family"], "localDecision": decision,
            "changed": changed, "correct": correct, "undoExact": observation["restoredBeforeBoundaryExactly"],
            "originalRetained": original, "actualDecision": decision})

    def one(language: str, split_name: str) -> dict:
        selected = [item for item in evidence if item["language"] == language and item["split"] == split_name]
        all_changes = [item for item in selected if item["changed"]]
        changes = [item for item in all_changes if item["localDecision"] is not None]
        correct = [item for item in changes if item["correct"]]
        local_decisions = [item for item in selected if item["localDecision"] is not None]
        protected_changes = [item for item in changes if item["cohort"] == "protected"]
        undo_failures = [item for item in changes if not item["undoExact"]]
        original_failures = [item for item in changes if not item["originalRetained"]]
        precision = len(correct) / len(changes) if changes else None
        families = len({item["family"] for item in correct})
        qualified = QUALIFIED[language]
        passed = (not qualified) or (len(changes) >= 300 and families >= 300 and
            len(correct) * 100 >= len(changes) * 99 and not protected_changes and
            not undo_failures and not original_failures and len(changes) == len(local_decisions))
        return {"qualified": qualified, "rows": len(selected), "localDecisions": len(local_decisions),
            "automaticChanges": len(changes), "correctChanges": len(correct),
            "otherAutomaticChanges": len(all_changes) - len(changes),
            "precision": precision, "distinctCorrectFamilies": families,
            "protectedChanges": len(protected_changes), "undoFailures": len(undo_failures),
            "originalRetentionFailures": len(original_failures), "passed": passed,
            "falseExamples": [{"id": item["id"], "cohort": item["cohort"],
                "actualDecision": item["actualDecision"]}
                for item in changes if not item["correct"]][:10]}

    result = {split_name: {language: one(language, split_name) for language in LANGUAGES}
        for split_name in ("calibration", "holdout")}
    result["releaseApproved"] = all(result["holdout"][language]["passed"] for language in LANGUAGES)
    return {"report": result, "evidence": evidence}


def run(args: argparse.Namespace) -> None:
    root = Path(args.output).resolve()
    if not root.is_relative_to(REPO / "build") or root.exists():
        raise ValueError("FRESH_BUILD_OUTPUT_REQUIRED")
    rows, manifest = load_rows()
    root.mkdir(parents=True)
    rows_path = root / "rows.jsonl"
    with rows_path.open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    inputs = root / "inputs.tsv"
    with inputs.open("x", encoding="ascii") as stream:
        for index, row in enumerate(rows):
            encode = lambda value: base64.b64encode(value.encode()).decode("ascii")
            stream.write("\t".join((str(index), encode(row["id"]), row["split"], row["language"],
                encode(row["prefix"]), encode(row["typed"]))) + "\n")
    java = Path(args.java).resolve(strict=True)
    sources, jars, android = replay.compile_inputs(java)
    jar, compile_command = replay.compile_harness(root, java, sources, jars, android)
    observations_path = root / "observations.jsonl"
    execute_command = replay.run_harness(root, java, jars, android, jar, inputs,
        observations_path, "unavailable")
    observations = read_jsonl(observations_path)
    evaluated = evaluate(rows, observations)
    evidence_path = root / "evidence.jsonl"
    with evidence_path.open("x", encoding="utf-8") as stream:
        for item in evaluated["evidence"]:
            stream.write(json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    source_paths = [Path(__file__).resolve(), *sources, *replay.asset_paths(), CORPUS / "manifest.json",
        *(CORPUS / name for name in manifest["files"])]
    report = {"schemaVersion": 1, "policyVersion": 1, "searchVersion": 1,
        "corpusVersion": 2, "modelMode": "explicitly-unavailable", "rows": len(rows),
        "bindings": {str(path.relative_to(REPO)): sha256(path) for path in source_paths},
        "commands": {"compile": compile_command, "execute": execute_command}, **evaluated["report"]}
    write_json(root / "report.json", report)
    print(json.dumps(evaluated["report"], ensure_ascii=False, indent=2))
    if not evaluated["report"]["releaseApproved"]:
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--java", default="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/java")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
