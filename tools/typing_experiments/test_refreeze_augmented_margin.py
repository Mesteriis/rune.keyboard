import importlib.util
import math
from pathlib import Path
import unittest


SCRIPT = Path(__file__).with_name("refreeze_augmented_margin.py")
SPEC = importlib.util.spec_from_file_location("refreeze_augmented_margin", SCRIPT)
refreeze = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(refreeze)


def record(identifier, margin, correct=True, score=0.8, control=False):
    return {"id": identifier, "family": identifier, "cohort": "typo",
            "topScore": score, "margin": margin, "candidate": identifier,
            "correct": correct, "control": control}


class RefreezeMarginTest(unittest.TestCase):
    def test_moves_strictly_above_disclosed_error(self):
        records = [record(f"good-{index}", 0.6) for index in range(3)]
        records.append(record("bad", 0.4, correct=False))
        margin, metrics = refreeze.select_margin([records], 0.2, 0.3, 2)
        self.assertEqual(math.nextafter(0.4, math.inf), margin)
        self.assertEqual(3, metrics[0]["correctAdditions"])
        self.assertEqual(0, metrics[0]["incorrectAdditions"])

    def test_fails_when_safe_threshold_loses_required_coverage(self):
        records = [record("good", 0.6), record("bad", 0.7, correct=False)]
        with self.assertRaisesRegex(ValueError, "NO_SAFE_MARGIN"):
            refreeze.select_margin([records], 0.2, 0.3, 1)

    def test_keeps_current_margin_without_disclosed_errors(self):
        margin, _ = refreeze.select_margin([[record("good", 0.5)]], 0.2, 0.3, 1)
        self.assertEqual(0.3, margin)


if __name__ == "__main__":
    unittest.main()
