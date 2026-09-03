#!/usr/bin/env python3
"""Compare a current compiled export harness with the preserved full-neighborhood oracle."""
import argparse
import base64
import importlib.util
import json
import os
from pathlib import Path
import subprocess

if not __debug__:
    raise RuntimeError("QUALIFICATION_REQUIRES_ASSERTIONS")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PACKAGE = HERE.parent / "weighted-qualification"
EXPORT = ROOT / "tools/eval/smart-typing-0.3/pipeline/export_calibration.py"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def signature(candidate):
    return (candidate["text"], candidate["canonicalKey"], candidate["terminalKey"], candidate["language"],
            int(candidate["isFallback"]), candidate["languagePrior"], candidate["frequencyRank"],
            candidate["unitDistance"], candidate["editCost"] * 4, candidate["repeatedCharacterEdits"],
            candidate["lengthDifference"], candidate["casePattern"])


def expected_signature(candidate):
    return (candidate["display"], candidate["key"], candidate["terminal"], ("en", "ru", "es")[candidate["language"]],
            candidate["fallback"], candidate["prior"], candidate["frequency"], candidate["unit"],
            candidate["quarters"], candidate["repeats"], candidate["length_difference"],
            ("LOWER", "TITLE", "UPPER", "MIXED", "UNCASED")[candidate["case"]])


def excluded_controls(inputs):
    excluded = []
    for row in inputs:
        if row["cancellation"]:
            excluded.append({"id": row["id"], "reason": "explicit cancellation"})
        elif any(0xd800 <= ord(c) <= 0xdfff for c in row["query"]):
            excluded.append({"id": row["id"], "reason": "unpaired surrogate incompatible with strict UTF-8 harness"})
    return excluded


def requested_width(receipt, maximum):
    assert type(maximum) is int and maximum in (1, 3, 7)
    experiment = receipt.get("experiment")
    if receipt.get("harnessWidthArgument") is True:
        assert receipt["maximumAlternatives"] == maximum
    if experiment is None:
        assert maximum == 7 or receipt.get("harnessWidthArgument") is True
    else:
        assert experiment["name"] == "exact-candidate-budget"
        assert experiment["maximumAlternatives"] == maximum and experiment["totalCandidates"] == maximum + 1
        assert experiment["stateCap"] == 8192 and experiment["verificationCap"] == 64
    return maximum


def run(args):
    archive = module("preserved_archive", PACKAGE / "archive.py")
    export = module("current_export", EXPORT)
    records = archive.load(PACKAGE)
    inputs = json.loads(records["fixtures/inputs.json"])
    oracle = json.loads(records["fixtures/expected.json"])
    assert [r["id"] for r in inputs] == [r["id"] for r in oracle] == list(range(775))
    # The export protocol deliberately has a strict UTF-8 boundary and no cancellation command.
    # Both excluded controls are separately exercised by production JVM tests.
    excluded = excluded_controls(inputs)
    excluded_ids = {r["id"] for r in excluded}
    selected = [r for r in inputs if r["id"] not in excluded_ids]
    assert len(selected) == 773 and len(excluded) == 2
    home = Path(args.compiled_export).resolve(strict=True)
    receipt = json.loads((home / "provenance.json").read_text())
    maximum = requested_width(receipt, getattr(args, "maximum_alternatives", 7))
    def verify_sources():
        assert all(export.sha(ROOT / path) == digest for path, digest in receipt["sources"].items())
        assert export.sha(home / "generator.jar") == receipt["binary"]
    verify_sources()
    jars = []
    manifest = json.loads((PACKAGE / "manifests/reproduction-toolchain.json").read_text())
    for item in manifest["jars"][1:3]:
        found = list((Path(args.gradle_cache) / item["group"] / item["artifact"] / item["version"]).glob("*/*.jar"))
        assert len(found) == 1 and export.sha(found[0]) == item["sha256"]
        jars.append(found[0])
    output = Path(args.output).resolve()
    assert output.is_relative_to(ROOT / "build") and not output.exists()
    index, rank = Path(args.index_dir).resolve(strict=True), Path(args.rank_dir).resolve(strict=True)
    assets = [index / f"{lang}{suffix}" for lang in ("en", "ru", "es") for suffix in (".trie", ".trie.lengths")]
    assets += [rank / f"{lang}.ranks" for lang in ("en", "ru", "es")]
    assert {p.name: export.sha(p) for p in assets} == receipt["assets"]
    output.mkdir(parents=True)
    with (output / "inputs.tsv").open("x") as stream:
        for i, row in enumerate(selected):
            encoded = base64.b64encode(row["query"].encode()).decode()
            stream.write(f'{i}\t{("en", "ru", "es")[row["active"]]}\t{encoded}\n')
    with (output / "actual.tsv").open("xb") as raw, (output / "run.log").open("xb") as log:
        subprocess.run([args.java, "-XX:ActiveProcessorCount=2", "-Xmx768m", "-cp",
            os.pathsep.join(map(str, [home / "generator.jar", *jars])),
            "io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateExport", str(output / "inputs.tsv"),
            str(index), str(rank)] + ([str(maximum)] if receipt.get("harnessWidthArgument") else []),
            stdout=raw, stderr=log, timeout=300, check=True)
    rows = [{"id": r["id"], "typed": r["query"]} for r in selected]
    actual = export.parse_output((output / "actual.tsv").read_text(), rows)
    counts = {"complete": 0, "incomplete": 0, "policy": 0}
    reasons = ("TOO_LONG", "MALFORMED_UNICODE", "PATH_OR_IDENTIFIER", "MIXED_SCRIPT", "UNSUPPORTED_SCRIPT",
               "LETTERS_AND_DIGITS", "MIXED_CASE", "ALL_CAPS", "TECHNICAL_HYPHEN", "UNUSUAL_SYMBOL", "NON_WORD")
    for r, result in zip(selected, actual):
        expected = oracle[r["id"]]
        allowed = {expected_signature(c) for c in expected["all_candidates"] if c["admitted"]}
        signatures = list(map(signature, result["alternatives"]))
        assert len(signatures) <= maximum
        assert all(c in allowed for c in signatures), r["id"]
        assert all(c["repetitionBonus"] == c["repeatedCharacterEdits"] * 0.25 for c in result["alternatives"])
        if expected["completion"] != 0:
            assert result["completion"] == {1: "PROTECTED", 2: "VALID_WORD"}[expected["completion"]]
            assert result["protectedReason"] == (reasons[expected["protected"]] if expected["protected"] >= 0 else None)
            counts["policy"] += 1
        elif result["completion"] == "COMPLETE":
            assert signatures == [expected_signature(c) for c in expected["best"][:maximum]], r["id"]
            assert not result["prohibitsAutoReplace"]
            counts["complete"] += 1
        else:
            assert result["completion"] in ("STATES_EXHAUSTED", "VERIFIED_EXHAUSTED") and result["prohibitsAutoReplace"]
            counts["incomplete"] += 1
    verify_sources()
    assert {p.name: export.sha(p) for p in assets} == receipt["assets"]
    export.write_json(output / "report.json", {"freshExecution": True, "requests": len(actual), "excludedControls": excluded,
        "counts": counts, "violations": 0, "compiledReceipt": export.sha(home / "provenance.json"),
        "archiveSha256": archive.ARCHIVE_SHA, "actualSha256": export.sha(output / "actual.tsv"),
        "scriptSha256": export.sha(Path(__file__)), "noModelOrHoldout": True,
        "maximumAlternatives": maximum, "experiment": receipt.get("experiment")})
    print(f'Fresh full-oracle comparison PASS: {len(actual)} requests, {counts}; 2 controls separately covered in JVM.')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("compiled-export", "output", "index-dir", "rank-dir", "java", "gradle-cache"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--maximum-alternatives", type=int, choices=(1, 3, 7), default=7)
    run(parser.parse_args())
