"""Compare fixed Android matrices; changed search outcomes cannot count as a speedup."""
import argparse
import hashlib
import json
from pathlib import Path

from analyze_android import distribution, read_measurements


def timings(values):
    return dict(distribution(values), totalMillis=sum(values) / 1_000_000,
                meanMillis=sum(values) / len(values) / 1_000_000)


def compare(before, after):
    for text in (before, after):
        if "OK (2 tests)" not in text or "INSTRUMENTATION_CODE: -1" not in text:
            raise ValueError("INSTRUMENTATION_NOT_PASSED")
    old, new = (read_measurements(text) for text in (before, after))
    identity = lambda r: (r["id"], r["strategy"], r["round"])
    old, new = (sorted(rows, key=identity) for rows in (old, new))
    semantic = ("id", "strategy", "round", "states", "verified", "completion", "alternatives")
    if any(tuple(a[k] for k in semantic) != tuple(b[k] for k in semantic) for a, b in zip(old, new)):
        raise ValueError("SEARCH_OUTCOMES_CHANGED")
    result = {"identicalSearchCountersAndCompletions": True, "observationsPerVariant": 600,
              "uniqueQueries": 60, "strategies": {}}
    for strategy, name in ((0, "exhaustiveControl"), (1, "topSeven")):
        result["strategies"][name] = {
            phase: {metric: timings([r[field] for r in rows if r["strategy"] == strategy])
                    for metric, field in (("cpu", "cpu_ns"), ("wall", "wall_ns"))}
            for phase, rows in (("before", old), ("after", new))}
    return result


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measurements", type=Path, required=True)
    parser.add_argument("--baseline-export", type=Path, required=True)
    parser.add_argument("--current-export", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sources = {}
    report = {"physicalEnergyQualified": False, "holdoutExecuted": False,
              "hostEmulatorsOnly": True, "apis": {}}
    for name in ("candidates.jsonl", "actual.tsv", "inputs.tsv"):
        old, new = (root / name for root in (args.baseline_export, args.current_export))
        if old.read_bytes() != new.read_bytes():
            raise ValueError("CALIBRATION_OUTPUT_CHANGED")
        sources[name] = sha(new)
    for api in (26, 37):
        files = [args.measurements / f"{phase}-api{api}.log" for phase in ("before", "after")]
        report["apis"][str(api)] = compare(*(p.read_text() for p in files))
        sources.update({p.name: sha(p) for p in files})
    sources["apks.json"] = sha(args.measurements / "apks.json")
    sources["script"] = sha(Path(__file__))
    report["sources"] = sources
    report["calibrationByteIdentical"] = True
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


if __name__ == "__main__":
    main()
