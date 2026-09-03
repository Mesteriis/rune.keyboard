"""Score only actual generated calibration candidates using the exact qualified GGUF."""
import argparse
import json
from pathlib import Path

from calibrate_deterministic import load_verified, evaluator
import export_calibration as export


def requests_from(rows: list[dict], generated: list[dict]) -> list[dict]:
    requests = []
    for row, generation in zip(rows, generated, strict=True):
        export.require(row["split"] == "calibration" and row["id"] == generation["id"], "CALIBRATION_ONLY")
        if not generation["alternatives"]:
            continue
        # Same boundary as TypingSessionController: space is owned prefix, not continuation.
        requests.append({"id": row["id"], "split": "calibration", "prefix": row["prefix"] + " ",
                         "candidates": [generation["original"]] + [c["text"] for c in generation["alternatives"]]})
    return requests


def run(args) -> None:
    root = Path(args.output).resolve()
    export.require(root.is_relative_to(export.REPO / "build"), "BUILD_OUTPUT_REQUIRED")
    rows, generated, receipt = load_verified(Path(args.compiled_export).resolve(strict=True))
    requests = requests_from(rows, generated)
    ev = evaluator()
    identity = ev.cache_identity(requests, Path(args.runner), Path(args.model))
    source_paths = [Path(__file__), Path(__file__).with_name("calibrate_deterministic.py"), export.CORPUS / "evaluate.py"]
    sources = {str(p.relative_to(export.REPO)): export.sha(p) for p in source_paths}
    run_input = {"scope": "generated-calibration-model-scores", "holdoutExecuted": False,
                 "requests": len(requests), "omittedOriginalOnly": len(rows) - len(requests),
                 "maximumAlternatives": receipt["maximumAlternatives"], "identity": identity,
                 "generatorReceiptSha256": export.sha(Path(args.compiled_export) / "provenance.json"),
                 "sources": sources}
    root.mkdir(parents=True, exist_ok=True)
    info = root / "run-input.json"
    if info.exists():
        export.require(json.loads(info.read_text()) == run_input, "RESUME_IDENTITY_MISMATCH")
    else:
        export.write_json(info, run_input)
    ev.score_corpus(requests, Path(args.runner), Path(args.model), root / "scores.jsonl", 60, limit=args.limit)
    export.require(sources == {p: export.sha(export.REPO / p) for p in sources}, "SOURCE_DRIFT")
    export.require(identity == ev.cache_identity(requests, Path(args.runner), Path(args.model)), "EXECUTION_DRIFT")
    _, scores = ev.load_cache(root / "scores.jsonl", requests, identity)
    if len(scores) == len(requests) and not (root / "complete.json").exists():
        export.write_json(root / "complete.json", {**run_input, "scores": len(scores),
            "runtimeErrors": sum("error" in value for value in scores.values()),
            "scoresSha256": export.sha(root / "scores.jsonl")})
    print(f"Validated {len(scores)}/{len(requests)} numeric calibration responses; no holdout or quality claim.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("compiled-export", "output", "runner", "model"):
        parser.add_argument("--" + option, required=True)
    parser.add_argument("--limit", type=int)
    run(parser.parse_args())
