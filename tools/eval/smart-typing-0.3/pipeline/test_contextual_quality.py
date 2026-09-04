import base64
import unittest

from contextual_quality import BOUNDARIES, decisions, metrics, parse_output, requests


def encoded(value): return base64.b64encode(value.encode()).decode()


class ContextualQualityTest(unittest.TestCase):
    def test_exact_seven_variant_protocol_and_expected_boundary_mapping(self):
        row = {"id": "one", "split": "holdout", "language": "en", "prefix": "I think",
               "ambiguous": False, "expectedBoundary": ", "}
        lines = ["R\t0\t7"] + [f"C\t0\t{i}\t{encoded(boundary)}\t{encoded(boundary + 'word')}"
                                    for i, boundary in enumerate(BOUNDARIES)]
        result = parse_output("\n".join(lines), [row])[0]
        self.assertEqual(result["expectedCandidate"], 1)
        self.assertEqual([value["boundary"] for value in result["variants"]], BOUNDARIES)

    def test_strict_original_tie_abstains_and_stable_nonoriginal_tie_uses_lower_id(self):
        records = [{"id": "one"}, {"id": "two"}]
        def response(identifier, values):
            return {"id": identifier, "scores": [{"id": i, "sumLogProbability": value,
                    "scoredTokenCount": 1} for i, value in enumerate(values)], "durationMillis": 1}
        scores = {"one": response("one", [-1, -1, -2, -3, -4, -5, -6]),
                  "two": response("two", [-2, -1, -1, -3, -4, -5, -6])}
        self.assertEqual(decisions(records, scores), [0, 1])

    def test_production_exclusion_is_retained_but_not_scored(self):
        row = {"id": "excluded", "split": "holdout", "language": "en",
               "prefix": "Published in 2011", "ambiguous": False,
               "expectedBoundary": " "}
        result = parse_output("R\t0\t0", [row])[0]
        self.assertEqual([], result["variants"])
        records = [{**result, "id": f"excluded-{index}"} for index in range(600)]
        self.assertEqual([], requests(records, "holdout"))
        self.assertEqual(600, metrics(records, {})["productionExcludedRows"])

    def test_error_abstains(self):
        self.assertEqual(decisions([{"id": "one"}], {"one": {"id": "one", "error": "SCORING_FAILED"}}), [0])


if __name__ == "__main__": unittest.main()
