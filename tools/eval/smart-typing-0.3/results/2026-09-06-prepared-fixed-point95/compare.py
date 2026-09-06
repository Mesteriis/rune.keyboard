"""Compare existing prepared decisions with the revised point gate; never fit or score."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "2026-09-02"
EXPECTED = {
    "suitability.json": "dd9c8e8cb833b27e4d32491b56727be82cfebbf443e1180b1d7051e79688340a",
    "calibration.json": "bb6241ece4644bd512d670862f8917267001b17a9f19fd8e9a9b03a2c89bd65d",
    "scores.jsonl": "83c0d412804701d105bd14c73c894a7cb1ddf6eab6f5b930511d5bed464a2c02",
}


def main():
    for name, expected in EXPECTED.items():
        actual = hashlib.sha256((SOURCE / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Historical identity mismatch: {name}")
    source = json.loads((SOURCE / "suitability.json").read_text())
    config = json.loads((SOURCE / "calibration.json").read_text())
    rows = {}
    for language, metrics in source["splits"]["holdout"].items():
        precision, false_change = metrics["precision"], metrics["falseChange"]
        count = metrics["automaticReplacements"]
        assert count == precision["denominator"]
        gates = {
            "volume": count >= 300,
            "pointPrecision": count > 0 and precision["numerator"] * 100 >= count * 95,
            "falseChange": false_change["denominator"] > 0 and
                false_change["numerator"] * 200 <= false_change["denominator"],
        }
        rows[language] = {
            "historicalMetricsUnchanged": metrics,
            "revisedPointGates": gates,
            "verdict": "PASS" if all(gates.values()) else "FAIL",
        }
    output = {
        "scope": "Revealed-data, fixed-decision comparison of the historical prepared selector",
        "historicalInputs": EXPECTED,
        "identity": source["identity"],
        "unchangedFrozenConfigSha256": config["frozenConfigSha256"],
        "unchangedLanguageParameters": config["languages"],
        "precisionTargetPercent": 95,
        "minimumChanges": 300,
        "maximumNegativeFalseChange": "1/200",
        "newModelCalls": 0,
        "thresholdFitting": False,
        "decisionChanges": 0,
        "historicalReportModified": False,
        "limitations": source["limitations"],
        "languages": rows,
        "verdict": "PASS" if all(r["verdict"] == "PASS" for r in rows.values()) else "FAIL",
    }
    (HERE / "comparison.json").write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"verdict": output["verdict"], "newModelCalls": 0,
                      "languages": {k: v["revisedPointGates"] for k, v in rows.items()}}))


if __name__ == "__main__":
    main()
