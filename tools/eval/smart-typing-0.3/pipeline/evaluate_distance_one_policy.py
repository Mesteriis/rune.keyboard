#!/usr/bin/env python3
"""Diagnose the current local distance-one policy on already revealed corpus v2."""
from __future__ import annotations

import argparse
import base64
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys
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


def utf16(text: str) -> bytes:
    return text.encode('utf-16-le', errors='surrogatepass')


def snapshot(value: object) -> dict:
    if not isinstance(value, dict) or not isinstance(value.get('text'), str):
        raise ValueError('EDITOR_SNAPSHOT')
    size = len(utf16(value['text'])) // 2
    if any(type(value.get(key)) is not int for key in ('caret', 'composingStart', 'composingEnd')):
        raise ValueError('EDITOR_SNAPSHOT')
    start, end = value['composingStart'], value['composingEnd']
    if not 0 <= value['caret'] <= size or not (start == end == -1 or 0 <= start <= end <= size):
        raise ValueError('EDITOR_SNAPSHOT')
    return value


def validate_editor(row: dict, observation: dict) -> tuple[bool, bool]:
    if any(observation.get(key) != row.get(key) for key in ('id', 'split', 'language', 'typed')) or \
            observation.get('prefix') != row.get('prefix', ''):
        raise ValueError('OBSERVATION_INPUT_IDENTITY')
    expected = (row['prefix'] + ' ' if row.get('prefix') else '') + row['typed']
    before = snapshot(observation.get('beforeBoundary'))
    after = snapshot(observation.get('afterBoundary'))
    restored = snapshot(observation.get('afterBackspace'))
    facts = {'inputChangedByTyping': before['text'] != expected,
             'boundaryChangedBeyondInsertedSpace': after['text'] != before['text'] + ' ',
             'restoredBeforeBoundaryExactly': restored['text'] == before['text']}
    if observation.get('inputExpected') != expected or any(
            type(observation.get(key)) is not bool or observation[key] != value
            for key, value in facts.items()):
        raise ValueError('EDITOR_FLAGS_DIVERGE')
    edit = observation.get('autoEdit')
    if edit is not None and not isinstance(edit, dict):
        raise ValueError('EDITOR_CORRECTION_DIVERGES')
    correction = (edit or {}).get('correctionGeneration')
    if correction is not None:
        if not isinstance(correction, dict) or not facts['boundaryChangedBeyondInsertedSpace'] or \
                type(edit.get('committedStart')) is not int or edit['committedStart'] < 0 or \
                not all(isinstance(edit.get(key), str) for key in ('original', 'applied')):
            raise ValueError('EDITOR_CORRECTION_DIVERGES')
        start = 2 * edit['committedStart']
        original = utf16(edit['original'])
        text = utf16(before['text'])
        if start > len(text) or text[start:start + len(original)] != original or \
                text[:start] + utf16(edit['applied']) + text[start + len(original):] != utf16(after['text']):
            raise ValueError('EDITOR_CORRECTION_DIVERGES')
    return facts['boundaryChangedBeyondInsertedSpace'], before == restored


def evaluate(rows: list[dict], observations: list[dict]) -> dict:
    if len(rows) != len(observations) or [row["id"] for row in rows] != [o["id"] for o in observations]:
        raise ValueError("OBSERVATION_IDENTITY")
    evidence = []
    for row, observation in zip(rows, observations):
        if observation.get("status") != "COMPLETE":
            raise ValueError(f"ROW_NOT_COMPLETE:{row['id']}")
        if observation.get("morphologyAdmission") is not True:
            raise ValueError(f"MORPHOLOGY_ADMISSION_MISSING:{row['id']}")
        allowed = observation.get('automaticAdmissionAllowed')
        refusal = observation.get('automaticAdmissionRefusal')
        candidate = observation.get('automaticAdmissionCandidate')
        if not all(key in observation for key in ('automaticAdmissionAllowed',
                'automaticAdmissionRefusal', 'automaticAdmissionCandidate')):
            raise ValueError('ADMISSION_RECORD_DIVERGES')
        if allowed is None:
            if refusal is not None:
                raise ValueError('ADMISSION_RECORD_DIVERGES')
        elif type(allowed) is not bool or not isinstance(candidate, str) or not candidate or \
                (allowed and refusal is not None) or (not allowed and not isinstance(refusal, str)):
            raise ValueError('ADMISSION_RECORD_DIVERGES')
        changed, undo_exact = validate_editor(row, observation)
        decision = observation.get("localDecision")
        after = observation["afterBoundary"]["text"]
        expected = unicodedata.normalize("NFKC", row.get("expectedSpelling", row["typed"])).casefold()
        expected_text = (row['prefix'] + ' ' if row.get('prefix') else '') + \
            row.get('expectedSpelling', row['typed']) + ' '
        correct = changed and decision == expected and after == expected_text and \
            row["cohort"] == "typo" and not row["noAuto"]
        original = any(item.get("role") == "ORIGINAL" and item.get("text") == row["typed"]
            for item in observation.get("candidateView", {}).get("candidates", []))
        evidence.append({"id": row["id"], "split": row["split"], "language": row["language"],
            "cohort": row["cohort"], "family": row["family"], "localDecision": decision,
            "changed": changed, "correct": correct, "undoExact": undo_exact,
            "typingChanged": observation['inputChangedByTyping'],
            "editorMismatch": decision == expected and after != expected_text,
            "originalRetained": original, "actualDecision": decision,
            "automaticAdmissionAllowed": observation.get("automaticAdmissionAllowed"),
            "automaticAdmissionRefusal": observation.get("automaticAdmissionRefusal"),
            "automaticAdmissionCandidate": observation.get("automaticAdmissionCandidate")})

    def one(language: str, split_name: str) -> dict:
        selected = [item for item in evidence if item["language"] == language and item["split"] == split_name]
        all_changes = [item for item in selected if item["changed"]]
        changes = [item for item in all_changes if item["localDecision"] is not None]
        correct = [item for item in changes if item["correct"]]
        local_decisions = [item for item in selected if item["localDecision"] is not None]
        admission_vetoes = [item for item in local_decisions if not item["changed"]]
        unexpected_vetoes = [item for item in admission_vetoes
            if item['automaticAdmissionAllowed'] is not False or
                item["automaticAdmissionRefusal"] != "ORIGINAL_VALID" or
                item["automaticAdmissionCandidate"] != item["localDecision"]]
        unexplained_changes = [item for item in changes
            if item["automaticAdmissionAllowed"] is not True or
                item["automaticAdmissionCandidate"] != item["localDecision"]]
        protected_changes = [item for item in changes if item["cohort"] == "protected"]
        undo_failures = [item for item in changes if not item["undoExact"]]
        original_failures = [item for item in changes if not item["originalRetained"]]
        precision = len(correct) / len(changes) if changes else None
        families = len({item["family"] for item in correct})
        qualified = QUALIFIED[language]
        passed = (not qualified) or (len(changes) >= 300 and families >= 300 and
            len(correct) * 100 >= len(changes) * 99 and not protected_changes and
            not undo_failures and not original_failures and not unexpected_vetoes and
            not unexplained_changes)
        return {"qualified": qualified, "rows": len(selected), "localDecisions": len(local_decisions),
            "automaticChanges": len(changes), "correctChanges": len(correct),
            "otherAutomaticChanges": len(all_changes) - len(changes),
            "precision": precision, "distinctCorrectFamilies": families,
            "admissionVetoes": len(admission_vetoes),
            "unexpectedAdmissionVetoes": len(unexpected_vetoes),
            "unexplainedAdmissionChanges": len(unexplained_changes),
            "typingChanges": sum(item['typingChanged'] for item in selected),
            "editorMismatchChanges": sum(item['editorMismatch'] for item in changes),
            "protectedChanges": len(protected_changes), "undoFailures": len(undo_failures),
            "originalRetentionFailures": len(original_failures), "passed": passed,
            "falseExamples": [{"id": item["id"], "cohort": item["cohort"],
                "actualDecision": item["actualDecision"]}
                for item in changes if not item["correct"]][:10]}

    result = {split_name: {language: one(language, split_name) for language in LANGUAGES}
        for split_name in ("calibration", "holdout")}
    result['historicalHoldoutGatePassed'] = all(result['holdout'][language]['passed'] for language in LANGUAGES)
    result.update(releaseApproved=False, productionQualified=False, newUnseenHoldout=False)
    return {"report": result, "evidence": evidence}


def run(args: argparse.Namespace) -> None:
    root = Path(args.output).resolve()
    if not root.is_relative_to(REPO / "build") or root.exists():
        raise ValueError("FRESH_BUILD_OUTPUT_REQUIRED")
    if any(os.environ.get(key) for key in ('JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', '_JAVA_OPTIONS')):
        raise ValueError('UNDECLARED_JAVA_OPTIONS')
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
    runtime = replay.java_runtime_binding(java)
    assets = sorted(path for path in replay.ASSETS.rglob('*') if path.is_file())
    source_paths = [Path(__file__).resolve(), Path(replay.__file__), *sources,
        *assets, CORPUS / 'manifest.json',
        *(CORPUS / name for name in manifest['files']), replay.SOURCE_MANIFEST, replay.TOOLCHAIN,
        *jars, android, Path(sys.executable).resolve(),
        *(Path(runtime['home']) / name for name in runtime['inventory'])]
    bindings = {replay.path_key(path): sha256(path) for path in source_paths}
    write_json(root / 'source-freeze.json', bindings)
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
    replay.verify_bound_files({'files': bindings})
    if assets != sorted(path for path in replay.ASSETS.rglob('*') if path.is_file()):
        raise ValueError('ASSET_SET_DRIFT')
    report = {"schemaVersion": 2, "policyVersion": 1, "searchVersion": 1,
        "scope": "historical-distance-one-diagnostic",
        "morphologyAdmission": True,
        "corpusVersion": 2, "modelMode": "explicitly-unavailable", "rows": len(rows),
        "bindings": bindings, "javaRuntime": runtime,
        "files": {path.name: sha256(path) for path in root.iterdir() if path.is_file()},
        "commands": {"compile": compile_command, "execute": execute_command}, **evaluated["report"]}
    write_json(root / "report.json", report)
    print(json.dumps(evaluated["report"], ensure_ascii=False, indent=2))
    if not evaluated["report"]["historicalHoldoutGatePassed"]:
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--java", default="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/java")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
