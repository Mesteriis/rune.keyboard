import unittest

from candidate_budget import changed, once
from qualify_current import requested_width


class CandidateBudgetContracts(unittest.TestCase):
    def test_width_is_explicit_and_preserves_hard_caps(self):
        for maximum in (1, 3, 7):
            receipt = {"experiment": {"name": "exact-candidate-budget", "maximumAlternatives": maximum,
                "totalCandidates": maximum + 1, "stateCap": 8192, "verificationCap": 64}}
            self.assertEqual(maximum, requested_width(receipt, maximum))
            receipt["experiment"]["verificationCap"] = 65
            with self.assertRaises(AssertionError):
                requested_width(receipt, maximum)

    def test_implicit_smaller_or_mismatched_oracle_is_rejected(self):
        self.assertEqual(7, requested_width({}, 7))
        for value in (1, 3, 0, 8, True):
            with self.assertRaises(AssertionError):
                requested_width({}, value)
        with self.assertRaises(AssertionError):
            requested_width({"experiment": {"name": "exact-candidate-budget", "maximumAlternatives": 7,
                "totalCandidates": 8, "stateCap": 8192, "verificationCap": 64}}, 3)

    def test_source_transform_is_bounded_and_rejects_ambiguous_source(self):
        for maximum in (1, 3, 7):
            self.assertEqual(f"const val MAX_ALTERNATIVES = {maximum}",
                changed("const val MAX_ALTERNATIVES = 7", "CandidateGenerator", maximum))
        for maximum in (0, 2, 8):
            with self.assertRaises(ValueError):
                changed("const val MAX_ALTERNATIVES = 7", "CandidateGenerator", maximum)
        with self.assertRaises(ValueError):
            once("repeat repeat", "repeat", "changed")


if __name__ == "__main__":
    unittest.main()
