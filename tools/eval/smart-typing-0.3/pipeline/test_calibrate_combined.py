import unittest
from calibrate_combined import model_proposal, fit
from deterministic_policy import Weights, Thresholds, choose
from test_deterministic_policy import generation, candidate


def scores(values):
    return {"scores": [{"id": i, "sumLogProbability": value, "scoredTokenCount": count}
                       for i, (value, count) in enumerate(values)]}


class CombinedPolicyTest(unittest.TestCase):
    def test_average_model_evidence_combines_with_integer_features(self):
        generated = generation([candidate(1, 1, 1.0), candidate(2, 8, 1.0)])
        weights = Weights(2, 1, 0, 0, 0)
        evidence = scores([(-20.0, 2), (-7.0, 1), (-3.0, 3)])
        combined = model_proposal(generated, weights, 2, evidence)
        self.assertEqual((2, -7.0, 2.0), (combined.candidate_id, combined.penalty, combined.runner_up_penalty))
        self.assertEqual(2, choose(combined, Thresholds(6, 4, 1)))
        deterministic = model_proposal(generated, weights, 0, evidence)
        self.assertEqual((1, 8.0, 11.0), (deterministic.candidate_id, deterministic.penalty, deterministic.runner_up_penalty))

    def test_unusable_models_and_retrieval_veto_never_create_proposals(self):
        generated = generation([candidate(1, 1, 1.0)])
        weights = Weights(2, 1, 0, 0, 0)
        for evidence in [None, {"error": "SCORING_FAILED"}, scores([(-2.0, 1), (0.0, 0)]),
                         scores([(-1.7e308, 1), (0.0, 1)])]:
            self.assertIsNone(model_proposal(generated, weights, 8, evidence))
        generated["prohibitsAutoReplace"] = True
        self.assertIsNone(model_proposal(generated, weights, 8, scores([(-20.0, 2), (-1.0, 1)])))

    def test_wrong_ids_and_holdout_are_rejected(self):
        with self.assertRaises(ValueError):
            model_proposal(generation([candidate(1, 1, 1.0)]), Weights(2, 1, 0, 0, 0), 1, scores([(-1.0, 1)]))
        with self.assertRaises(ValueError):
            fit([{"split": "holdout"}], [], {})
