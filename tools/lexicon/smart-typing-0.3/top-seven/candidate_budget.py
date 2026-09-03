"""Measure production candidate-set widths2/4/8 (including original) on calibration only."""
import argparse
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location("export_calibration", ROOT / "tools/eval/smart-typing-0.3/pipeline/export_calibration.py")
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)


def maximum_alternatives(candidates):
    export.require(type(candidates) is int and candidates in (2, 4, 8), "CANDIDATE_WIDTH")
    return candidates - 1


def run(args):
    script_sha = export.sha(Path(__file__))
    maximum = maximum_alternatives(args.candidates)
    output = Path(args.output).resolve()
    export.require(output.is_relative_to(ROOT / "build") and not output.exists(), "FRESH_BUILD_OUTPUT")
    output.mkdir(parents=True)
    args.output = str(output / "export")
    args.maximum_alternatives = maximum
    export.run(args, experiment={"name": "exact-candidate-budget", "totalCandidates": args.candidates,
        "maximumAlternatives": maximum, "productionIntegrated": True,
        "stateCap": 8192, "verificationCap": 64, "scriptSha256": script_sha})
    export.require(script_sha == export.sha(Path(__file__)), "SCRIPT_DRIFT")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "index-dir", "rank-dir", "java", "gradle-cache"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--candidates", type=int, choices=(2, 4, 8), required=True)
    run(parser.parse_args())
