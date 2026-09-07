import unittest

from typing_diagnostics_analyzer import analyze_events


class TypingDiagnosticsAnalyzerTest(unittest.TestCase):
    def test_schema_two_matches_operations_instead_of_adjacent_revisions(self):
        events = [
            {"schema": 2, "kind": "BOUNDARY", "reason": "AUTO_REPLACE", "session": 7,
             "revision": 10, "operationId": 4, "original": "teh", "result": "the"},
            {"schema": 2, "kind": "EDITOR", "reason": "EDITOR_ACCEPTED", "session": 7,
             "revision": 11, "operationId": 5},
        ]
        self.assertEqual([], analyze_events(events)["outcomes"])
        events.append({"schema": 2, "kind": "EDITOR", "reason": "EDITOR_REJECTED", "session": 7,
                       "revision": 10, "operationId": 4})
        outcome = analyze_events(events)["outcomes"][0]
        self.assertEqual("REJECTED", outcome["outcome"])
        self.assertIsNone(outcome["final"])

    def test_schema_two_acceptance_is_one_shot_and_needs_matching_origin(self):
        attempt = {"schema": 2, "kind": "MANUAL", "reason": "CORRECTION", "session": 7,
                   "revision": 10, "operationId": 4, "original": "teh", "result": "the"}
        accepted = {"schema": 2, "kind": "EDITOR", "reason": "EDITOR_ACCEPTED", "session": 7,
                    "revision": 10, "operationId": 4}
        self.assertEqual([], analyze_events([attempt, dict(accepted, session=8), dict(accepted, revision=11)])["outcomes"])
        outcomes = analyze_events([attempt, accepted, accepted])["outcomes"]
        self.assertEqual(1, len(outcomes))
        self.assertEqual("APPLIED", outcomes[0]["outcome"])

    def test_late_editor_response_cannot_join_undo_across_a_fresh_segment(self):
        events = [
            {"schema": 2, "kind": "MANUAL", "reason": "CORRECTION", "session": 7,
             "revision": 10, "operationId": 4, "original": "teh", "result": "the"},
            {"schema": 2, "kind": "SESSION", "reason": "START", "session": 7, "revision": 15},
            {"schema": 2, "kind": "EDITOR", "reason": "EDITOR_ACCEPTED", "session": 7,
             "revision": 10, "operationId": 4},
            {"schema": 2, "kind": "UNDO", "reason": "ACCEPTED", "session": 7,
             "revision": 17, "result": "unrelated"},
        ]
        self.assertEqual("the", analyze_events(events)["outcomes"][0]["final"])

    def test_malformed_operation_ids_fail_closed(self):
        for operation in (True, -1, 1_000_000_001, "4"):
            with self.subTest(operation=operation), self.assertRaises(ValueError):
                analyze_events([{"schema": 2, "kind": "EDITOR", "reason": "EDITOR_ACCEPTED",
                                 "session": 1, "revision": 1, "operationId": operation}])

    def test_malformed_known_schema_two_metadata_is_rejected(self):
        for field, value in (("elapsedMs", -1), ("elapsedMs", 60_001), ("scoringCode", 16),
                             ("requestId", False), ("completion", "guessed"), ("source", "private free text")):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                analyze_events([{"schema": 2, "kind": "RANKING", "reason": "STALE",
                                 "session": 1, "revision": 1, field: value}])

    def test_mechanical_outcomes_wait_for_exact_editor_response(self):
        attempt = {"schema": 2, "kind": "MECHANICAL", "reason": "AUTO_REPLACE", "session": 2,
                   "revision": 3, "operationId": 7, "original": "hello  ", "result": "hello. "}
        self.assertEqual([], analyze_events([attempt])["outcomes"])
        report = analyze_events([attempt, {"schema": 2, "kind": "EDITOR", "reason": "EDITOR_ACCEPTED",
                                          "session": 2, "revision": 3, "operationId": 7}])
        self.assertEqual("MECHANICAL", report["outcomes"][0]["kind"])

    def test_accepted_correction_followed_by_undo_has_the_final_original_word(self):
        """Dropping editor acceptance would turn a rejected attempt into a correction outcome."""
        report = analyze_events([
            {"schema": 1, "kind": "BOUNDARY", "reason": "AUTO_REPLACE", "session": 7,
             "revision": 10, "original": "teh", "result": "the"},
            {"schema": 1, "kind": "EDITOR", "reason": "EDITOR_ACCEPTED", "session": 7,
             "revision": 11},
            {"schema": 1, "kind": "UNDO", "reason": "ACCEPTED", "session": 7,
             "revision": 12, "original": "", "result": "teh"},
        ])

        self.assertEqual([{
            "session": 7,
            "initial_revision": 10,
            "final_revision": 12,
            "kind": "AUTO_REPLACE",
            "original": "teh",
            "preliminary": "the",
            "final": "teh",
            "outcome": "UNDONE",
        }], report["outcomes"])

    def test_rejected_correction_attempt_has_no_word_outcome(self):
        """Reporting a correction before its editor acknowledgement creates a false positive."""
        report = analyze_events([
            {"schema": 1, "kind": "MANUAL", "reason": "CORRECTION", "session": 8,
             "revision": 20, "original": "spelng", "result": "spelling"},
            {"schema": 1, "kind": "EDITOR", "reason": "EDITOR_REJECTED", "session": 8,
             "revision": 21},
            {"schema": 1, "kind": "UNDO", "reason": "ACCEPTED", "session": 8,
             "revision": 22, "original": "", "result": "spelng"},
        ])

        self.assertEqual([], report["outcomes"])

    def test_accepted_undo_requires_a_string_result(self):
        """Coercing a malformed Undo result to the original hides corrupt schema-1 data."""
        undo_events = [
            ("missing", {"schema": 1, "kind": "UNDO", "reason": "ACCEPTED", "session": 9,
                         "revision": 32, "original": ""}),
            ("null", {"schema": 1, "kind": "UNDO", "reason": "ACCEPTED", "session": 9,
                      "revision": 32, "original": "", "result": None}),
            ("false", {"schema": 1, "kind": "UNDO", "reason": "ACCEPTED", "session": 9,
                       "revision": 32, "original": "", "result": False}),
            ("zero", {"schema": 1, "kind": "UNDO", "reason": "ACCEPTED", "session": 9,
                      "revision": 32, "original": "", "result": 0}),
        ]
        for label, undo in undo_events:
            with self.subTest(result=label), self.assertRaisesRegex(ValueError, "undo result must be a string"):
                analyze_events([
                    {"schema": 1, "kind": "BOUNDARY", "reason": "AUTO_REPLACE", "session": 9,
                     "revision": 30, "original": "teh", "result": "the"},
                    {"schema": 1, "kind": "EDITOR", "reason": "EDITOR_ACCEPTED", "session": 9,
                     "revision": 31},
                    undo,
                ])

    def test_additive_future_schema_fields_do_not_change_final_outcomes(self):
        """Rejecting schema 2 or consuming its unknown fields would break compatible exports."""
        report = analyze_events([
            {"schema": 2, "kind": "MANUAL", "reason": "CORRECTION", "session": 10,
             "revision": 20, "original": "spelng", "result": "spelling",
             "elapsedMs": 4, "source": "LOCAL_POLICY", "futureOnly": {"ignored": True}},
            {"schema": 2, "kind": "EDITOR", "reason": "EDITOR_ACCEPTED", "session": 10,
             "revision": 21, "elapsedMs": 5, "source": "LOCAL_POLICY"},
        ])

        self.assertEqual([2], report["schemas"])
        self.assertEqual([{
            "session": 10,
            "initial_revision": 20,
            "final_revision": 20,
            "kind": "CORRECTION",
            "original": "spelng",
            "preliminary": "spelling",
            "final": "spelling",
            "outcome": "APPLIED",
        }], report["outcomes"])

    def test_late_stale_events_do_not_replace_an_applied_outcome(self):
        """Treating any later ranking event as a final result would erase a real correction."""
        report = analyze_events([
            {"schema": 1, "kind": "MANUAL", "reason": "CORRECTION", "session": 11,
             "revision": 30, "original": "recieve", "result": "receive"},
            {"schema": 1, "kind": "EDITOR", "reason": "EDITOR_ACCEPTED", "session": 11,
             "revision": 31},
            {"schema": 2, "kind": "RANKING", "reason": "STALE", "session": 11,
             "revision": 30, "original": "recieve", "result": "late-value", "source": "MODEL"},
        ])

        self.assertEqual("receive", report["outcomes"][0]["final"])
        self.assertEqual("APPLIED", report["outcomes"][0]["outcome"])


if __name__ == "__main__":
    unittest.main()
