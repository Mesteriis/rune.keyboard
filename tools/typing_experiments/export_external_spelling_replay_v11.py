#!/usr/bin/env python3
"""Replay the frozen v11 external holdout without passing labels to Kotlin."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from fresh_spelling_replay import export


VERSION = 11


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("rows", "manifest", "parquet", "policy", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--java", type=Path,
        default=Path("/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/java"))
    args = parser.parse_args()
    receipt = export(VERSION, Path(__file__), args.rows, args.manifest, args.parquet,
                     args.policy, args.output, args.java)
    print(json.dumps({key: receipt[key] for key in ("rows", "observations", "modelCalls",
                                                    "policySha256")}, sort_keys=True))


if __name__ == "__main__":
    main()
