"""Validate numeric Android requested-width observations, without an energy claim."""
import argparse
import json
from pathlib import Path
import re
from analyze_android import distribution

FIELDS = ("id", "maximum", "round", "wall_ns", "cpu_ns", "states", "verified", "completion", "alternatives")
PATTERN = re.compile(r"INSTRUMENTATION_STATUS: candidate_width_measurement=v1 " +
                     " ".join(fr"{field}=(\d+)" for field in FIELDS))


def report(text):
    if not re.search(r"^OK \(1 test\)$", text, re.M) or "INSTRUMENTATION_CODE: -1" not in text:
        raise ValueError("TEST_NOT_PASSED")
    rows = []
    for line in text.splitlines():
        if "candidate_width_measurement=" not in line:
            continue
        match = PATTERN.fullmatch(line)
        if match is None:
            raise ValueError("NUMERIC_PROTOCOL")
        row = dict(zip(FIELDS, map(int, match.groups())))
        if row["states"] > 8192 or row["verified"] > 64 or row["alternatives"] > row["maximum"] or row["completion"] not in range(5):
            raise ValueError("SEARCH_BOUNDS")
        rows.append(row)
    expected = {(i, width, r) for i in range(60) for width in (1, 3, 7) for r in range(5)}
    keys = [(r["id"], r["maximum"], r["round"]) for r in rows]
    if len(rows) != 900 or len(set(keys)) != 900 or set(keys) != expected:
        raise ValueError("FIXED_SAMPLE_MATRIX")
    for i in range(60):
        for width in (1, 3, 7):
            signatures = {(r["states"], r["verified"], r["completion"], r["alternatives"])
                          for r in rows if r["id"] == i and r["maximum"] == width}
            if len(signatures) != 1:
                raise ValueError("NONREPEATABLE_SEARCH")
    result = {"suitePassed": True, "physicalEnergyQualified": False,
              "uniqueRequests": 60, "warmupPasses": 2, "measuredPasses": 5, "widths": {}}
    for width in (1, 3, 7):
        subset = [r for r in rows if r["maximum"] == width]
        result["widths"][str(width + 1)] = {
            "cpu": distribution([r["cpu_ns"] for r in subset]),
            "wall": distribution([r["wall_ns"] for r in subset]),
            "totalCpuMillis": sum(r["cpu_ns"] for r in subset) / 1_000_000,
            "completeUniqueRequests": len({r["id"] for r in subset if r["completion"] == 0})}
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = report(args.input.read_text())
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
