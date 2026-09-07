#!/usr/bin/env python3
"""Produce final correction outcomes from opt-in typing diagnostics JSONL exports.

Schema 2 pairs final editor responses by operation, session and originating
revision. Only schema-1 records use legacy adjacency rules.
Unknown additive fields remain ignored.
"""
import argparse
import json
import re
from pathlib import Path


CORRECTION_EVENTS = {
    ("MECHANICAL", "AUTO_REPLACE"): "MECHANICAL",
    ("BOUNDARY", "AUTO_REPLACE"): "AUTO_REPLACE",
    ("MANUAL", "CORRECTION"): "CORRECTION",
    ("MANUAL", "CONTEXTUAL"): "CONTEXTUAL",
    ("MANUAL", "ORIGINAL"): "ORIGINAL",
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
    if schema >= 2:
        for name, lower, upper in (("elapsedMs", 0, 60_000), ("scoringCode", -1, 15),
                                   ("requestId", 0, 1_000_000_000), ("candidateCount", 0, 8),
                                   ("selectedIndex", -1, 7)):
            if name in event and not lower <= _integer(event[name], name) <= upper:
                raise ValueError(f"{name} outside bounds")
        enums = {
            "source": {"NONE", "LOCAL_POLICY", "MODEL", "CANONICAL_CASE", "MECHANICAL", "CONTEXTUAL"},
            "completion": {"NONE", "COMPLETE", "PROTECTED", "VALID_WORD", "STATES_EXHAUSTED",
                           "VERIFIED_EXHAUSTED", "CANCELLED", "UNAVAILABLE", "READER_FAILURE"},
        }
        for name, allowed in enums.items():
            if name in event and (not isinstance(event[name], str) or event[name] not in allowed):
                raise ValueError(f"{name} must be a fixed enum")
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
    pending = {}
    operations = {}
    segment_start = {}
    last_start = None

    def finish(attempt, accepted):
        session = attempt["session"]
        revision = attempt["initial_revision"]
        current_segment = revision >= segment_start.get(session, 0)
        if attempt["kind"] == "ORIGINAL":
            # Schema 2 ties Original to the same local allowlist by numeric request ID.
            # A veto, missing lineage, or rejected editor response cannot restore an outcome.
            if accepted and current_segment:
                eligible = [previous for previous in active.get(session, [])
                            if previous["outcome"] == "APPLIED" and previous["initial_revision"] < revision]
                if attempt["_requestId"] is None:
                    # Schema 1 has no request lineage; its accepted adjacent restoration
                    # can reconcile only the most recent matching original/correction pair.
                    restored = [previous for previous in eligible if previous["_requestId"] is None and
                                previous["final"] == attempt["original"] and
                                previous["original"] == attempt["preliminary"]][-1:]
                else:
                    restored = [previous for previous in eligible if attempt["_requestId"] > 0 and
                                previous["_requestId"] == attempt["_requestId"]]
                for previous in restored:
                    previous["final"] = attempt["preliminary"]
                    previous["final_revision"] = revision
                    previous["outcome"] = "RESTORED"
            return
        if not accepted:
            # Refusal can follow an ambiguously applied edit; no readback is allowed.
            attempt["final"] = None
            attempt["outcome"] = "REJECTED"
        elif current_segment:
            active.setdefault(session, []).append(attempt)
        outcomes.append(attempt)

    for event in events:
        schema, kind, reason, session, revision = _event_fields(event)
        schemas.add(schema)
        operation = None
        if schema >= 2 and "operationId" in event:
            operation = _integer(event["operationId"], "operationId")
            if not 0 <= operation <= 1_000_000_000:
                raise ValueError("operationId outside bounds")
        if kind == "SESSION" and reason == "START":
            # Controller revision/session counters advance within one service lifetime.
            # A reset marker revokes every old identity, including a truncated capture
            # whose first START was rotated away. Forward segments retain late responses.
            reset = (last_start is not None and (session < last_start[0] or revision <= last_start[1])) or any(
                key[1] >= revision for key in operations)
            if reset:
                operations.clear(); pending.clear(); active.clear(); segment_start.clear()
            last_start = (session, revision)
            segment_start[session] = revision
            active.pop(session, None)
            pending.pop(session, None)
            continue

        correction_kind = CORRECTION_EVENTS.get((kind, reason))
        original = event.get("original", "")
        result = event.get("result")
        if correction_kind is not None:
            if not isinstance(original, str) or not isinstance(result, str):
                raise ValueError("correction original and result must be strings")
            if original and result and original != result:
                # Correction diagnostics are emitted before the guarded editor mutation.
                # Do not expose an outcome until its next editor revision accepts it.
                attempt = {
                    "session": session,
                    "initial_revision": revision,
                    "final_revision": revision,
                    "kind": correction_kind,
                    "original": original,
                    "preliminary": result,
                    "final": result,
                    "outcome": "APPLIED",
                    "_requestId": event.get("requestId", 0) if schema >= 2 else None,
                }
                if schema >= 2:
                    if operation is not None and operation > 0:
                        operations.setdefault((session, revision, operation), attempt)
                else:
                    pending[session] = attempt
            continue

        if operation is not None and kind == "EDITOR" and reason in ("EDITOR_ACCEPTED", "EDITOR_REJECTED"):
            attempt = operations.pop((session, revision, operation), None)
            if attempt is not None:
                finish(attempt, reason == "EDITOR_ACCEPTED")

        attempt = pending.get(session)
        if attempt is not None and revision >= attempt["initial_revision"] + 1:
            pending.pop(session)
            if schema == 1 and kind == "EDITOR" and reason == "EDITOR_ACCEPTED" and revision == attempt["initial_revision"] + 1:
                finish(attempt, True)

        if kind == "UNDO" and reason == "ACCEPTED":
            if not isinstance(result, str):
                raise ValueError("undo result must be a string")
            candidates = active.get(session, [])
            previous = next((item for item in reversed(candidates)
                             if item["outcome"] == "APPLIED" and item["initial_revision"] <= revision), None)
            if previous is not None:
                previous["final_revision"] = revision
                previous["final"] = result or previous["original"]
                previous["outcome"] = "UNDONE"

    return {"schemas": sorted(schemas), "outcomes": [
        {key: value for key, value in item.items() if key != "_requestId"} for item in outcomes]}


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
