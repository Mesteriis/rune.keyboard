#!/usr/bin/env python3
"""Freeze an independent Russian spelling holdout from public Wikipedia ru-0016."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from fresh_spelling_holdout import HoldoutSpec, prepare


SPEC = HoldoutSpec(
    version=11,
    shard="0016",
    source_sha256="0e2d2100e924ebedb057a37e789fec861fe2b78787c912c266e36eadd8d2e0a7",
    source_bytes=229_151_965,
    seed=923_2026,
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
