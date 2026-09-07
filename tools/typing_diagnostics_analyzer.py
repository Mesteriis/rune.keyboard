#!/usr/bin/env python3
"""Produce final correction outcomes from opt-in typing diagnostics JSONL exports.

The analyzer only relies on fields introduced by schema 1.  Later schemas may
add fields and are accepted without changing the schema-1 interpretation.
"""
import argparse
import json
import re
from pathlib import Path


CORRECTION_EVENTS = {
    ("BOUNDARY", "AUTO_REPLACE"): "AUTO_REPLACE",
    ("MANUAL", "CORRECTION"): "CORRECTION",
    ("MANUAL", "CONTEXTUAL"): "CONTEXTUAL",
}
ROTATED_JSONL = re.compile(r"^(.*)\.(\d+)\.jsonl$")


def _integer(value, field):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    return value


def _event_fields(event):
    if not isinstance(event, dict):
        raise ValueError("event must be an object")
    schema = _integer(event.get("schema"), "schema")
    if schema < 1:
        raise ValueError("schema must be at least 1")
    kind = event.get("kind")
    reason = event.get("reason")
    if not isinstance(kind, str) or not isinstance(reason, str):
        raise ValueError("kind and reason must be strings")
    return schema, kind, reason, _integer(event.get("session"), "session"), _integer(event.get("revision"), "revision")


def analyze_events(events):
    """Return deterministic, final correction outcomes for events in capture order."""
    schemas = set()
    outcomes = []
    active = {}

    for event in events:
        schema, kind, reason, session, revision = _event_fields(event)
        schemas.add(schema)
        if kind == "SESSION" and reason == "START":
            active.pop(session, None)
            continue

        correction_kind = CORRECTION_EVENTS.get((kind, reason))
        original = event.get("original", "")
        result = event.get("result", "")
        if correction_kind is not None:
            if not isinstance(original, str) or not isinstance(result, str):
                raise ValueError("correction original and result must be strings")
            if original and result and original != result:
                outcome = {
                    "session": session,
                    "initial_revision": revision,
                    "final_revision": revision,
                    "kind": correction_kind,
                    "original": original,
                    "preliminary": result,
                    "final": result,
                    "outcome": "APPLIED",
                }
                outcomes.append(outcome)
                active.setdefault(session, []).append(outcome)
            continue

        if kind == "UNDO" and reason == "ACCEPTED":
            candidates = active.get(session, [])
            previous = next((item for item in reversed(candidates)
                             if item["outcome"] == "APPLIED" and item["initial_revision"] <= revision), None)
            if previous is not None:
                if result and not isinstance(result, str):
                    raise ValueError("undo result must be a string")
                previous["final_revision"] = revision
                previous["final"] = result or previous["original"]
                previous["outcome"] = "UNDONE"

    return {"schemas": sorted(schemas), "outcomes": outcomes}


def _rotation_order(path):
    match = ROTATED_JSONL.match(path.name)
    if match is None:
        return (str(path.parent), path.name, 0)
    # DiagnosticsStorage snapshots parts from the highest index (oldest) to zero.
    return (str(path.parent), match.group(1), -int(match.group(2)))


def load_events(paths):
    events = []
    for path in sorted((Path(path) for path in paths), key=_rotation_order):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            raise ValueError(f"cannot read {path}: {error}") from error
        for number, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{number}: invalid JSON: {error.msg}") from error
    return events


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", required=True, type=Path,
                        help="opt-in text JSONL export; repeat for rotated parts")
    parser.add_argument("--output", required=True, type=Path,
                        help="destination JSON report (use ignored build output for captured text)")
    args = parser.parse_args(argv)
    try:
        report = analyze_events(load_events(args.input))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
