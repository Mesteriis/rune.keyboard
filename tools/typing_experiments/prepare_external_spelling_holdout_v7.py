#!/usr/bin/env python3
"""Freeze the next Russian spelling holdout from public Wikipedia ru-0012."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import fresh_spelling_holdout as shared
from fresh_spelling_holdout import HoldoutSpec

common = shared.common
registry_guard = shared.registry_guard

SPEC = HoldoutSpec(
    version=7,
    shard="0012",
    source_sha256="21e33d8a7a0d068e573db688f5816a22fd690bf699dee958373f9b9e957921ad",
    source_bytes=196_511_972,
    seed=619_2026,
)
SOURCE_SHA256 = SPEC.source_sha256
SOURCE_BYTES = SPEC.source_bytes
SOURCE_PATH = SPEC.source_path
SEED = SPEC.seed
TYPO_ROWS = shared.TYPO_ROWS
CORRECT_ROWS = shared.CORRECT_ROWS


def build_rows(pool: list[dict], known: set[str], generator,
               typo_count: int = TYPO_ROWS, correct_count: int = CORRECT_ROWS) -> list[dict]:
    return shared.build_rows(SPEC, pool, known, generator,
                             typo_count=typo_count, correct_count=correct_count)


def prepare(parquet_path: Path, frequency_path: Path, exclusions: list[Path], output: Path, *,
            historical_reproduction: bool = False) -> dict:
    return shared.prepare(SPEC, Path(__file__), parquet_path, frequency_path, exclusions, output,
                          historical_reproduction=historical_reproduction)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parquet", type=Path, required=True)
    parser.add_argument("--frequency", type=Path, required=True)
    parser.add_argument("--exclude-rows", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--historical-reproduction", action="store_true",
                        help="Reproduce disclosed data; never claim independent qualification.")
    args = parser.parse_args()
    result = prepare(args.parquet, args.frequency, args.exclude_rows, args.output,
                     historical_reproduction=args.historical_reproduction)
    print(json.dumps({"counts": result["counts"], "selection": result["selection"],
                      "scope": result["scope"], "independentQualification": result["independentQualification"]},
                     ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
