#!/usr/bin/env python3
"""Export passing worker trace JUnit XML, never infer Android or model performance."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

PREFIX = "DUTY_TRACE_V1 "
COSTS = {
    ("EN", 2): (257, 862), ("EN", 4): (469, 1666), ("EN", 8): (1004, 3634),
    ("RU", 2): (600, 2138), ("RU", 4): (1076, 3937), ("RU", 8): (2063, 7656),
    ("ES", 2): (369, 1272), ("ES", 4): (767, 2702), ("ES", 8): (1432, 5263),
}
COUNTS = dict(submitted=11, admitted=6, denied=4, expired=1, cancelled=3,
              completed=2, failed=1, replacedPending=1, boundaryProbes=1,
              simulatedExhaustionTailCpuMillis=100, simulatedExhaustionTailWallMillis=25)
VARIABLES = {"language", "candidates", "usableBefore1000msBoundary", "simulatedCpuMillis",
             "simulatedWallMillis", "finalCreditUnits"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_results(xml_bytes):
    require(len(xml_bytes) <= 1024 * 1024, "oversized JUnit XML")
    root = ET.fromstring(xml_bytes)
    require(root.tag == "testsuite" and root.get("name") ==
            "io.github.mesteriis.rune.keyboard.intelligence.inference.ModelDutyTraceTest",
            "wrong test suite")
    require(int(root.get("tests", "-1")) == 9, "expected nine tests")
    require(all(root.get(key) == "0" for key in ("failures", "errors", "skipped")),
            "suite did not pass completely")
    cases = root.findall("testcase")
    require(len(cases) == 9 and len({case.get("name") for case in cases}) == 9,
            "missing or repeated test cases")
    require(all(root.find(".//" + tag) is None for tag in ("failure", "error", "skipped")),
            "failed or skipped test case")
    rows = {}
    for output in root.findall("system-out"):
        for line in (output.text or "").splitlines():
            if not line.startswith(PREFIX):
                continue
            row = json.loads(line[len(PREFIX):])
            require(isinstance(row, dict) and set(row) == set(COUNTS) | VARIABLES,
                    "unexpected trace schema")
            require(isinstance(row["language"], str), "invalid language")
            require(all(type(value) is int for key, value in row.items() if key != "language"),
                    "non-integer numeric metric")
            key = (row["language"], row["candidates"])
            require(key in COSTS and key not in rows, "unknown or repeated configuration")
            require(all(row[name] == expected for name, expected in COUNTS.items()), "count mismatch")
            wall, cpu = COSTS[key]
            require(row["simulatedCpuMillis"] == 9355 + 2 * cpu and
                    row["simulatedWallMillis"] == 275510 + 2 * wall, "clock total mismatch")
            require(row["usableBefore1000msBoundary"] == int(wall + 25 <= 1000),
                    "boundary count mismatch")
            # At capacity, refill before the 8400 CPU-ms debit is capped away.
            # (8000 - 8400) * 15 + 25 * 2 - 100 * 15 = -7450.
            require(row["finalCreditUnits"] == -7450, "debt mismatch")
            rows[key] = row
    require(set(rows) == set(COSTS), "incomplete nine-configuration trace")
    return [rows[key] for key in sorted(rows)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xml", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    raw = args.xml.read_bytes()
    rows = read_results(raw)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result = {"schemaVersion": 1, "evidenceKind": "virtual-clock-worker-simulation",
              "junitSha256": hashlib.sha256(raw).hexdigest(), "results": rows}
    (args.output_dir / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    lines = ["# CPU duty trace v1 — virtual-clock worker simulation", "",
             "9/9 traces PASS. Each submits 11 requests: 6 engine admissions, 4 denials",
             "(including 1 queue expiry), 3 cancelled engine calls, 2 OK replies, 1 failed",
             "load and 1 replaced pending request. Categories overlap as defined in PROTOCOL.md.", "",
             "| Language | Candidates | Simulated CPU ms | Simulated wall ms | Ready by 1000 ms boundary |",
             "| --- | --- | --- | --- | --- |"]
    for row in rows:
        lines.append(f"| {row['language']} | {row['candidates']} | {row['simulatedCpuMillis']} | "
                     f"{row['simulatedWallMillis']} | {row['usableBefore1000msBoundary']}/1 |")
    lines.extend(["", "Each exhaustion probe ends at -7450 credit units (-496.667 CPU ms). Its",
                  "100 CPU ms / 25 wall ms cancellation tail is injected, not measured.", "",
                  "Only five of nine configured warm-cost boundary probes finish within 1000 ms.",
                  "This motivates nonblocking fallback; it does not estimate production coverage.",
                  "Real CPU/time, Binder tracing, idle unload timing, physical battery, quality",
                  "and the complete device trace experiment remain unqualified.", ""])
    (args.output_dir / "REPORT.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
