import importlib.util
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("abstaining_ranker.py")
SPEC = importlib.util.spec_from_file_location("abstaining_ranker", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class AbstainingRankerTest(unittest.TestCase):
    def row(self, **values):
        row = {"id": "case", "typed": "ошбка", "expectedSpelling": "ошибка",
               "cohort": "typo", "noAuto": False, "prefix": "это", "family": "ошибка"}
        row.update(values)
        return row

    def candidate(self, text):
        return {"text": text, "canonicalKey": text, "unitDistance": 1,
                "frequencyRank": 10, "editCost": 1.0, "isFallback": False}

    def test_missing_expected_candidate_trains_explicit_abstention(self):
        group = MODULE.labelled_group(self.row(), [self.candidate("ошибки")], "test")
        self.assertEqual("ошбка", group["candidates"][0]["text"])
        self.assertEqual(0, group["target"])
        self.assertFalse(group["expectedAvailable"])

    def test_available_expected_candidate_remains_positive_target(self):
        group = MODULE.labelled_group(self.row(), [self.candidate("ошибки"),
                                                   self.candidate("ошибка")], "test")
        self.assertEqual(2, group["target"])
        self.assertTrue(group["expectedAvailable"])

    def test_correct_input_always_trains_original_even_if_alternative_matches_label(self):
        row = self.row(typed="сесил", expectedSpelling="сесил", cohort="correct")
        group = MODULE.labelled_group(row, [self.candidate("сесил"),
                                            self.candidate("весил")], "test")
        self.assertEqual(0, group["target"])

    def test_rejected_cases_can_never_enter_development_partition(self):
        self.assertTrue(MODULE.REJECTED_CASES)
        self.assertTrue(all(not MODULE.is_development(identifier)
                            for identifier in MODULE.REJECTED_CASES))


if __name__ == "__main__":
    unittest.main()
