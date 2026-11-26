#!/usr/bin/env python3
"""Freeze an independent Russian spelling holdout from public Wikipedia ru-0017."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from fresh_spelling_holdout import HoldoutSpec, prepare


SPEC = HoldoutSpec(
    version=12,
    shard="0017",
    source_sha256="1a5c96dfda452e7725229760347e781b46f88ccd5df4196a5c1a9d46b51b1a65",
    source_bytes=210_166_516,
    seed=924_2026,
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
