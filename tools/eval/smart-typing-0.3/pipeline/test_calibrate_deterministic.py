import unittest
from calibrate_deterministic import annotations, counts, fit
from deterministic_policy import Proposal, Thresholds


class CalibrationBoundaryTest(unittest.TestCase):
    def test_policy_annotations_never_hide_false_changes(self):
        rows = [dict(cohort="correct", noAuto=False), dict(cohort="protected", noAuto=True),
                dict(cohort="typo", noAuto=True, expectedSpelling="cat"),
                dict(cohort="typo", noAuto=False, expectedSpelling="cat")]
        generated = [dict(alternatives=[dict(id=1, text="cat")])] * len(rows)
        labels = annotations(rows, generated)
        self.assertEqual([(set(), True), (set(), True), (set(), False), ({1}, False)], labels)
        # Same runtime decision for all rows. Policy labels affect metrics only.
        self.assertEqual((4, 1, 2), counts([Proposal(1, 1, None, 3)] * 4, labels, Thresholds(3, 1, 1)))

    def test_holdout_and_mismatched_label_counts_are_rejected(self):
        with self.assertRaises(ValueError):
            fit([dict(split="holdout")], [])
        with self.assertRaises(ValueError):
            annotations([dict(cohort="correct", noAuto=False)], [])
