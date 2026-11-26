#!/usr/bin/env python3
"""Freeze an independent Russian spelling holdout from public Wikipedia ru-0015."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from fresh_spelling_holdout import HoldoutSpec, prepare


SPEC = HoldoutSpec(
    version=10,
    shard="0015",
    source_sha256="dc248873a3cc80b857f11a0320cfaa889da803eabf09351f1ba8abbf9348eda0",
    source_bytes=219_480_494,
    seed=922_2026,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parquet", type=Path, required=True)
    parser.add_argument("--frequency", type=Path, required=True)
    parser.add_argument("--exclude-rows", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = prepare(SPEC, Path(__file__), args.parquet, args.frequency,
                     args.exclude_rows, args.output)
    print(json.dumps({"counts": result["counts"], "selection": result["selection"]},
                     ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
