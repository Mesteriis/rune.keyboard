import unittest

from typing_diagnostics_analyzer import analyze_events


class TypingDiagnosticsAnalyzerTest(unittest.TestCase):
    def test_undo_finalizes_the_prior_automatic_word_correction(self):
        """Removing the session correction stack would report `the` instead of final `teh`."""
        report = analyze_events([
            {"schema": 1, "kind": "BOUNDARY", "reason": "AUTO_REPLACE", "session": 7,
             "revision": 10, "original": "teh", "result": "the"},
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

    def test_additive_future_schema_fields_do_not_change_final_outcomes(self):
        """Rejecting schema 2 or consuming its unknown fields would break compatible exports."""
        report = analyze_events([
            {"schema": 2, "kind": "MANUAL", "reason": "CORRECTION", "session": 8,
             "revision": 20, "original": "spelng", "result": "spelling",
             "elapsedMs": 4, "source": "LOCAL", "futureOnly": {"ignored": True}},
        ])

        self.assertEqual([2], report["schemas"])
        self.assertEqual([{
            "session": 8,
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
            {"schema": 1, "kind": "MANUAL", "reason": "CORRECTION", "session": 9,
             "revision": 30, "original": "recieve", "result": "receive"},
            {"schema": 2, "kind": "RANKING", "reason": "STALE", "session": 9,
             "revision": 30, "original": "recieve", "result": "late-value", "source": "MODEL"},
        ])

        self.assertEqual("receive", report["outcomes"][0]["final"])
        self.assertEqual("APPLIED", report["outcomes"][0]["outcome"])


if __name__ == "__main__":
    unittest.main()
