import unittest
from score_generated import requests_from


class GeneratedScoringBoundaryTest(unittest.TestCase):
    def test_only_actual_candidates_reach_scorer_without_policy_labels(self):
        rows = [dict(id="x", split="calibration", prefix="The", noAuto=True, expectedSpelling="secret-label",
                     candidates=["injected-label"]), dict(id="y", split="calibration", prefix="The")]
        generations = [dict(id="x", original="czt", alternatives=[dict(text="cat")]),
                       dict(id="y", original="word", alternatives=[])]
        self.assertEqual([dict(id="x", split="calibration", prefix="The ", candidates=["czt", "cat"])],
                         requests_from(rows, generations))

    def test_holdout_and_identity_mismatch_fail_before_scoring(self):
        for row in [dict(id="x", split="holdout"), dict(id="y", split="calibration")]:
            with self.assertRaises(ValueError):
                requests_from([row], [dict(id="x", original="word", alternatives=[])])
