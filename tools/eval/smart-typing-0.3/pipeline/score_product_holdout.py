#!/usr/bin/env python3
"""Score frozen product holdout candidates with the exact calibration model and runner."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time

import export_calibration as calibration
import export_product_holdout as holdout


def load_verified(directory: Path) -> tuple[list[dict], list[dict], dict]:
    ev, rows = holdout.holdout_rows()
    receipt = json.loads((directory / "provenance.json").read_text())
    calibration.require(receipt.get("scope") == "product-spelling-holdout-candidates"
                        and receipt.get("holdoutExecuted") is True
                        and receipt["holdoutRows"] == ev.digest(rows), "HOLDOUT_RECEIPT")
    for name, key in (("inputs.tsv", "inputs"), ("actual.tsv", "actual"),
                      ("generator.jar", "binary"), ("candidates.jsonl", "candidates")):
        calibration.require(calibration.sha(directory / name) == receipt[key], "HOLDOUT_EXPORT_DIGEST")
    calibration.require(all(calibration.sha(calibration.REPO / name) == digest
                            for name, digest in receipt["sources"].items()), "PRODUCTION_SOURCE_DRIFT")
    generated = calibration.parse_output((directory / "actual.tsv").read_text(), rows)
    stored = [json.loads(line) for line in (directory / "candidates.jsonl").read_text().splitlines()]
    calibration.require(generated == stored and all(result["id"] == row["id"]
                        for row, result in zip(rows, generated, strict=True)), "HOLDOUT_GENERATOR_RECORDS")
    return rows, generated, receipt


def requests_from(rows: list[dict], generated: list[dict]) -> list[dict]:
    requests = []
    for row, result in zip(rows, generated, strict=True):
        calibration.require(row["split"] == "holdout" and row["id"] == result["id"], "HOLDOUT_ONLY")
        if result["alternatives"]:
            requests.append({"id": row["id"], "split": "holdout", "prefix": row["prefix"] + " ",
                "candidates": [result["original"], *(item["text"] for item in result["alternatives"])]})
    return requests


def score_requests(requests: list[dict], runner: Path, model: Path, cache: Path,
                   ev, limit: int | None = None) -> None:
    """Bounded resumable transport; holdout admission was verified before this call."""
    identity = ev.cache_identity(requests, runner, model)
    if cache.exists():
        _, completed = ev.load_cache(cache, requests, identity)
    else:
        cache.parent.mkdir(parents=True, exist_ok=True)
        with cache.open("x", encoding="utf-8") as stream:
            stream.write(ev.canonical({"cacheIdentity": identity}).decode() + "\n")
        completed = {}
    remaining = [request for request in requests if request["id"] not in completed]
    if limit is not None:
        remaining = remaining[:limit]
    if not remaining:
        return
    process = subprocess.Popen([str(runner), str(model)], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    pending = bytearray()
    try:
        with cache.open("a", encoding="utf-8") as stream:
            for ordinal, request in enumerate(remaining, 1):
                payload = {key: request[key] for key in ("id", "prefix", "candidates")}
                process.stdin.write(ev.canonical(payload) + b"\n")
                process.stdin.flush()
                deadline = time.monotonic() + 60
                while b"\n" not in pending:
                    wait = deadline - time.monotonic()
                    if wait <= 0 or not selector.select(wait):
                        raise TimeoutError(f"runner timeout at sample id {request['id']}")
                    block = os.read(process.stdout.fileno(), 65536)
                    if not block:
                        raise RuntimeError(f"runner closed output at sample id {request['id']}")
                    pending.extend(block)
                    calibration.require(len(pending) <= 65536, "RUNNER_RESPONSE_BOUND")
                line, _, tail = pending.partition(b"\n")
                pending = bytearray(tail)
                result = json.loads(line)
                ev.validate_response(request, result)
                stream.write(ev.canonical(result).decode() + "\n")
                stream.flush()
                if ordinal % 100 == 0:
                    print(f"scored {len(completed) + ordinal}/{len(requests)}", file=sys.stderr, flush=True)
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


def run(args) -> None:
    output = Path(args.output).resolve()
    calibration.require(output.is_relative_to(calibration.REPO / "build"), "BUILD_OUTPUT_REQUIRED")
    rows, generated, receipt = load_verified(Path(args.holdout_export).resolve(strict=True))
    requests = requests_from(rows, generated)
    config_path = Path(args.combined_config).resolve(strict=True)
    config = json.loads(config_path.read_text())
    content = {k: v for k, v in config.items() if k != "configSha256"}
    ev = holdout.evaluator()
    calibration.require(ev.digest(content) == config["configSha256"]
                        and config["configSha256"] == receipt["combinedConfigSha256"], "FROZEN_CONFIG")
    runner, model = Path(args.runner).resolve(strict=True), Path(args.model).resolve(strict=True)
    model_identity = config["modelIdentity"]
    calibration.require(calibration.sha(runner) == model_identity["runnerSha256"]
                        and calibration.sha(model) == model_identity["modelSha256"], "FROZEN_MODEL_IDENTITY")
    identity = ev.cache_identity(requests, runner, model)
    run_input = {"scope": "product-spelling-holdout-model-scores", "holdoutExecuted": True,
        "requests": len(requests), "omittedOriginalOnly": len(rows) - len(requests),
        "holdoutGeneratorReceiptSha256": calibration.sha(Path(args.holdout_export) / "provenance.json"),
        "combinedConfigSha256": config["configSha256"], "identity": identity,
        "sources": {str(Path(__file__).resolve().relative_to(calibration.REPO)):
                    calibration.sha(Path(__file__).resolve())}}
    output.mkdir(parents=True, exist_ok=True)
    info = output / "run-input.json"
    if info.exists():
        calibration.require(json.loads(info.read_text()) == run_input, "RESUME_IDENTITY_MISMATCH")
    else:
        calibration.write_json(info, run_input)
    score_requests(requests, runner, model, output / "scores.jsonl", ev, args.limit)
    calibration.require(identity == ev.cache_identity(requests, runner, model), "EXECUTION_DRIFT")
    _, scores = ev.load_cache(output / "scores.jsonl", requests, identity)
    if len(scores) == len(requests) and not (output / "complete.json").exists():
        calibration.write_json(output / "complete.json", {**run_input, "scores": len(scores),
            "runtimeErrors": sum("error" in result for result in scores.values()),
            "scoresSha256": calibration.sha(output / "scores.jsonl")})
    print(f"Validated {len(scores)}/{len(requests)} frozen holdout numeric responses.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("holdout-export", "output", "combined-config", "runner", "model"):
        parser.add_argument("--" + option, required=True)
    parser.add_argument("--limit", type=int)
    run(parser.parse_args())
