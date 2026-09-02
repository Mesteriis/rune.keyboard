#!/usr/bin/env python3
"""Validate the complete fixed numeric Android comparison; no device/text identifiers."""
import argparse
import json
import math
from pathlib import Path
import re
import statistics

FIELDS = ("id", "strategy", "round", "wall_ns", "cpu_ns", "states", "verified", "completion", "alternatives")
PATTERN = re.compile(r"INSTRUMENTATION_STATUS: top_seven_measurement=v1 " +
                     " ".join(fr"{field}=(\d+)" for field in FIELDS))


def read_measurements(text):
    rows = []
    for line in text.splitlines():
        if "top_seven_measurement=" not in line:
            continue
        match = PATTERN.fullmatch(line)
        if match is None:
            raise ValueError("NUMERIC_PROTOCOL")
        row = dict(zip(FIELDS, map(int, match.groups())))
        if row["states"] > 8192 or row["verified"] > 64 or row["alternatives"] > 7 or row["completion"] not in range(8):
            raise ValueError("SEARCH_BOUNDS")
        rows.append(row)
    expected = {(i, strategy, r) for i in range(60) for strategy in (0, 1) for r in range(5)}
    identities = [(r["id"], r["strategy"], r["round"]) for r in rows]
    if len(rows) != 600 or len(set(identities)) != 600 or set(identities) != expected:
        raise ValueError("FIXED_SAMPLE_MATRIX")
    return rows


def distribution(values):
    ordered = sorted(v / 1_000_000 for v in values)
    return {"count": len(ordered), "p50Millis": statistics.median(ordered),
            "p95Millis": ordered[math.ceil(0.95 * len(ordered)) - 1], "maxMillis": max(ordered)}


def report(text):
    rows = read_measurements(text)
    result = {"physicalEnergyQualified": False, "measuredPasses": 5, "warmupPasses": 2,
              "uniqueRequests": 60, "suite30Passed": "OK (30 tests)" in text,
              "strategies": {}}
    for strategy, name in ((0, "exhaustive"), (1, "topSeven")):
        selected = [r for r in rows if r["strategy"] == strategy]
        result["strategies"][name] = {"wall": distribution([r["wall_ns"] for r in selected]),
            "cpu": distribution([r["cpu_ns"] for r in selected]),
            "completeUniqueRequests": len({r["id"] for r in selected if r["completion"] == 0})}
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api26", type=Path, required=True)
    parser.add_argument("--api37", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    value = {str(api): report(path.read_text()) for api, path in ((26, args.api26), (37, args.api37))}
    with args.out.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
