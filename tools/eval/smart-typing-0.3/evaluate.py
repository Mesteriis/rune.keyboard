#!/usr/bin/env python3
"""Offline, prepared-candidate model suitability evaluation; Python 3.10+ stdlib."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time
import unicodedata
from collections import Counter

ROOT = Path(__file__).resolve().parent
LANGUAGES = ("ru", "en", "es")
FILES = [f"{task}-{lang}.jsonl" for task in ("spelling", "punctuation") for lang in LANGUAGES] + ["protected-tokens.jsonl"]
PROTOCOL = "rune-score-jsonl-v1"
MODEL_SHA256 = "7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4"
MODEL_SIZE = 396704416
ERROR_CODES = {"INVALID_REQUEST", "INVALID_UTF8", "TOO_MANY_CANDIDATES", "CONTEXT_TOO_LONG", "CANCELLED", "TOKENIZE_FAILED", "CONTEXT_CREATE_FAILED", "SCORING_FAILED", "INSUFFICIENT_CONTEXT"}


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def file_hash(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def load_corpus(directory: Path = ROOT) -> list[dict]:
    return [row for name in FILES for row in read_jsonl(directory / name)]


def edit_distance(left: str, right: str) -> int:
    """Optimal string alignment distance with adjacent transposition as one edit."""
    matrix = [[0] * (len(right) + 1) for _ in range(len(left) + 1)]
    for i in range(len(left) + 1):
        matrix[i][0] = i
    for j in range(len(right) + 1):
        matrix[0][j] = j
    for i in range(1, len(left) + 1):
        for j in range(1, len(right) + 1):
            matrix[i][j] = min(matrix[i - 1][j] + 1, matrix[i][j - 1] + 1, matrix[i - 1][j - 1] + (left[i - 1] != right[j - 1]))
            if i > 1 and j > 1 and left[i - 1] == right[j - 2] and left[i - 2] == right[j - 1]:
                matrix[i][j] = min(matrix[i][j], matrix[i - 2][j - 2] + 1)
    return matrix[-1][-1]


def orthographic_base(value: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFD", value.casefold()) if unicodedata.category(char) != "Mn")


def validate(rows: list[dict], minimums: bool = True) -> dict:
    ids, observations = set(), set()
    families = {split: set() for split in ("calibration", "holdout")}
    templates = {split: set() for split in families}
    counts = Counter()
    orthographic_families = {split: set() for split in families}
    orthographic_coverage = Counter()
    for row in rows:
        sid, lang, split = row["id"], row["language"], row["split"]
        if not isinstance(sid, str) or not sid or sid in ids:
            raise ValueError("invalid or duplicate sample id")
        ids.add(sid)
        if row.get("corpusVersion") != 2:
            raise ValueError(f"{sid}: unsupported corpus version")
        if lang not in LANGUAGES or split not in families:
            raise ValueError(f"{sid}: invalid language or split")
        for field in ("family", "template", "source", "category", "prefix"):
            if not isinstance(row.get(field), str) or (field != "prefix" and not row[field]):
                raise ValueError(f"{sid}: invalid {field}")
        families[split].add((lang, row["family"]))
        templates[split].add((lang, row["template"]))
        candidates = row["candidates"]
        if not isinstance(candidates, list) or not 2 <= len(candidates) <= 8:
            raise ValueError(f"{sid}: candidate bound")
        if any(not isinstance(c, str) or not c for c in candidates) or len(set(candidates)) != len(candidates):
            raise ValueError(f"{sid}: empty or duplicate candidate")
        observation = digest([lang, row["prefix"], candidates])
        if observation in observations:
            raise ValueError(f"{sid}: duplicate model observation")
        observations.add(observation)
        expected = row["expectedCandidate"]
        if type(expected) is not int or not 0 <= expected < len(candidates):
            raise ValueError(f"{sid}: invalid label")
        if type(row.get("noAuto")) is not bool:
            raise ValueError(f"{sid}: noAuto must be boolean")
        if row["task"] == "punctuation":
            word = row["currentWord"]
            if not isinstance(word, str) or not word:
                raise ValueError(f"{sid}: currentWord required")
            boundaries = row["boundaries"]
            if boundaries != [" ", ", ", ": ", ". "]:
                raise ValueError(f"{sid}: unsupported punctuation boundaries")
            required = [b + (word[:1].upper() + word[1:] if b == ". " else word) for b in boundaries]
            if candidates != required or row["expectedBoundary"] != boundaries[expected] or not row["noAuto"]:
                raise ValueError(f"{sid}: punctuation changed word or label")
            if type(row.get("ambiguous")) is not bool:
                raise ValueError(f"{sid}: ambiguity must be explicit")
            cohort = "punctuation"
        elif row["task"] == "spelling":
            if candidates[0] != " " + row["typed"]:
                raise ValueError(f"{sid}: original must be candidate zero")
            limit = 1 if len(row["typed"]) < 5 else 2
            if any(not candidate.startswith(" ") or edit_distance(row["typed"].casefold(), candidate[1:].casefold()) > limit for candidate in candidates):
                raise ValueError(f"{sid}: spelling candidate outside bounded edit neighbourhood")
            if row["cohort"] not in ("typo", "correct", "protected"):
                raise ValueError(f"{sid}: invalid cohort")
            if row["cohort"] != "typo" and expected != 0:
                raise ValueError(f"{sid}: no-change label must preserve original")
            if row["cohort"] == "protected" and not row["noAuto"]:
                raise ValueError(f"{sid}: protected token permits auto")
            if row["cohort"] == "typo":
                if expected == 0:
                    raise ValueError(f"{sid}: typo needs a correction")
                if not isinstance(row.get("expectedSpelling"), str) or not row["expectedSpelling"] or candidates[expected] != " " + row["expectedSpelling"]:
                    raise ValueError(f"{sid}: expected spelling and candidate label disagree")
            if "orthographicPolicy" in row:
                alternative, kind = row.get("orthographicAlternative"), row.get("orthographicKind")
                if row["orthographicPolicy"] != "preserve_ambiguous_diacritic_or_yo_e" or row["cohort"] != "protected" or not row["noAuto"] or expected != 0:
                    raise ValueError(f"{sid}: invalid orthographic protection policy")
                if kind not in {"en_optional_accent", "es_ambiguous_accent", "ru_yo_e"} or not isinstance(alternative, str) or alternative == row["typed"] or " " + alternative not in candidates or orthographic_base(alternative) != orthographic_base(row["typed"]):
                    raise ValueError(f"{sid}: missing actual orthographic contrast")
                if kind == "ru_yo_e" and alternative.replace("ё", "е") != row["typed"].replace("ё", "е"):
                    raise ValueError(f"{sid}: invalid yo/e contrast")
                orthographic_families[split].add((lang, orthographic_base(row["typed"])))
                orthographic_coverage[(lang, split, kind)] += 1
            elif row["category"] == "ambiguous_accent":
                raise ValueError(f"{sid}: ambiguous accent category has no authored contrast")
            cohort = "typo" if row["cohort"] == "typo" else "negative"
        else:
            raise ValueError(f"{sid}: unknown task")
        counts[(lang, split, cohort)] += 1
    if orthographic_families["calibration"] & orthographic_families["holdout"]:
        raise ValueError("orthographic-family leakage between splits")
    if families["calibration"] & families["holdout"]:
        raise ValueError("word-family leakage between splits")
    if templates["calibration"] & templates["holdout"]:
        raise ValueError("context-template leakage between splits")
    if minimums:
        for lang in LANGUAGES:
            for split in families:
                for cohort, expected in (("typo", 1000), ("negative", 1000), ("punctuation", 200)):
                    if counts[(lang, split, cohort)] != expected:
                        raise ValueError(f"{lang}/{split}/{cohort}: expected {expected}, got {counts[(lang, split, cohort)]}")
                for kind in ("en_optional_accent", "es_ambiguous_accent", "ru_yo_e"):
                    if not orthographic_coverage[(lang, split, kind)]:
                        raise ValueError(f"{lang}/{split}: missing actual {kind} probes")
                lexical = {r["family"] for r in rows if r["language"] == lang and r["split"] == split and r.get("cohort") == "typo"}
                if len(lexical) < 100:
                    raise ValueError(f"{lang}/{split}: fewer than 100 typo families")
    return {"samples": len(rows), "counts": {"/".join(k): v for k, v in sorted(counts.items())}, "families": {s: len(v) for s, v in families.items()}, "templates": {s: len(v) for s, v in templates.items()}}


def validate_response(row: dict, result: dict) -> None:
    if not isinstance(result, dict) or result.get("id") != row["id"]:
        raise ValueError("runner response id mismatch")
    if "error" in result:
        if set(result) != {"id", "error"} or result["error"] not in ERROR_CODES:
            raise ValueError("malformed runner error")
        return
    if set(result) != {"id", "scores", "durationMillis"}:
        raise ValueError("unexpected response fields (text is forbidden)")
    duration = result["durationMillis"]
    if type(duration) not in (int, float) or not math.isfinite(duration) or duration < 0:
        raise ValueError("invalid duration")
    scores = result["scores"]
    if not isinstance(scores, list) or len(scores) != len(row["candidates"]):
        raise ValueError("candidate count mismatch")
    seen = set()
    for score in scores:
        if not isinstance(score, dict) or set(score) != {"id", "sumLogProbability", "scoredTokenCount"}:
            raise ValueError("unexpected score fields")
        index, total, count = score["id"], score["sumLogProbability"], score["scoredTokenCount"]
        if type(index) is not int or not 0 <= index < len(scores) or index in seen:
            raise ValueError("candidate id mismatch")
        seen.add(index)
        if type(count) is not int or not 0 <= count <= 256 or type(total) not in (int, float) or not math.isfinite(total) or total > 0:
            raise ValueError("invalid numeric score")
        if count == 0 and total != 0:
            raise ValueError("zero-token score has nonzero sum")


def cache_identity(rows: list[dict], runner: Path, model: Path) -> dict:
    if model.stat().st_size != MODEL_SIZE or file_hash(model) != MODEL_SHA256:
        raise ValueError("model must match the frozen Rune Text 0.1 size and digest")
    return {"protocol": PROTOCOL, "corpusSha256": digest(rows), "runnerSha256": file_hash(runner), "modelSha256": MODEL_SHA256}


def load_cache(path: Path, rows: list[dict], identity: dict | None = None) -> tuple[dict, dict]:
    with path.open("rb") as stream:
        stream.seek(0, os.SEEK_END)
        if stream.tell():
            stream.seek(-1, os.SEEK_END)
            if stream.read(1) != b"\n":
                raise ValueError("incomplete cache tail; use --repair-incomplete-tail")
    records = read_jsonl(path)
    if not records or set(records[0]) != {"cacheIdentity"}:
        raise ValueError("cache header missing")
    actual = records[0]["cacheIdentity"]
    if actual.get("protocol") != PROTOCOL or actual.get("corpusSha256") != digest(rows):
        raise ValueError("cache corpus/protocol mismatch")
    if identity is not None and actual != identity:
        raise ValueError("cache executable/model/corpus mismatch")
    by_id = {row["id"]: row for row in rows}
    scores = {}
    for record in records[1:]:
        if record.get("id") not in by_id or record["id"] in scores:
            raise ValueError("cache duplicate or unknown id")
        validate_response(by_id[record["id"]], record)
        scores[record["id"]] = record
    return actual, scores


def repair_incomplete_tail(path: Path, rows: list[dict]) -> bool:
    data = path.read_bytes()
    if not data or data.endswith(b"\n"):
        return False
    boundary = data.rfind(b"\n") + 1
    if boundary == 0:
        raise ValueError("cannot repair missing cache header")
    # Validate all complete records before truncating. No completed result is dropped.
    complete = [json.loads(line) for line in data[:boundary].splitlines()]
    if not complete or set(complete[0]) != {"cacheIdentity"} or complete[0]["cacheIdentity"].get("corpusSha256") != digest(rows):
        raise ValueError("cannot repair mismatched cache")
    by_id = {row["id"]: row for row in rows}
    seen = set()
    for item in complete[1:]:
        if item.get("id") not in by_id or item["id"] in seen:
            raise ValueError("cannot repair malformed completed record")
        validate_response(by_id[item["id"]], item)
        seen.add(item["id"])
    with path.open("r+b") as stream:
        stream.truncate(boundary)
    return True


def score_corpus(rows: list[dict], runner: Path, model: Path, cache: Path, timeout: float, limit: int | None = None, split: str = "calibration", config_path: Path | None = None) -> None:
    identity = cache_identity(rows, runner, model)
    if cache.exists():
        _, completed = load_cache(cache, rows, identity)
    else:
        cache.parent.mkdir(parents=True, exist_ok=True)
        with cache.open("x", encoding="utf-8") as stream:
            stream.write(canonical({"cacheIdentity": identity}).decode() + "\n")
        completed = {}
    if split == "holdout":
        if config_path is None:
            raise ValueError("holdout scoring requires a previously frozen calibration config")
        frozen = json.loads(config_path.read_text(encoding="utf-8"))
        if frozen != calibrate(rows, completed, identity):
            raise ValueError("holdout config does not match completed calibration")
    elif any(row["split"] == "holdout" and row["id"] in completed for row in rows):
        raise ValueError("calibration cannot be resumed after holdout scoring started")
    remaining = [row for row in rows if row["split"] == split and row["id"] not in completed]
    if limit is not None:
        remaining = remaining[:limit]
    if not remaining:
        return
    # stderr is deliberately not retained: only score-only stdout enters the cache.
    process = subprocess.Popen([str(runner.resolve()), str(model.resolve())], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    pending = bytearray()
    try:
        with cache.open("a", encoding="utf-8") as stream:
            for ordinal, row in enumerate(remaining, 1):
                request = {key: row[key] for key in ("id", "prefix", "candidates")}
                process.stdin.write(canonical(request) + b"\n")
                process.stdin.flush()
                deadline = time.monotonic() + timeout
                while b"\n" not in pending:
                    wait = deadline - time.monotonic()
                    if wait <= 0 or not selector.select(wait):
                        raise TimeoutError(f"runner timeout at sample id {row['id']}")
                    block = os.read(process.stdout.fileno(), 65536)
                    if not block:
                        raise RuntimeError(f"runner closed output at sample id {row['id']}")
                    pending.extend(block)
                    if len(pending) > 65536:
                        raise ValueError("runner response exceeds bound")
                line, _, tail = pending.partition(b"\n")
                pending = bytearray(tail)
                result = json.loads(line)
                validate_response(row, result)
                stream.write(canonical(result).decode() + "\n")
                stream.flush()
                if ordinal % 100 == 0:
                    print(f"scored {len(completed) + ordinal}/{len(rows)}", file=sys.stderr, flush=True)
    finally:
        selector.close()
        if process.stdin:
            process.stdin.close()
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        if process.stdout:
            process.stdout.close()


def features(row: dict, response: dict | None) -> dict | None:
    if response is None or "error" in response:
        return None
    validate_response(row, response)
    if any(score["scoredTokenCount"] <= 0 for score in response["scores"]):
        return None
    means = {score["id"]: score["sumLogProbability"] / score["scoredTokenCount"] for score in response["scores"]}
    ranking = sorted(means, key=lambda i: (-means[i], i))
    best = ranking[0]
    margin = means[best] - means[ranking[1]]
    confidence = 1.0 / sum(math.exp(value - means[best]) for value in means.values())
    return {"best": best, "margin": margin, "confidence": confidence}


def automatic(row: dict, feature: dict | None, config: dict) -> bool:
    return bool(feature is not None and row["task"] == "spelling" and not row["noAuto"] and feature["best"] != 0 and feature["margin"] > 0 and feature["margin"] >= config["margin"] and feature["confidence"] >= config["confidence"])


def wilson(successes: int, total: int) -> list[float] | None:
    if not total:
        return None
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    radius = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [max(0.0, center - radius), min(1.0, center + radius)]


def rate(numerator: int, denominator: int) -> dict:
    return {"numerator": numerator, "denominator": denominator, "value": numerator / denominator if denominator else None, "wilson95RowDescriptive": wilson(numerator, denominator)}


def language_metrics(rows: list[dict], scores: dict, config: dict) -> dict:
    spelling = [row for row in rows if row["task"] == "spelling"]
    usable = {row["id"]: features(row, scores.get(row["id"])) for row in rows}
    auto = [row for row in spelling if automatic(row, usable[row["id"]], config)]
    good = sum(usable[row["id"]]["best"] == row["expectedCandidate"] for row in auto)
    negative = [row for row in spelling if row["cohort"] != "typo"]
    changed = {row["id"] for row in auto if row["cohort"] != "typo"}
    typos = [row for row in spelling if row["cohort"] == "typo"]
    eligible_typos = [row for row in typos if not row["noAuto"]]
    punct = [row for row in rows if row["task"] == "punctuation"]
    unambiguous = [row for row in punct if not row["ambiguous"]]
    def top1(subset: list[dict]) -> dict:
        return rate(sum(usable[row["id"]] is not None and usable[row["id"]]["best"] == row["expectedCandidate"] for row in subset), len(subset))
    false_changes = rate(len(changed), len(negative))
    precision = rate(good, len(auto))
    return {
        "automaticReplacements": len(auto), "precision": precision,
        "falseChange": false_changes,
        "falseChangeByCohort": {cohort: rate(sum(row["id"] in changed for row in negative if row["cohort"] == cohort), sum(row["cohort"] == cohort for row in negative)) for cohort in ("correct", "protected")},
        "coverageAllSpelling": rate(len(auto), len(spelling)),
        "abstentionAllSpelling": rate(len(spelling) - len(auto), len(spelling)),
        "preparedOracleCandidateRecall": rate(sum(" " + row["expectedSpelling"] in row["candidates"] for row in typos), len(typos)),
        "typoCorrectionCoverage": rate(sum(row["cohort"] == "typo" and usable[row["id"]]["best"] == row["expectedCandidate"] for row in auto), len(typos)),
        "eligibleTypoCount": len(eligible_typos), "typoCount": len(typos), "negativeCount": len(negative),
        "top1Spelling": top1(spelling), "top1Typo": top1(typos),
        "punctuationSuggestionTop1Unambiguous": top1(unambiguous),
        "punctuationAmbiguousCount": len(punct) - len(unambiguous), "punctuationAutomaticReplacements": 0,
        "rejectedOrMissingScores": sum(value is None for value in usable.values()),
        "runtimeErrors": sum("error" in scores.get(row["id"], {}) for row in rows),
        "missingScores": sum(row["id"] not in scores for row in rows),
        "wordFamilies": len({row["family"] for row in spelling}),
        "typoWordFamilies": len({row["family"] for row in typos}),
        "contextTemplates": len({row["template"] for row in rows}),
        "automaticReplacementFamilies": len({row["family"] for row in auto}),
        "falsePositiveIds": [row["id"] for row in auto if usable[row["id"]]["best"] != row["expectedCandidate"]],
        "passesRowGate": len(auto) >= 300 and good / len(auto) >= .99 and len(changed) / len(negative) <= .005 if auto and negative else False,
    }


def calibrate(rows: list[dict], scores: dict, identity: dict) -> dict:
    calibration = [row for row in rows if row["split"] == "calibration"]
    if any(row["id"] not in scores for row in calibration):
        raise ValueError("calibration scores incomplete")
    configs = {}
    # Fixed search grid was authored before scoring. No holdout labels/scores consulted.
    for lang in LANGUAGES:
        subset = [row for row in calibration if row["language"] == lang and row["task"] == "spelling"]
        prepared = [(row, features(row, scores[row["id"]])) for row in subset]
        candidates = []
        for margin in (0.0, .1, .2, .4, .6, .8, 1., 1.5, 2., 3., 4., 8., 16., 1e9):
            for confidence in (0.0, .5, .6, .7, .8, .9, .95, .99, 1.):
                config = {"margin": margin, "confidence": confidence}
                auto = [(row, feature) for row, feature in prepared if automatic(row, feature, config)]
                correct = sum(feature["best"] == row["expectedCandidate"] for row, feature in auto)
                negative_count = sum(row["cohort"] != "typo" for row in subset)
                false_changes = sum(row["cohort"] != "typo" for row, _ in auto)
                if auto and correct / len(auto) >= .99 and negative_count and false_changes / negative_count <= .005:
                    candidates.append((len(auto), margin, confidence, config))
        configs[lang] = max(candidates, key=lambda item: item[:3])[3] if candidates else {"margin": 1e9, "confidence": 1.0}
    calibration_scores = [scores[row["id"]] for row in calibration]
    config = {"version": 1, "protocol": PROTOCOL, "modelSha256": identity["modelSha256"], "runnerSha256": identity["runnerSha256"], "calibrationCorpusSha256": digest(calibration), "calibrationScoresSha256": digest(calibration_scores), "languages": configs, "confidenceMeaning": "softmax of average log probabilities; not an empirical correctness probability"}
    return {**config, "frozenConfigSha256": digest(config)}


def report(rows: list[dict], scores: dict, identity: dict, frozen: dict) -> dict:
    content = {key: value for key, value in frozen.items() if key != "frozenConfigSha256"}
    if frozen["frozenConfigSha256"] != digest(content):
        raise ValueError("frozen configuration modified")
    expected = calibrate(rows, scores, identity)
    if frozen != expected:
        raise ValueError("frozen configuration does not match calibration-only evidence")
    result = {"version": 2, "scope": "prepared-candidate synthetic stress suitability only", "identity": identity, "frozenConfigSha256": frozen["frozenConfigSha256"], "limitations": ["Rows share lexical families and authored context templates; Wilson intervals describe row counts and are not independent-sample confidence guarantees.", "Synthetic typo and protected-token distributions do not represent real typing. Prepared candidates do not test production candidate generation.", "noAuto is an authored policy annotation. Production protection detection is not implemented or evaluated.", "Punctuation ambiguity is authored; ambiguous rows have no single correct suggestion and are excluded from suggestion accuracy.", "Runtime errors and zero-token scores abstain and remain in metric denominators.", "Abstention uses all spelling rows, including protected, error and missing-score rows. Prepared oracle candidate recall uses all typo rows; expected spellings are injected by construction, so 100% is not production candidate-generator evidence."], "splits": {}}
    for split in ("calibration", "holdout"):
        result["splits"][split] = {lang: language_metrics([row for row in rows if row["split"] == split and row["language"] == lang], scores, frozen["languages"][lang]) for lang in LANGUAGES}
    complete = all(row["id"] in scores for row in rows)
    result["allScoresPresent"] = complete
    result["preparedCandidateRowGatePass"] = complete and all(metrics["passesRowGate"] for metrics in result["splits"]["holdout"].values())
    result["productionQualified"] = False
    return result


def markdown_report(value: dict) -> str:
    lines = ["# Rune Text 0.1 prepared-candidate suitability", "", f"Row gate: **{'PASS' if value['preparedCandidateRowGatePass'] else 'FAIL'}**. Production qualification: **not established**.", "", "Lexical families and templates repeat. Wilson 95% intervals below are row-level descriptive intervals, not independent-sample guarantees.", "", "| Split | Language | Auto | Precision (correct/auto) | False change (changed/negative) | Correct-only false change | Typo coverage | Families with auto | Rejected/missing |", "| --- | --- | ---: | --- | --- | --- | --- | ---: | ---: |"]
    def cell(metric: dict) -> str:
        if metric["value"] is None:
            return f"undefined (0/{metric['denominator']})"
        lo, hi = metric["wilson95RowDescriptive"]
        return f"{100*metric['value']:.2f}% ({metric['numerator']}/{metric['denominator']}); [{100*lo:.2f}, {100*hi:.2f}]%"
    for split, languages in value["splits"].items():
        for lang, metric in languages.items():
            lines.append(f"| {split} | {lang} | {metric['automaticReplacements']} | {cell(metric['precision'])} | {cell(metric['falseChange'])} | {cell(metric['falseChangeByCohort']['correct'])} | {cell(metric['typoCorrectionCoverage'])} | {metric['automaticReplacementFamilies']} | {metric['rejectedOrMissingScores']} |")
    lines += ["", "## Abstention and prepared candidate containment", "", "Abstention counts every spelling row without an automatic replacement, including policy-protected and rejected/missing-score rows. Prepared oracle candidate recall counts typo rows whose independently recorded expected spelling is present in the prepared set. Expected candidates are injected by construction; 100% does not evaluate production candidate generation or model ranking.", "", "| Split | Language | Abstention (no auto/all spelling) | Prepared oracle candidate recall (contained/all typos) |", "| --- | --- | --- | --- |"]
    for split, languages in value["splits"].items():
        for lang, metric in languages.items():
            lines.append(f"| {split} | {lang} | {cell(metric['abstentionAllSpelling'])} | {cell(metric['preparedOracleCandidateRecall'])} |")
    lines += ["", "## Suggestion and raw ranking", "", "| Split | Language | Typo top-1 | Unambiguous punctuation top-1 | Ambiguous punctuation excluded | Typo families | Templates |", "| --- | --- | --- | --- | ---: | ---: | ---: |"]
    for split, languages in value["splits"].items():
        for lang, metric in languages.items():
            lines.append(f"| {split} | {lang} | {cell(metric['top1Typo'])} | {cell(metric['punctuationSuggestionTop1Unambiguous'])} | {metric['punctuationAmbiguousCount']} | {metric['typoWordFamilies']} | {metric['contextTemplates']} |")
    lines += ["", "## Evidence", "", f"Frozen calibration: `{value['frozenConfigSha256']}`", "", "```json", json.dumps(value["identity"], indent=2), "```", "", "## Limits", ""] + ["- " + item for item in value["limitations"]]
    lines += ["", "False positives (sample IDs only):", ""]
    for lang, metric in value["splits"]["holdout"].items():
        lines.append(f"- {lang}: {', '.join(metric['falsePositiveIds']) or 'none among automatic replacements'}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=ROOT)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate")
    score = commands.add_parser("score")
    score.add_argument("--runner", type=Path, required=True)
    score.add_argument("--model", type=Path, required=True)
    score.add_argument("--cache", type=Path, required=True)
    score.add_argument("--timeout", type=float, default=120)
    score.add_argument("--limit", type=int, help="bounded smoke run; resume uses same cache")
    score.add_argument("--split", choices=("calibration", "holdout"), required=True)
    score.add_argument("--config", type=Path, help="required frozen calibration config for holdout")
    score.add_argument("--repair-incomplete-tail", action="store_true", help="truncate only a final unterminated cache line after validating complete records")
    freeze = commands.add_parser("calibrate")
    freeze.add_argument("--cache", type=Path, required=True)
    freeze.add_argument("--out", type=Path, required=True)
    make_report = commands.add_parser("report")
    make_report.add_argument("--cache", type=Path, required=True)
    make_report.add_argument("--config", type=Path, required=True)
    make_report.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    rows = load_corpus(args.corpus)
    summary = validate(rows)
    if args.command == "validate":
        print(json.dumps(summary, indent=2))
        return 0
    if args.command == "score":
        if not math.isfinite(args.timeout) or args.timeout <= 0 or (args.limit is not None and args.limit <= 0):
            raise ValueError("timeout/limit must be positive")
        if args.repair_incomplete_tail and args.cache.exists():
            repair_incomplete_tail(args.cache, rows)
        score_corpus(rows, args.runner, args.model, args.cache, args.timeout, args.limit, args.split, args.config)
        return 0
    identity, scores = load_cache(args.cache, rows)
    if args.command == "calibrate":
        if any(row["split"] == "holdout" and row["id"] in scores for row in rows):
            raise ValueError("cannot freeze thresholds after holdout scoring started")
        value = calibrate(rows, scores, identity)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        # A frozen file is immutable by this command; new experiments need new paths.
        with args.out.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(value, indent=2) + "\n")
        return 0
    frozen = json.loads(args.config.read_text(encoding="utf-8"))
    value = report(rows, scores, identity, frozen)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    args.out.with_suffix(".md").write_text(markdown_report(value), encoding="utf-8")
    return 0 if value["preparedCandidateRowGatePass"] else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, TimeoutError, RuntimeError) as error:
        print(f"evaluation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
