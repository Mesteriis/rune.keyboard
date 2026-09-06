"""Separate state-based annotation; never rewrites the frozen replay report."""
import argparse
import hashlib
import json
from pathlib import Path


def classify(row):
    observation = row["observation"]
    state = observation["stateBeforeCandidates"]
    word = state["typedWord"]
    candidates = observation["candidateView"]["candidates"]
    # Ownership, not presence of a displayed list or model request, determines scope.
    if isinstance(word, str) and word:
        originals = [item for item in candidates if item.get("role") == "ORIGINAL"]
        passed = (state["composingText"] == (state["leadingBoundary"] or "") + word
                  and observation["actualOriginal"] == word
                  and len(originals) == 1 and originals[0].get("text") == word
                  and bool(originals[0].get("id")))
        return "ownedWord", passed
    if word is not None and word != "":
        return "invalidState", False
    prefix = row["input"]["prefix"]
    raw = (prefix + " " if prefix else "") + row["input"]["typed"]
    empty_state = (state["composingText"] is None if word is None else
                   state["composingText"] == state["leadingBoundary"])
    passed = (empty_state and not candidates
              and observation["candidateView"]["selectedCandidateId"] is None
              and observation["actualOriginal"] in (None, "")
              and observation["actualModelRequest"] is None
              and observation["requestToken"] is None
              and observation["autoEdit"] is None
              and observation["beforeBoundary"]["text"] == raw
              and observation["afterBoundary"]["text"] == raw + " "
              and observation["afterBackspace"]["text"] == raw)
    return "noWord", passed


def annotate(rows):
    groups = {}
    seen = set()
    for row in rows:
        key = (row["split"], row["mode"], row["input"]["language"])
        identity = (*key, row["input"]["id"])
        if identity in seen:
            raise ValueError("DUPLICATE_ROW")
        seen.add(identity)
        group = groups.setdefault(key, {"rows": 0, "ownedWord": 0, "noWord": 0,
                                       "invalidState": 0, "passed": 0, "failures": []})
        kind, passed = classify(row)
        group["rows"] += 1
        group[kind] += 1
        group["passed"] += int(passed)
        if not passed:
            group["failures"].append(row["input"]["id"])
    return [{"split": key[0], "mode": key[1], "language": key[2], **value}
            for key, value in sorted(groups.items())]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--report-sha256", required=True)
    parser.add_argument("--rows-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report_bytes = (args.root / "report.json").read_bytes()
    rows_bytes = (args.root / "row-evidence.jsonl").read_bytes()
    if hashlib.sha256(report_bytes).hexdigest() != args.report_sha256:
        raise ValueError("REPORT_DIGEST")
    if hashlib.sha256(rows_bytes).hexdigest() != args.rows_sha256:
        raise ValueError("ROWS_DIGEST")
    report = json.loads(report_bytes)
    groups = annotate(json.loads(line) for line in rows_bytes.splitlines())
    expected = {(s, m, l) for s in ("calibration", "holdout")
                for m in ("ready", "unavailable") for l in ("en", "es", "ru")}
    if {(g["split"], g["mode"], g["language"]) for g in groups} != expected:
        raise ValueError("GROUPS")
    if any(g["rows"] != 2000 for g in groups):
        raise ValueError("ROW_COUNTS")
    result = {
        "schemaVersion": 1, "scope": "state-based-original-contract-annotation",
        "releaseApproved": False, "thresholdFittingPerformed": False,
        "reportSha256": args.report_sha256, "rowsSha256": args.rows_sha256,
        "toolSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "frozenHoldoutGatesUnchanged": {language: values["fixedPointPolicyGates"]
            for language, values in report["holdoutModelReady"]["languages"].items()},
        "groups": groups,
        "limits": ["Separate contract annotation; frozen all-row FAIL remains unchanged.",
                   "Every row remains accounted for; no corpus category or model-request exemption.",
                   "Host candidate identities and exact text; Android tap behavior is separate."]}
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


if __name__ == "__main__":
    main()
