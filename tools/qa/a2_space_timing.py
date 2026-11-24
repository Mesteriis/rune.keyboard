#!/usr/bin/env python3
"""Summarize a predefined matrix of one-Space Perfetto captures."""

import argparse
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess


KEY = "Rune#modelSpaceKey"
REQUEST = "Rune#modelSpaceRequest"
RESULT = "Rune#modelSpaceScoreOk"
DEADLINE = "Rune#modelSpaceDeadline"
CONTEXT_TOO_LONG = "Rune#modelSpaceContextTooLong"
SCORING_ERROR = "Rune#modelSpaceScoringError"
TERMINAL_OUTCOMES = {RESULT: "completed", DEADLINE: "deadline_missed",
                     CONTEXT_TOO_LONG: "context_too_long", SCORING_ERROR: "scoring_error"}
MARKERS = (KEY, REQUEST, *TERMINAL_OUTCOMES)
CELLS = [(mode, size) for mode in ("off", "on") for size in (300, 600, 1000)]
PACKAGES = {"io.github.mesteriis.rune.keyboard", "io.github.mesteriis.rune.keyboard.qualification"}
GRACE_NS = 250_000_000


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def query(package):
    if package not in PACKAGES:
        raise ValueError("expected a Rune debug package")
    names = ", ".join(f"'{name}'" for name in MARKERS)
    return f"""
        SELECT s.name, s.ts, s.dur, p.upid, b.end_ts AS trace_end
        FROM slice s
        JOIN thread_track tt ON tt.id = s.track_id
        JOIN thread t ON t.utid = tt.utid
        JOIN process p ON p.upid = t.upid
        CROSS JOIN trace_bounds b
        WHERE p.name = '{package}' AND t.tid = p.pid AND s.name IN ({names})
        ORDER BY s.ts, s.id
    """


def measure(csv_text):
    reader = csv.DictReader(io.StringIO(csv_text))
    if reader.fieldnames != ["name", "ts", "dur", "upid", "trace_end"]:
        return "invalid_capture", None
    by_name = {}
    owners = set()
    ends = set()
    for row in reader:
        name = row["name"]
        if name not in MARKERS or name in by_name:
            return "invalid_capture", None
        try:
            timestamp, duration, owner, end = (int(row[key]) for key in ("ts", "dur", "upid", "trace_end"))
        except (ValueError, TypeError):
            return "invalid_capture", None
        if None in row or duration < 0 or timestamp < 0 or end < timestamp + duration:
            return "invalid_capture", None
        by_name[name] = (timestamp, duration)
        owners.add(owner)
        ends.add(end)

    if KEY not in by_name or len(owners) != 1 or len(ends) != 1:
        return "invalid_capture", None
    start, key_duration = by_name[KEY]
    if ends.pop() < start + GRACE_NS:
        return "incomplete_capture", None
    if REQUEST not in by_name:
        return ("no_admission" if len(by_name) == 1 else "invalid_capture"), None
    request, request_duration = by_name[REQUEST]
    terminal = [name for name in TERMINAL_OUTCOMES if name in by_name]
    if request < start + key_duration or len(terminal) > 1:
        return "invalid_capture", None
    if not terminal:
        return "no_terminal_marker", None
    name = terminal[0]
    timestamp, duration = by_name[name]
    if timestamp < request + request_duration:
        return "invalid_capture", None
    return TERMINAL_OUTCOMES[name], timestamp + duration - start if name == RESULT else None


def load_plan(manifest):
    data = json.loads(manifest.read_bytes())
    if set(data) != {"schema", "package", "attemptsPerCell", "attempts"} or data["schema"] != 1:
        raise ValueError("invalid timing manifest")
    planned = data["attemptsPerCell"]
    if type(planned) is not int or planned < 1:
        raise ValueError("invalid planned attempt count")
    directory = manifest.parent.resolve()
    rows = []
    seen_paths = set()
    for row in data["attempts"]:
        if set(row) != {"mode", "characters", "trace"}:
            raise ValueError("invalid timing attempt")
        mode, characters, name = row["mode"], row["characters"], row["trace"]
        if (mode, characters) not in CELLS or type(characters) is not int:
            raise ValueError("unknown timing cell")
        path = None
        if name is not None:
            relative = Path(name)
            path = (directory / relative).resolve()
            if relative.is_absolute() or not path.is_relative_to(directory) or path in seen_paths:
                raise ValueError("invalid or repeated capture path")
            seen_paths.add(path)
        rows.append(((mode, characters), path))
    if Counter(cell for cell, _ in rows) != {cell: planned for cell in CELLS}:
        raise ValueError("incomplete timing plan")
    return query(data["package"]), rows


def summarize(manifest, processor):
    manifest_sha = sha256(manifest)
    processor_sha = sha256(processor)
    sql, rows = load_plan(manifest)
    counts = {cell: Counter() for cell in CELLS}
    durations = {cell: [] for cell in CELLS}
    hashes = set()
    for cell, path in rows:
        outcome, duration = "missing_capture", None
        if path is not None and path.is_file():
            digest = sha256(path)
            if digest in hashes:
                raise ValueError("repeated trace bytes")
            hashes.add(digest)
            try:
                result = subprocess.run([processor, "query", path, sql], text=True,
                                        capture_output=True, timeout=60)
                outcome, duration = (measure(result.stdout) if result.returncode == 0
                                     else ("invalid_capture", None))
            except subprocess.TimeoutExpired:
                outcome = "invalid_capture"
            if digest != sha256(path):
                raise ValueError("trace changed during analysis")
        counts[cell][outcome] += 1
        if duration is not None:
            durations[cell].append(duration)

    complete = True
    cells = []
    for (mode, characters), outcomes in counts.items():
        samples = sorted(durations[mode, characters])
        attempts = sum(outcomes.values())
        measured = sum(outcomes[name] for name in TERMINAL_OUTCOMES.values())
        unresolved = attempts - measured - outcomes["no_admission"]
        complete &= bool(samples) and unresolved == 0
        cells.append(dict(mode=mode, characters=characters, attempts=attempts,
                          observedAdmissions=measured + outcomes["no_terminal_marker"],
                          outcomes=dict(sorted(outcomes.items())),
                          p95Ms=samples[(95 * len(samples) + 99) // 100 - 1] / 1_000_000 if samples else None,
                          deadlineMisses=outcomes["deadline_missed"], deadlineDenominator=measured,
                          deadlineMissRate=outcomes["deadline_missed"] / measured if measured else None,
                          unresolvedAttempts=unresolved))
    if manifest_sha != sha256(manifest) or processor_sha != sha256(processor):
        raise ValueError("plan or trace processor changed during analysis")
    return dict(schema=1, complete=complete, cells=cells, traceProcessorSha256=processor_sha,
                manifestSha256=manifest_sha)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--trace-processor", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = summarize(args.manifest.resolve(strict=True), args.trace_processor.resolve(strict=True))
    except (OSError, TypeError, ValueError) as error:
        parser.exit(2, f"A2 trace analysis failed ({type(error).__name__})\n")
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
