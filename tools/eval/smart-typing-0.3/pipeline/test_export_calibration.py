import base64
import copy
import unittest

from pathlib import Path
from export_calibration import REPO, parse_output, selected_sources, summarize


def enc(s):
    return base64.b64encode(s.encode()).decode()


ROW = {"id": "en-calibration-test", "typed": "helo", "language": "en", "cohort": "typo", "expectedSpelling": "hello"}
RECORD = "R\t0\tCOMPLETE\tfalse\tfalse\t12\t1\tNONE\t1\n"
CANDIDATE = f"C\t0\t1\t{enc('hello')}\t{enc('hello')}\t{enc('hello')}\ten\tfalse\t4\t10\t1\t1.0\t1\t0.25\t1\tLOWER\n"


class ExportContractTest(unittest.TestCase):
    def test_experimental_sources_require_explicit_identity_and_known_scoped_paths(self):
        source = REPO / "app/source.kt"
        overlay = REPO / "build/experiment/source.kt"
        self.assertEqual([source], selected_sources([source], None, None))
        self.assertEqual([overlay], selected_sources([source], {source: overlay}, {"name": "experiment"}))
        for replacements, identity in (({source: overlay}, None), ({overlay: source}, {}),
                                        ({source: Path('/outside/source.kt')}, {})):
            with self.assertRaises(ValueError):
                selected_sources([source], replacements, identity)

    def test_real_candidate_features_and_original_survive_protocol(self):
        output = parse_output(RECORD + CANDIDATE, [ROW])
        self.assertEqual(output[0]["original"], "helo")
        self.assertEqual(output[0]["alternatives"][0]["text"], "hello")
        self.assertEqual(output[0]["alternatives"][0]["repetitionBonus"], 0.25)

    def test_missing_expected_word_is_not_injected(self):
        row = dict(ROW, expectedSpelling="help")
        result = parse_output(RECORD + CANDIDATE, [row])
        counts = summarize([row], result)["languages"]["en"]
        self.assertEqual(counts["candidateRecallCount"], 0)
        self.assertEqual(counts["completeRecalledTypos"], 0)

    def test_partial_recall_never_clears_retrieval_veto(self):
        output = RECORD.replace("COMPLETE\tfalse\tfalse", "STATES_EXHAUSTED\tfalse\ttrue") + CANDIDATE
        results = parse_output(output, [ROW])
        counts = summarize([ROW], results)["languages"]["en"]
        self.assertEqual(counts["candidateRecallCount"], 1)
        self.assertEqual(counts["retrievalAllowsAutoReplace"], 0)
        self.assertEqual(counts["completeRecalledTypos"], 0)

    def test_wrong_owner_order_count_and_duplicate_fail(self):
        for output in [RECORD, CANDIDATE, RECORD + CANDIDATE.replace("C\t0\t1", "C\t1\t1"),
                       RECORD + CANDIDATE + CANDIDATE, RECORD.replace("R\t0", "R\t1") + CANDIDATE,
                       RECORD + CANDIDATE + "unknown\n"]:
            with self.subTest(output=output), self.assertRaises(ValueError):
                parse_output(output, [ROW])

    def test_limits_and_veto_cannot_be_forged(self):
        for record in [RECORD.replace("\t12\t", "\t8193\t"), RECORD.replace("\tNONE\t1", "\tNONE\t8"),
                       RECORD.replace("COMPLETE", "VALID_WORD"), RECORD.replace("\tfalse\tfalse", "\ttrue\tfalse")]:
            with self.subTest(record=record), self.assertRaises(ValueError):
                parse_output(record + CANDIDATE, [ROW])

    def test_nonfinite_and_malformed_utf8_fail(self):
        for candidate in [CANDIDATE.replace("\t1.0\t", "\tnan\t"), CANDIDATE.replace("\t1.0\t", "\tinf\t"),
                          CANDIDATE.replace(enc("hello"), "/w==", 1)]:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                parse_output(RECORD + candidate, [ROW])

    def test_original_is_present_for_protected_no_alternatives(self):
        row = dict(ROW, typed="example.com", cohort="protected")
        results = parse_output("R\t0\tPROTECTED\tfalse\ttrue\t0\t0\tURL\t0\n", [row])
        self.assertEqual(results[0]["original"], row["typed"])
        self.assertEqual(results[0]["alternatives"], [])

    def test_duplicate_observations_remain_visible_in_counts(self):
        rows = [ROW, dict(ROW, id="en-calibration-test2")]
        one = parse_output(RECORD + CANDIDATE, [ROW])[0]
        results = [one, copy.deepcopy(one)]
        results[1]["id"] = rows[1]["id"]
        counts = summarize(rows, results)["languages"]["en"]
        self.assertEqual(counts["rows"], 2)
        self.assertEqual(counts["uniqueInputs"], 1)


if __name__ == "__main__":
    unittest.main()
