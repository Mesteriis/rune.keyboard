"""Measure exact candidate-set widths2/4/8 (including original) on calibration only."""
import argparse
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location("export_calibration", ROOT / "tools/eval/smart-typing-0.3/pipeline/export_calibration.py")
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)


def once(text, old, new):
    export.require(text.count(old) == 1, "BUDGET_SOURCE_DRIFT")
    return text.replace(old, new)


def changed(text, name, alternatives):
    export.require(alternatives in (1, 3, 7), "CANDIDATE_WIDTH")
    if name == "CandidateGenerator":
        return once(text, "const val MAX_ALTERNATIVES = 7", f"const val MAX_ALTERNATIVES = {alternatives}")
    if name == "PackedTopSeven":
        text = once(text, "selectedCount == 7", "selectedCount == CandidateGenerator.MAX_ALTERNATIVES")
        text = once(text, "result.size == 7", "result.size == CandidateGenerator.MAX_ALTERNATIVES")
        text = once(text, "selected = IntArray(7)", "selected = IntArray(CandidateGenerator.MAX_ALTERNATIVES)")
        return text.replace("SEVEN_IN_GLOBAL_ORDER", "REQUESTED_IN_GLOBAL_ORDER")
    export.require(name == "TopCandidateSelection", "BUDGET_SOURCE")
    return text.replace("SEVEN_IN_GLOBAL_ORDER", "REQUESTED_IN_GLOBAL_ORDER")


def run(args):
    script_sha = export.sha(Path(__file__))
    output = Path(args.output).resolve()
    export.require(output.is_relative_to(ROOT / "build") and not output.exists(), "FRESH_BUILD_OUTPUT")
    output.mkdir(parents=True)
    overrides = {}
    originals = {}
    for name in ("CandidateGenerator", "PackedTopSeven", "TopCandidateSelection"):
        source = ROOT / (export.PRODUCTION + f"smarttyping/lexicon/{name}.kt")
        destination = output / (name + ".kt")
        originals[str(source.relative_to(ROOT))] = export.sha(source)
        destination.write_text(changed(source.read_text(), name, args.candidates - 1))
        overrides[source] = destination
    args.output = str(output / "export")
    export.run(args, overrides, {"name": "exact-candidate-budget", "totalCandidates": args.candidates,
        "maximumAlternatives": args.candidates - 1, "originalSources": originals,
        "productionIntegrated": False, "stateCap": 8192, "verificationCap": 64, "scriptSha256": script_sha})
    export.require(all(export.sha(ROOT / name) == digest for name, digest in originals.items()), "ORIGINAL_SOURCE_DRIFT")
    export.require(script_sha == export.sha(Path(__file__)), "SCRIPT_DRIFT")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "index-dir", "rank-dir", "java", "gradle-cache"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--candidates", type=int, choices=(2, 4, 8), required=True)
    run(parser.parse_args())
