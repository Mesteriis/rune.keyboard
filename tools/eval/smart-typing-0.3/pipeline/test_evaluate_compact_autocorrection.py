import importlib.util
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("evaluate_compact_autocorrection.py")
SPEC = importlib.util.spec_from_file_location("evaluate_compact_autocorrection", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def record(identifier, top, margin, correct=True, cohort="typo"):
    return {
        "id": identifier,
        "family": identifier,
        "topScore": top,
        "margin": margin,
        "correct": correct,
        "control": cohort in {"correct", "protected"},
        "cohort": cohort,
    }


class CompactAutocorrectionEvaluationTest(unittest.TestCase):
    def test_singleton_requires_complete_full_generation(self):
        self.assertFalse(MODULE.structurally_eligible(1, "STATES_EXHAUSTED"))
        self.assertFalse(MODULE.structurally_eligible(1, "VERIFIED_EXHAUSTED"))
        self.assertTrue(MODULE.structurally_eligible(1, "COMPLETE"))
        self.assertTrue(MODULE.structurally_eligible(2, "STATES_EXHAUSTED"))

    def test_calibration_selects_zero_regression_thresholds(self):
        records = [
            record("a", .8, .7),
            record("b", .7, .6),
            record("c", .6, .5),
            record("wrong", .9, .4, correct=False),
            record("control", .95, .3, correct=False, cohort="correct"),
        ]
        policy, metrics = MODULE.calibrate(records, minimum_additions=3)
        self.assertEqual(metrics["additions"], 3)
        self.assertEqual(metrics["incorrectAdditions"], 0)
        self.assertEqual(metrics["controlChanges"], 0)
        self.assertEqual(policy["score"], "combinedScore")
        self.assertGreaterEqual(policy["minimumMargin"], .5)

    def test_promotion_rolls_back_after_any_new_incorrect_change(self):
        active = MODULE.automatic_metrics(changes=100, correct=100, control_changes=0)
        proposed = MODULE.automatic_metrics(changes=112, correct=111, control_changes=0)
        decision = MODULE.promotion_decision(active, proposed, additions=12,
            minimum_additions=1)
        self.assertFalse(decision["promotionApproved"])
        self.assertTrue(decision["rollbackRequired"])
        self.assertIn("INCORRECT_CHANGES_INCREASED", decision["refusals"])

    def test_promotion_requires_real_improvement_and_preserves_controls(self):
        active = MODULE.automatic_metrics(changes=100, correct=98, control_changes=0)
        improved = MODULE.automatic_metrics(changes=112, correct=110, control_changes=0)
        accepted = MODULE.promotion_decision(active, improved, additions=12,
            minimum_additions=10)
        self.assertTrue(accepted["promotionApproved"])
        self.assertFalse(accepted["rollbackRequired"])

        control_regression = MODULE.automatic_metrics(changes=112, correct=110,
            control_changes=1)
        rejected = MODULE.promotion_decision(active, control_regression, additions=12,
            minimum_additions=10)
        self.assertFalse(rejected["promotionApproved"])
        self.assertIn("CONTROL_CHANGES_INCREASED", rejected["refusals"])

    def test_frozen_strict_admission_is_applied_to_holdout_records(self):
        row = {
            "id": "case", "split": "holdout", "language": "ru", "family": "case",
            "cohort": "typo", "noAuto": False, "typed": "ошбка", "expectedSpelling": "ошибка",
        }
        observation = {
            "id": "case", "split": "holdout", "status": "COMPLETE", "localDecision": None,
            "compactSourceMorphology": {"available": True, "present": False},
            "fullTokenGeneration": {"completion": "COMPLETE"},
            "compactScores": [{"canonicalKey": "ошибка", "combinedScore": 1.0,
                "strictAdmissionAllowed": False}],
        }
        self.assertEqual(1, len(MODULE.compact_records([row], [observation], "holdout",
            require_strict_admission=False)))
        self.assertEqual([], MODULE.compact_records([row], [observation], "holdout",
            require_strict_admission=True))


if __name__ == "__main__":
    unittest.main()
