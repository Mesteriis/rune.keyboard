import unittest

from candidate_budget import maximum_alternatives
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

    def test_production_width_is_explicit_and_mismatch_fails(self):
        for total in (2, 4, 8):
            maximum = maximum_alternatives(total)
            receipt = {"harnessWidthArgument": True, "maximumAlternatives": maximum}
            self.assertEqual(maximum, requested_width(receipt, maximum))
            with self.assertRaises(AssertionError):
                requested_width(receipt, 3 if maximum != 3 else 1)
        for total in (0, 1, 3, 7, 9, True):
            with self.assertRaises(ValueError):
                maximum_alternatives(total)


if __name__ == "__main__":
    unittest.main()
