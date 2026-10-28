import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).with_name("evaluate_product_compact_policy.py")
SPEC = importlib.util.spec_from_file_location("evaluate_product_compact_policy", SCRIPT)
evaluation = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(evaluation)


class ProductCompactPolicyTest(unittest.TestCase):
    @staticmethod
    def selected(identifier, word):
        return {"id": identifier, "status": "COMPLETE", "localDecision": None,
            "automaticAdmissionAllowed": True, "automaticAdmissionCandidate": word,
            "fullTokenGeneration": {"compactAlternatives": [{"terminalKey": word}]},
            "candidateView": {"selectedCandidateId": "c", "candidates": [
                {"id": "c", "role": "CORRECTION", "text": word}]},
            "autoEdit": {"correctionGeneration": {}}}

    @staticmethod
    def abstained(identifier):
        return {"id": identifier, "status": "COMPLETE", "localDecision": None,
            "automaticAdmissionAllowed": True, "automaticAdmissionCandidate": None,
            "fullTokenGeneration": {"compactAlternatives": []}, "candidateView": {}, "autoEdit": {}}

    def test_requires_applied_selected_compact_candidate(self):
        observation = {"localDecision": None, "automaticAdmissionAllowed": True,
            "automaticAdmissionCandidate": "слово",
            "fullTokenGeneration": {"compactAlternatives": [{"terminalKey": "слово"}]},
            "candidateView": {"selectedCandidateId": "c", "candidates": [
                {"id": "c", "role": "CORRECTION", "text": "слово"}]},
            "autoEdit": {"correctionGeneration": {}}}
        self.assertEqual("слово", evaluation.compact_selection(observation))
        observation["candidateView"]["selectedCandidateId"] = "original"
        self.assertIsNone(evaluation.compact_selection(observation))

    def test_proposal_can_be_scored_while_release_qualification_blocks_mutation(self):
        observation = self.selected("id", "слово")
        observation["compactPolicyCandidate"] = "слово"
        observation["automaticAdmissionAllowed"] = False
        observation["autoEdit"] = {}
        self.assertIsNone(evaluation.compact_selection(observation))
        self.assertEqual("слово", evaluation.compact_proposal(observation))

    def test_reports_latency_for_full_and_compact_paths(self):
        observations = [
            {"fullTokenGenerationNanos": 10, "fullTokenGeneration": {"compactAlternatives": []},
             "compactPolicyCandidate": None},
            {"fullTokenGenerationNanos": 20,
             "fullTokenGeneration": {"compactAlternatives": [{"terminalKey": "а"}]},
             "compactPolicyCandidate": None},
            {"fullTokenGenerationNanos": 30,
             "fullTokenGeneration": {"compactAlternatives": [{"terminalKey": "б"}]},
             "compactPolicyCandidate": "б"},
        ]

        self.assertEqual(
            {
                "all": {"rows": 3, "p50Nanos": 20, "p95Nanos": 30, "maxNanos": 30},
                "compactPool": {"rows": 2, "p50Nanos": 20, "p95Nanos": 30, "maxNanos": 30},
                "compactSelected": {"rows": 1, "p50Nanos": 30, "p95Nanos": 30, "maxNanos": 30},
            },
            evaluation.generation_latency(observations),
        )

    def test_empty_compact_path_has_explicit_unavailable_percentiles(self):
        self.assertEqual(
            {"rows": 0, "p50Nanos": None, "p95Nanos": None, "maxNanos": None},
            evaluation.generation_latency([{
                "fullTokenGenerationNanos": 10,
                "fullTokenGeneration": {"compactAlternatives": []},
                "compactPolicyCandidate": None,
            }])["compactSelected"],
        )

    def test_cascade_requires_every_legacy_selection_and_only_correct_additions(self):
        rows = [
            {"id": "old", "cohort": "typo", "noAuto": False, "typed": "слво",
             "expectedSpelling": "слово"},
            {"id": "new", "cohort": "typo", "noAuto": False, "typed": "дмо",
             "expectedSpelling": "дом"},
        ]
        legacy = [self.selected("old", "слово"), self.abstained("new")]
        product = [self.selected("old", "слово"), self.selected("new", "дом")]
        report = evaluation.evaluate_legacy_preservation(rows, legacy, product, 1)
        self.assertTrue(report["promotionApproved"])
        self.assertEqual(1, report["correctNewSelections"])

        product[0] = self.abstained("old")
        report = evaluation.evaluate_legacy_preservation(rows, legacy, product, 1)
        self.assertFalse(report["promotionApproved"])
        self.assertTrue(report["rollbackRequired"])
        self.assertEqual("old", report["changedLegacySelections"][0]["id"])


if __name__ == "__main__":
    unittest.main()
