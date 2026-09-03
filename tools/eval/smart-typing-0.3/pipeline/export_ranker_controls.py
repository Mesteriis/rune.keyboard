"""Freeze numeric-only controls for the independent Kotlin ranking port."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

import calibrate_deterministic as base
from calibrate_combined import model_proposal
from deterministic_policy import Weights, Thresholds, propose, choose
import export_calibration as export
from score_generated import requests_from


def run(args):
    output = Path(args.output).resolve()
    export.require(output.is_relative_to(export.REPO / "build") and not output.exists(), "FRESH_BUILD_OUTPUT")
    rows, generated, receipt = base.load_verified(Path(args.compiled_export))
    ev = base.evaluator()
    deterministic = json.loads(Path(args.deterministic_config).read_text())
    combined = json.loads(Path(args.combined_config).read_text())
    for config in (deterministic, combined):
        export.require(ev.digest({k: v for k, v in config.items() if k != "configSha256"}) == config["configSha256"], "CONFIG_DIGEST")
    _, scores = ev.load_cache(Path(args.scoring) / "scores.jsonl", requests_from(rows, generated), combined["modelIdentity"])
    export.require(export.sha(Path(args.scoring) / "scores.jsonl") == combined["modelCacheSha256"], "MODEL_CACHE_DIGEST")
    lines = []
    for lang in ("en", "ru", "es"):
        for mode, config in ((0, deterministic), (1, combined)):
            policy = config["languages"][lang]["policy"]
            export.require(policy is not None, "CONTROL_POLICY_REQUIRED")
            numbers = [policy["weights"][k] for k in ("edit", "frequency", "repetition", "fallback", "length")]
            numbers += [policy["thresholds"][k] for k in ("original_penalty", "minimum_margin", "minimum_length")]
            numbers += [policy.get("modelWeight", 0)]
            lines.append("\t".join(map(str, ["P", lang, mode, *numbers])))
    for index, (row, generation) in enumerate(zip(rows, generated, strict=True)):
        lang = row["language"]
        dp, mp = (c["languages"][lang]["policy"] for c in (deterministic, combined))
        det = propose(generation, Weights(**dp["weights"]))
        model = model_proposal(generation, Weights(**mp["weights"]), mp["modelWeight"], scores.get(row["id"]))
        det_id = choose(det, Thresholds(**dp["thresholds"]))
        combined_id = choose(model, Thresholds(**mp["thresholds"])) if model is not None else det_id
        candidates = ";".join(",".join(map(str, [c["id"], int(c["editCost"] * 4), c["frequencyRank"],
            c["repeatedCharacterEdits"], int(c["isFallback"]), c["lengthDifference"]])) for c in generation["alternatives"]) or "-"
        evidence = scores.get(row["id"], {})
        numbers = ";".join(",".join(map(str, [s["id"], s["sumLogProbability"], s["scoredTokenCount"]]))
                           for s in evidence.get("scores", [])) or "-"
        lines.append("\t".join(map(str, ["R", index, lang, len(generation["original"]),
            int(generation["prohibitsAutoReplace"]), candidates, numbers, det_id, combined_id, int(model is not None)])))
    raw = ("\n".join(lines) + "\n").encode("ascii")
    output.mkdir(parents=True)
    (output / "calibration.tsv.gz").write_bytes(gzip.compress(raw, mtime=0))
    export.write_json(output / "manifest.json", {"rows": len(rows), "sha256": hashlib.sha256(raw).hexdigest(),
        "generatorReceiptSha256": export.sha(Path(args.compiled_export) / "provenance.json"),
        "deterministicConfigSha256": deterministic["configSha256"], "combinedConfigSha256": combined["configSha256"],
        "modelCacheSha256": combined["modelCacheSha256"], "scriptSha256": export.sha(Path(__file__)),
        "content": "Numeric ranking features, scores and expected IDs only; no typed text or corpus labels."})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("compiled-export", "scoring", "deterministic-config", "combined-config", "output"):
        parser.add_argument("--" + option, required=True)
    run(parser.parse_args())
