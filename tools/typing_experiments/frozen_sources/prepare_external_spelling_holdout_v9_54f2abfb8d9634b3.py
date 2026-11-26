#!/usr/bin/env python3
"""Freeze an independent Russian spelling holdout from public Wikipedia ru-0014."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from fresh_spelling_holdout import HoldoutSpec, prepare


SPEC = HoldoutSpec(
    version=9,
    shard="0014",
    source_sha256="d2ad352beecb92765110e57e8ee9409f4ffe03ff9e4b6ec0640840dec748db18",
    source_bytes=214_902_777,
    seed=921_2026,
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
