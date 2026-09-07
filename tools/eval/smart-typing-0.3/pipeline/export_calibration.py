#!/usr/bin/env python3
"""Run the actual Kotlin generator on public calibration rows; never score holdout."""
from __future__ import annotations

import argparse
import base64
from collections import Counter
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
EVALUATOR_ROOT = HERE.parent
CORPUS = EVALUATOR_ROOT
LEXICON = REPO / "tools/lexicon/smart-typing-0.3"
PRODUCTION = "app/src/main/java/io/github/mesteriis/rune/keyboard/"
SOURCES = ["ime/model/KeyboardState.kt"] + [f"smarttyping/correction/{s}.kt" for s in (
    "TokenUnicode", "ProtectedTokenPolicy", "CasePattern", "KeyboardDistance", "WeightedDamerauLevenshtein", "CommonConfusions"
)] + [f"smarttyping/lexicon/{s}.kt" for s in (
    "LanguageRouter", "CandidateLexicon", "CanonicalCaseLexicon", "CandidateGenerator", "PackedCandidateLexicon",
    "PackedLexiconData", "PackedLexiconManifest", "FrozenPackedLexicons",
    "TopCandidateSelection", "PackedTopSeven", "PrefixDistance"
)]
COMPLETIONS = {"COMPLETE", "PROTECTED", "VALID_WORD", "STATES_EXHAUSTED", "VERIFIED_EXHAUSTED",
               "CANCELLED", "UNAVAILABLE", "READER_FAILURE"}


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")


def require(ok, code):
    if not ok:
        raise ValueError(code)


def boolean(value):
    require(value in ("true", "false"), "BOOLEAN")
    return value == "true"


def decoded(value):
    return base64.b64decode(value, validate=True).decode("utf-8", errors="strict")


def parse_output(text, rows):
    """Check every numeric envelope and retain original at index zero, without oracle injection."""
    results = []
    expected_count = 0
    for line in text.splitlines():
        f = line.split("\t")
        if f[0] == "R":
            require(len(f) == 9 and int(f[1]) == len(results) and len(results) < len(rows), "ROW_ID")
            require(not results or len(results[-1]["alternatives"]) == expected_count, "CANDIDATE_COUNT")
            row = rows[len(results)]
            complete, valid, veto = f[2], boolean(f[3]), boolean(f[4])
            states, verified, expected_count = int(f[5]), int(f[6]), int(f[8])
            require(complete in COMPLETIONS and 0 <= states <= 8192 and 0 <= verified <= 64
                    and 0 <= expected_count <= 7, "BOUNDS")
            require(veto == (complete != "COMPLETE" or valid or f[7] != "NONE"), "RETRIEVAL_VETO")
            results.append({"id": row["id"], "original": row["typed"], "completion": complete,
                            "isValidWord": valid, "prohibitsAutoReplace": veto,
                            "inspectedStates": states, "verifiedTerminals": verified,
                            "protectedReason": None if f[7] == "NONE" else f[7], "alternatives": []})
        elif f[0] == "C":
            require(len(f) == 16 and results and int(f[1]) == len(results) - 1, "CANDIDATE_OWNER")
            previous = results[-1]
            require(int(f[2]) == len(previous["alternatives"]) + 1 <= expected_count, "CANDIDATE_ID")
            display, key, terminal = map(decoded, f[3:6])
            require(display and display != previous["original"] and len(display) <= 32
                    and all(c["canonicalKey"] != key for c in previous["alternatives"]), "CANDIDATE_TEXT")
            cost, bonus = float(f[11]), float(f[13])
            require(f[6] in ("en", "ru", "es") and int(f[9]) > 0 and int(f[10]) in (1, 2)
                    and math.isfinite(cost) and cost >= 0 and math.isfinite(bonus) and bonus >= 0,
                    "CANDIDATE_FEATURES")
            previous["alternatives"].append({"id": int(f[2]), "text": display, "canonicalKey": key,
                "terminalKey": terminal, "language": f[6], "isFallback": boolean(f[7]),
                "languagePrior": int(f[8]), "frequencyRank": int(f[9]), "unitDistance": int(f[10]),
                "editCost": cost, "repeatedCharacterEdits": int(f[12]), "repetitionBonus": bonus,
                "lengthDifference": int(f[14]), "casePattern": f[15]})
        else:
            raise ValueError("UNEXPECTED_RECORD")
    require(len(results) == len(rows) and (not results or len(results[-1]["alternatives"]) == expected_count),
            "INCOMPLETE_OUTPUT")
    return results


def summarize(rows, results):
    report = {"split": "calibration", "productionQualified": False, "autoReplaceEnabled": False,
              "holdoutExecuted": False, "languages": {}}
    for language in ("en", "ru", "es"):
        pairs = [(r, c) for r, c in zip(rows, results) if r["language"] == language]
        typo = [(r, c) for r, c in pairs if r["cohort"] == "typo"]
        recalled = [(r, c) for r, c in typo if r["expectedSpelling"] in [c["original"]] +
                    [a["text"] for a in c["alternatives"]]]
        report["languages"][language] = {
            "rows": len(pairs), "uniqueInputs": len({r["typed"] for r, _ in pairs}),
            "typoRows": len(typo), "candidateRecallCount": len(recalled),
            "candidateRecall": len(recalled) / len(typo) if typo else None,
            "retrievalAllowsAutoReplace": sum(not c["prohibitsAutoReplace"] and bool(c["alternatives"]) for _, c in pairs),
            "completeRecalledTypos": sum(not c["prohibitsAutoReplace"] for _, c in recalled),
            "completionCounts": dict(sorted(Counter(c["completion"] for _, c in pairs).items())),
        }
    return report


def selected_sources(production_sources, source_overrides, experiment):
    source_overrides = source_overrides or {}
    require(set(source_overrides) <= set(production_sources), "UNKNOWN_SOURCE_OVERRIDE")
    require(not source_overrides or experiment is not None, "EXPERIMENT_IDENTITY_REQUIRED")
    sources = [source_overrides.get(p, p) for p in production_sources]
    require(all(p.resolve().is_relative_to(REPO) for p in sources), "SOURCE_SCOPE")
    return sources


def run(args, source_overrides=None, experiment=None):
    """CLI always uses production sources; controlled host experiments may provide hashed overlays."""
    exporter_sha = sha(Path(__file__))
    maximum = getattr(args, "maximum_alternatives", 7)
    require(type(maximum) is int and 1 <= maximum <= 7, "CANDIDATE_WIDTH")
    corpus = Path(getattr(args, "corpus", CORPUS)).resolve(strict=True)
    require(corpus.is_relative_to(REPO), "CORPUS_SCOPE")
    manifest = json.loads((corpus / "manifest.json").read_text())
    for name, digest in manifest["files"].items():
        require(sha(corpus / name) == digest, "CORPUS_DIGEST")
    spec = importlib.util.spec_from_file_location("prepared_evaluator", EVALUATOR_ROOT / "evaluate.py")
    evaluator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evaluator)
    all_rows = evaluator.load_corpus(corpus)
    evaluator.validate(all_rows)
    rows = [r for r in all_rows if r["split"] == "calibration" and r["task"] == "spelling"]
    require(len(rows) == 6000, "CALIBRATION_COUNT")
    output = Path(args.output).resolve()
    require(output.is_relative_to(REPO / "build") and not output.exists(), "FRESH_BUILD_OUTPUT_REQUIRED")
    index, rank = Path(args.index_dir).resolve(strict=True), Path(args.rank_dir).resolve(strict=True)
    assets = [index / f"{lang}{suffix}" for lang in ("en", "ru", "es") for suffix in (".trie", ".trie.lengths")]
    assets += [rank / f"{lang}.ranks" for lang in ("en", "ru", "es")]
    production_sources = [REPO / (PRODUCTION + p) for p in SOURCES] + [HERE / "CandidateExport.kt"]
    source_overrides = source_overrides or {}
    sources = selected_sources(production_sources, source_overrides, experiment)
    source_hashes = {str(p.relative_to(REPO)): sha(p) for p in sources}
    tools = json.loads((LEXICON / "weighted-qualification/manifests/reproduction-toolchain.json").read_text())
    jars = []
    for item in tools["jars"]:
        found = list((Path(args.gradle_cache) / item["group"] / item["artifact"] / item["version"]).glob("*/*.jar"))
        require(len(found) == 1 and sha(found[0]) == item["sha256"], "PINNED_CACHED_TOOLCHAIN_REQUIRED")
        jars.append(found[0])
    version = subprocess.run([args.java, "-version"], capture_output=True, timeout=15, check=True)
    require(b'version "17.' in version.stderr, "JAVA_17_REQUIRED")
    asset_hashes = {p.name: sha(p) for p in assets}
    output.mkdir(parents=True)
    inputs = output / "inputs.tsv"
    with inputs.open("x", encoding="ascii") as stream:
        for i, row in enumerate(rows):
            token = base64.b64encode(row["typed"].encode("utf-8")).decode("ascii")
            stream.write(f'{i}\t{row["language"]}\t{token}\n')
    binary = output / "generator.jar"
    command = [args.java, "-XX:ActiveProcessorCount=2", "-Xmx768m", "-cp", os.pathsep.join(map(str, jars)),
               "org.jetbrains.kotlin.cli.jvm.K2JVMCompiler", "-no-stdlib", "-no-reflect", "-jvm-target", "17",
               "-classpath", os.pathsep.join(map(str, jars[1:3])), "-d", str(binary), *map(str, sources)]
    with (output / "compile.log").open("xb") as log:
        subprocess.run(command, stdout=log, stderr=log, timeout=120, check=True)
    command = [args.java, "-XX:ActiveProcessorCount=2", "-Xmx768m", "-cp",
               os.pathsep.join(map(str, [binary, *jars[1:3]])),
               "io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateExport", str(inputs), str(index), str(rank), str(maximum)]
    with (output / "actual.tsv").open("xb") as data, (output / "run.log").open("xb") as log:
        subprocess.run(command, stdout=data, stderr=log, timeout=600, check=True)
    results = parse_output((output / "actual.tsv").read_text(encoding="ascii"), rows)
    require(all(len(r["alternatives"]) <= maximum for r in results), "REQUESTED_WIDTH")
    require(source_hashes == {str(p.relative_to(REPO)): sha(p) for p in sources}
            and asset_hashes == {p.name: sha(p) for p in assets}
            and exporter_sha == sha(Path(__file__)), "EXECUTION_INPUT_DRIFT")
    with (output / "candidates.jsonl").open("x", encoding="utf-8") as stream:
        for result in results:
            stream.write(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")
    summary = summarize(rows, results)
    if experiment is not None:
        summary["experiment"] = experiment
    write_json(output / "summary.json", summary)
    write_json(output / "provenance.json", {"sources": source_hashes, "assets": asset_hashes,
        "corpusManifest": sha(corpus / "manifest.json"),
        "corpusDirectory": str(corpus.relative_to(REPO)),
        "calibrationRows": evaluator.digest(rows),
        "exporter": exporter_sha, "toolchainManifest": sha(LEXICON / "weighted-qualification/manifests/reproduction-toolchain.json"),
        "binary": sha(binary), "inputs": sha(inputs), "actual": sha(output / "actual.tsv"),
        "candidates": sha(output / "candidates.jsonl"), "summary": sha(output / "summary.json"),
        "hostTimingIsNotDeviceMeasurement": True, "freshExecution": True,
        "maximumAlternatives": maximum, "harnessWidthArgument": True,
        "experiment": experiment, "sourceOverrides": {str(p.relative_to(REPO)): str(v.relative_to(REPO))
            for p, v in source_overrides.items()}})
    print("Calibration candidate export complete; no model, holdout or AutoReplace qualification.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "index-dir", "rank-dir", "java", "gradle-cache"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--corpus", default=CORPUS)
    parser.add_argument("--maximum-alternatives", type=int, choices=range(1, 8), default=7)
    run(parser.parse_args())
