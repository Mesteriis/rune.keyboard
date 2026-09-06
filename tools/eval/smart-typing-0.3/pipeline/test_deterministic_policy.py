import unittest
from deterministic_policy import Weights, Thresholds, propose, choose


def generation(alternatives, veto=False):
    return {"original": "czt", "prohibitsAutoReplace": veto, "alternatives": alternatives}


def candidate(cid, rank, cost, repeats=0, fallback=False, length=0):
    return {"id": cid, "frequencyRank": rank, "editCost": cost,
            "repeatedCharacterEdits": repeats, "isFallback": fallback, "lengthDifference": length}


class DeterministicPolicyTest(unittest.TestCase):
    def test_all_features_are_integer_and_directional(self):
        weights = Weights(edit=2, frequency=1, repetition=2, fallback=4, length=1)
        base = propose(generation([candidate(1, 1, 1.0), candidate(2, 8, 1.0)]), weights)
        self.assertEqual((1, 8, 11), (base.candidate_id, base.penalty, base.runner_up_penalty))
        better = propose(generation([candidate(1, 1, 1.0, repeats=1),
                                     candidate(2, 1, 1.0, fallback=True, length=1)]), weights)
        self.assertEqual((1, 6, 13), (better.candidate_id, better.penalty, better.runner_up_penalty))

    def test_both_original_and_runner_up_margins_are_required(self):
        proposal = propose(generation([candidate(1, 1, 1.0), candidate(2, 2, 1.0)]),
                           Weights(2, 1, 0, 0, 0))
        self.assertEqual(0, choose(proposal, Thresholds(20, 2, 1)))
        self.assertEqual(1, choose(proposal, Thresholds(20, 1, 1)))
        self.assertEqual(0, choose(proposal, Thresholds(8, 1, 1)))
        self.assertEqual(0, choose(proposal, Thresholds(20, 1, 4)))

    def test_veto_empty_ties_and_invalid_threshold_abstain_or_fail(self):
        weights = Weights(2, 0, 0, 0, 0)
        self.assertIsNone(propose(generation([], False), weights))
        self.assertIsNone(propose(generation([candidate(1, 1, 1.0)], True), weights))
        tie = propose(generation([candidate(2, 1, 1.0), candidate(1, 1, 1.0)]), weights)
        self.assertEqual(0, choose(tie, Thresholds(20, 1, 1)))
        with self.assertRaises(ValueError):
            choose(tie, Thresholds(20, 0, 1))
        with self.assertRaises(ValueError):
            propose(generation([candidate(1, 1, 0.1)]), weights)
