"""Fresh numeric compatibility replay; no fitting or product qualification."""
from pathlib import Path
import gzip
import hashlib
import json
import subprocess
import sys

REPO = Path(__file__).resolve().parents[3]
PIPELINE = REPO / "tools/eval/smart-typing-0.3/pipeline"
sys.path.insert(0, str(PIPELINE))
import export_calibration as shared
import export_product_holdout as holdout
from score_product_holdout import requests_from, score_requests

ROOT = Path(__file__).resolve().parent
ARCHIVE = PIPELINE / "results/2026-09-03-product-holdout"
RUNNER = REPO / "build/smart-typing-0.3/native-current-20260906/rune-score"
MODEL = REPO / "build/smart-typing-0.3/model/rune-text-v1-0.1.0-q4_k_m.gguf"
CONFIG = PIPELINE / "results/2026-09-03-combined-calibration/config.json"


def main():
    assert shared.sha(RUNNER) == "bc3f78bdf3ac41009a7603ca5dd6b6c4d5e8d6c2bdcaf3a692cfd95a3b3d2553"
    assert shared.sha(ARCHIVE / "candidate-provenance.json") == "a523ac829ac7b25c4b19774e2f9963c0b6b93ba9080f9d730b4b8ee79a848c25"
    assert shared.sha(ARCHIVE / "scores.jsonl.gz") == "98af884c0fd85ce878baa23d0315065611c32aed67e1033f9350b05cbbf5d873"
    config = json.loads(CONFIG.read_text())
    ev, rows = holdout.holdout_rows()
    assert config["configSha256"] == "a4375144211a719aec3fd3e131174e78403fa36de4e234787936bde27aca4bbc"
    assert ev.digest({k: v for k, v in config.items() if k != "configSha256"}) == config["configSha256"]
    prior = json.loads((ARCHIVE / "candidate-provenance.json").read_text())
    cal = json.loads((ROOT / "calibration/provenance.json").read_text())
    assert all(shared.sha(REPO / p) == digest for p, digest in cal["sources"].items())
    for name, key in [("inputs.tsv", "inputs"), ("actual.tsv", "actual"), ("candidates.jsonl", "candidates")]:
        assert shared.sha(ROOT / "holdout" / name) == prior[key]
    generated = shared.parse_output((ROOT / "holdout/actual.tsv").read_text(), rows)
    requests = requests_from(rows, generated)
    assert len(requests) == 2940
    raw = gzip.decompress((ARCHIVE / "scores.jsonl.gz").read_bytes())
    assert hashlib.sha256(raw).hexdigest() == "689545ffd51c3daae20d90ece3f451dee9321c4d70b8425b87c56624a5b862a6"
    records = [json.loads(line) for line in raw.splitlines()]
    old_identity = records[0]["cacheIdentity"]
    identity = ev.cache_identity(requests, RUNNER, MODEL)
    assert all(identity[k] == old_identity[k] for k in ["corpusSha256", "modelSha256", "protocol"])
    assert old_identity["runnerSha256"] == config["modelIdentity"]["runnerSha256"]
    old = {r["id"]: r for r in records[1:]}
    assert len(old) == len(records) - 1 == len(requests)
    for request in requests:
        ev.validate_response(request, old[request["id"]])
    inputs = {str(p.relative_to(REPO)): shared.sha(p) for p in [
        CONFIG, Path(__file__), PIPELINE / "export_calibration.py", PIPELINE / "export_product_holdout.py",
        PIPELINE / "score_product_holdout.py", PIPELINE.parent / "evaluate.py",
        PIPELINE.parent / "scoring.cpp", PIPELINE.parent / "score_main.cpp",
        ROOT / "calibration/provenance.json", ROOT / "holdout/comparison.json",
        REPO / "build/smart-typing-0.3/native-current-20260906/compile_commands.json",
    ]}
    stamp = {"scope": "current-native-numeric-compatibility-replay", "requests": len(requests),
             "identity": identity, "historicalIdentity": old_identity, "inputs": inputs,
             "policyConfigSha256": config["configSha256"], "thresholdFittingPerformed": False,
             "canonicalCaseProvider": "EMPTY", "releaseQualified": False}
    output = ROOT / "native-scores"
    output.mkdir(exist_ok=True)
    receipt = output / "run-input.json"
    if receipt.exists():
        assert json.loads(receipt.read_text()) == stamp
    else:
        assert not (output / "scores.jsonl").exists() and not (output / "complete.json").exists()
        shared.write_json(receipt, stamp)
    score_requests(requests, RUNNER, MODEL, output / "scores.jsonl", ev)
    _, current = ev.load_cache(output / "scores.jsonl", requests, identity)
    assert len(current) == len(requests)
    changed_errors, changed_counts, maximum_delta, changed_numerics = [], [], 0.0, 0
    for request in requests:
        sid = request["id"]
        left, right = old[sid], current[sid]
        if "error" in left or "error" in right:
            if left != right:
                changed_errors.append(sid)
            continue
        for a, b in zip(left["scores"], right["scores"], strict=True):
            assert a["id"] == b["id"]
            if a["scoredTokenCount"] != b["scoredTokenCount"]:
                changed_counts.append([sid, a["id"]])
            delta = abs(a["sumLogProbability"] - b["sumLogProbability"])
            maximum_delta = max(maximum_delta, delta)
            changed_numerics += delta != 0.0
    assert all(shared.sha(REPO / p) == digest for p, digest in inputs.items())
    assert ev.cache_identity(requests, RUNNER, MODEL) == identity
    result = {**stamp, "responses": len(current), "runtimeErrors": sum("error" in r for r in current.values()),
              "changedErrorRows": changed_errors, "changedTokenCounts": changed_counts,
              "changedNumericValues": changed_numerics, "maximumSumDelta": maximum_delta,
              "scoresSha256": shared.sha(output / "scores.jsonl")}
    if not (output / "complete.json").exists():
        shared.write_json(output / "complete.json", result)
    else:
        assert json.loads((output / "complete.json").read_text()) == result
    print(json.dumps({k: result[k] for k in ["responses", "runtimeErrors", "changedNumericValues", "maximumSumDelta", "releaseQualified"]}))


if __name__ == "__main__":
    main()
