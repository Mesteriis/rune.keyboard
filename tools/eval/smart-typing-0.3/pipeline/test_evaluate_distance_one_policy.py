import importlib.util
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("evaluate_distance_one_policy",
    HERE / "evaluate_distance_one_policy.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class DistanceOnePolicyEvaluationTest(unittest.TestCase):
    def test_holdout_counts_precision_undo_and_original(self):
        rows = []
        observations = []
        for language in MODULE.LANGUAGES:
            for split_name in ("calibration", "holdout"):
                for ordinal in range(300):
                    row = {"id": f"{language}-{split_name}-{ordinal}", "split": split_name,
                        "language": language, "cohort": "typo", "family": f"word-{ordinal}",
                        "typed": "mistke", "prefix": "", "expectedSpelling": "mistake", "noAuto": False}
                    qualified = MODULE.QUALIFIED[language]
                    after = "mistake " if qualified else "mistke "
                    rows.append(row)
                    observations.append({"id": row["id"], "status": "COMPLETE",
                        "localDecision": "mistake", "afterBoundary": {"text": after},
                        "autoEdit": {"correctionGeneration": {}} if qualified else None,
                        "restoredBeforeBoundaryExactly": qualified,
                        "candidateView": {"candidates": [{"role": "ORIGINAL", "text": "mistke"}]}})
        result = MODULE.evaluate(rows, observations)["report"]
        self.assertTrue(result["releaseApproved"])
        self.assertEqual(300, result["holdout"]["ru"]["distinctCorrectFamilies"])
        self.assertEqual(1.0, result["holdout"]["es"]["precision"])
        self.assertEqual(0, result["holdout"]["en"]["automaticChanges"])

    def test_qualified_false_change_fails_gate(self):
        rows = [{"id": "x", "split": "holdout", "language": "ru", "cohort": "protected",
            "family": "x", "typed": "Name", "prefix": "", "noAuto": True}]
        observations = [{"id": "x", "status": "COMPLETE", "localDecision": "name",
            "afterBoundary": {"text": "name "}, "restoredBeforeBoundaryExactly": True,
            "autoEdit": {"correctionGeneration": {}},
            "candidateView": {"candidates": [{"role": "ORIGINAL", "text": "Name"}]}}]
        report = MODULE.evaluate(rows, observations)["report"]
        self.assertFalse(report["holdout"]["ru"]["passed"])
        self.assertEqual(1, report["holdout"]["ru"]["protectedChanges"])


if __name__ == "__main__":
    unittest.main()
