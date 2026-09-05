"""Fixed host-only compiler diagnostic; never a Fold or energy qualification."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import resource
import shlex
import subprocess
import time

from extract_model import MODEL_SHA256, MODEL_SIZE


def digest(path):
    checksum = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def build_identity(directory, expected_flag):
    commands = directory / "compile_commands.json"
    records = json.loads(commands.read_text())
    if not records:
        raise ValueError("Missing compiler records")
    for record in records:
        args = shlex.split(record["command"])
        flags = [arg for arg in args if arg.startswith("-O")]
        if not flags or flags[-1] != expected_flag or "-DNDEBUG" in args:
            raise ValueError("Expected a uniform Debug optimization level with assertions")
    return {"binary_sha256": digest(directory / "rune-score"),
            "commands_sha256": digest(commands), "translation_units": len(records),
            "optimization": expected_flag}


def run(directory, model, identity):
    # Identical to the optional real-model Android regression fixture.
    requests = [{"id": f"compiler-audit-{index}", "prefix": "Пекарь готовит ",
                 "candidates": ["ттесто", "тесто", "место", "тесть"]} for index in range(4)]
    cpu_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    start = time.monotonic()
    completed = subprocess.run(
        [str(directory / "rune-score"), str(model)],
        input="".join(json.dumps(row, ensure_ascii=False) + "\n" for row in requests),
        text=True, capture_output=True, timeout=180, check=False,
    )
    wall = (time.monotonic() - start) * 1000
    cpu_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    if completed.returncode:
        raise ValueError("Host scoring failed")
    rows = [json.loads(line) for line in completed.stdout.splitlines()]
    if len(rows) != len(requests):
        raise ValueError("Incomplete host scoring output")
    for request, row in zip(requests, rows):
        if row.get("id") != request["id"] or "error" in row:
            raise ValueError("Invalid host scoring response identity")
        if [score["id"] for score in row["scores"]] != list(range(4)):
            raise ValueError("Invalid host candidate identities")
        for score in row["scores"]:
            if not math.isfinite(score["sumLogProbability"]) or score["scoredTokenCount"] <= 0:
                raise ValueError("Invalid host score")
        if row["scores"] != rows[0]["scores"]:
            raise ValueError("Repeated host scores changed")
    return {**identity, "first_native_score_ms": rows[0]["durationMillis"],
            "warm_native_score_ms": [row["durationMillis"] for row in rows[1:]],
            "process_wall_ms": round(wall, 3),
            "process_cpu_ms": round(1000 * (cpu_after.ru_utime + cpu_after.ru_stime -
                                           cpu_before.ru_utime - cpu_before.ru_stime), 3),
            "scores": rows[0]["scores"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before-dir", type=Path, required=True)
    parser.add_argument("--after-dir", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; preserve previous evidence")
    if args.model.stat().st_size != MODEL_SIZE or digest(args.model) != MODEL_SHA256:
        parser.error("Exact Rune Text model identity required")
    before_identity = build_identity(args.before_dir, "-O0")
    after_identity = build_identity(args.after_dir, "-O2")
    # Fixed order, one first score plus three repeated warm scores per process.
    before = run(args.before_dir, args.model, before_identity)
    after = run(args.after_dir, args.model, after_identity)
    deltas = []
    for original, optimized in zip(before["scores"], after["scores"]):
        if original["scoredTokenCount"] != optimized["scoredTokenCount"]:
            raise ValueError("Optimization changed scored token counts")
        deltas.append(abs(original["sumLogProbability"] - optimized["sumLogProbability"]))
    report = {"schema": 1, "kind": "host_debug_compiler_diagnostic",
              "model_sha256": MODEL_SHA256, "script_sha256": digest(Path(__file__)),
              "before": before, "after": after, "maximum_sum_delta": max(deltas),
              "limitations": ["Fixed order and one synthetic fixture; no percentile claim",
                              "Host CPU only; no Android, battery, or release acceptance",
                              "Native score excludes model/context construction; process totals include both",
                              "Digest verification warms filesystem before either run"]}
    with args.output.open("x") as output:
        json.dump(report, output, indent=2, allow_nan=False)
        output.write("\n")


if __name__ == "__main__":
    main()
