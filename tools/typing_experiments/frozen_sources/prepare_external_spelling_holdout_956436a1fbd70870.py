#!/usr/bin/env python3
"""Freeze a source-disjoint Russian spelling holdout from public Wikipedia."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import unicodedata


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
GENERATOR = ROOT / "tools/eval/smart-typing-0.3/qualification-v2/generate_corpus.py"
SOURCE_SHA256 = "30a2bd638e0556d1d09d459fd5ef5a4a7accbd54a7cc452798770bd80481dc5f"
SOURCE_BYTES = 200_905_664
SOURCE_REPOSITORY = "https://huggingface.co/datasets/wikimedia/wikipedia"
SOURCE_REVISION = "a634f78b1c435397c07001e175fa74cc4ad5e775"
SOURCE_PATH = "20231101.ru/train/0011.parquet"
FREQUENCY_SHA256 = "6095f507cc167488ec66ada5a85ac50433503a08ad24a07c6eabdf54352c4e7f"
SEED = 609_2026
TYPO_ROWS = 1_000
CORRECT_ROWS = 700


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def load_generator():
    spec = importlib.util.spec_from_file_location("external_holdout_generator", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def excluded_families(paths: list[Path], family_function) -> tuple[set[str], dict[str, str], int]:
    excluded: set[str] = set()
    bindings: dict[str, str] = {}
    rows = 0
    for path in paths:
        resolved = path.resolve(strict=True)
        if not resolved.is_file() or resolved in bindings:
            raise ValueError("EXCLUSION_PATH")
        bindings[str(resolved.relative_to(ROOT)) if resolved.is_relative_to(ROOT) else str(resolved)] = sha256(resolved)
        for row in read_jsonl(resolved):
            value = row.get("family") or row.get("expectedSpelling") or row.get("typed")
            if not isinstance(value, str) or not value:
                raise ValueError(f"EXCLUSION_FAMILY:{resolved.name}")
            excluded.add(family_function(value))
            rows += 1
    if not paths:
        raise ValueError("EXCLUSIONS_REQUIRED")
    return excluded, bindings, rows


def build_rows(pool: list[dict], known: set[str], generator, typo_count: int = TYPO_ROWS,
               correct_count: int = CORRECT_ROWS) -> list[dict]:
    ordered = sorted(pool, key=lambda row: hashlib.sha256(
        f"{SEED}:external-holdout:{row['family']}:{row['selectionHash']}".encode()).digest())
    rows: list[dict] = []
    cursor = 0
    for cohort, required in (("typo", typo_count), ("correct", correct_count)):
        produced = 0
        while produced < required and cursor < len(ordered):
            item = ordered[cursor]
            cursor += 1
            variants = generator.safe_typos(item["word"], "ru", known,
                f"{SEED}:holdout:{cohort}:{item['selectionHash']}")
            if not variants:
                continue
            typo, category = variants[0]
            typed = typo if cohort == "typo" else item["word"]
            candidates = [" " + typo, " " + item["word"]]
            expected = 1
            if cohort == "correct":
                candidates.reverse()
                expected = 0
            row = {
                "ambiguous": False,
                "candidates": candidates,
                "category": category if cohort == "typo" else "correct_word",
                "cohort": cohort,
                "corpusVersion": 6,
                "expectedCandidate": expected,
                "family": item["family"],
                "id": f"ru-holdout-v6-{cohort}-{produced:04d}",
                "language": "ru",
                "noAuto": False,
                "position": "end",
                "prefix": item["prefix"],
                "source": "wikimedia-wikipedia-20231101-ru-0011-external-v6",
                "split": "holdout",
                "task": "spelling",
                "template": f"holdout-wikipedia-{item['selectionHash']}",
                "typed": typed,
                "wordLength": len(item["word"]),
            }
            if cohort == "typo":
                row["expectedSpelling"] = item["word"]
            rows.append(row)
            produced += 1
    if Counter(row["cohort"] for row in rows) != Counter(typo=typo_count, correct=correct_count):
        raise ValueError("INSUFFICIENT_FRESH_HOLDOUT")
    if len({row["family"] for row in rows}) != len(rows):
        raise ValueError("HOLDOUT_FAMILY_OVERLAP")
    return rows


def prepare(parquet_path: Path, frequency_path: Path, exclusions: list[Path], output: Path) -> dict:
    try:
        import pyarrow
        import pyarrow.parquet as parquet
    except ImportError as error:
        raise RuntimeError("pyarrow is required") from error
    source = parquet_path.resolve(strict=True)
    frequency = frequency_path.resolve(strict=True)
    output = output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / "build"):
        raise ValueError("FRESH_BUILD_OUTPUT_REQUIRED")
    if source.stat().st_size != SOURCE_BYTES or sha256(source) != SOURCE_SHA256:
        raise ValueError("PUBLIC_SOURCE_IDENTITY")
    if sha256(frequency) != FREQUENCY_SHA256:
        raise ValueError("PUBLIC_FREQUENCY_IDENTITY")

    generator = load_generator()
    excluded, exclusion_bindings, excluded_rows = excluded_families(exclusions, generator.family)
    known = generator.vocabulary(frequency, "ru")
    best: dict[str, dict] = {}
    articles = 0
    for batch in parquet.ParquetFile(source).iter_batches(batch_size=128, columns=["id", "text"]):
        for article_id, text in zip(batch.column(0).to_pylist(), batch.column(1).to_pylist(), strict=True):
            articles += 1
            for item in generator.spelling_candidates(text or "", "ru", known, excluded, SEED):
                current = best.get(item["family"])
                if current is None or item["selectionHash"] < current["selectionHash"]:
                    best[item["family"]] = item

    rows = build_rows(list(best.values()), known, generator)
    if any(generator.family(row["family"]) in excluded for row in rows):
        raise ValueError("EXCLUDED_FAMILY_SELECTED")
    output.mkdir(parents=True)
    rows_path = output / "rows.jsonl"
    with rows_path.open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(canonical(row).decode("utf-8") + "\n")
    manifest = {
        "schemaVersion": 1,
        "corpusVersion": 6,
        "scope": "independent-ru-spelling-holdout-v6",
        "frozenBeforeScoring": True,
        "containsPersonalMessages": False,
        "labelsRetainedForPythonOnly": True,
        "source": {
            "repository": SOURCE_REPOSITORY,
            "revision": SOURCE_REVISION,
            "path": SOURCE_PATH,
            "bytes": SOURCE_BYTES,
            "sha256": SOURCE_SHA256,
            "license": "CC BY-SA 3.0 and GFDL",
        },
        "frequency": {"path": str(frequency.relative_to(ROOT)) if frequency.is_relative_to(ROOT) else str(frequency),
                      "sha256": FREQUENCY_SHA256},
        "exclusions": {"files": exclusion_bindings, "rows": excluded_rows,
                       "families": len(excluded)},
        "selection": {"seed": SEED, "articlesScanned": articles,
                      "eligibleFamilies": len(best)},
        "generatorRuntime": {"pyarrowVersion": pyarrow.__version__},
        "counts": {"typo": TYPO_ROWS, "correct": CORRECT_ROWS, "total": len(rows)},
        "files": {"rows.jsonl": sha256(rows_path)},
        "sources": {
            str(Path(__file__).resolve().relative_to(ROOT)): sha256(Path(__file__)),
            str(GENERATOR.relative_to(ROOT)): sha256(GENERATOR),
        },
    }
    manifest_path = output / "manifest.json"
    with manifest_path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2,
                                allow_nan=False) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parquet", type=Path, required=True)
    parser.add_argument("--frequency", type=Path, required=True)
    parser.add_argument("--exclude-rows", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.parquet, args.frequency, args.exclude_rows, args.output)
    print(json.dumps({"counts": result["counts"], "selection": result["selection"]},
                     ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
