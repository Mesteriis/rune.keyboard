import unittest

from typing_diagnostics_analyzer import analyze_events


class TypingDiagnosticsAnalyzerTest(unittest.TestCase):
    def test_schema_three_validates_separate_local_search_evidence(self):
        event = {"schema": 3, "kind": "CANDIDATES", "reason": "ACCEPTED", "session": 1,
                 "revision": 2, "localCompletion": "COMPLETE", "localInspectedStates": 100,
                 "localVerifiedTerminals": 3}
        self.assertEqual([3], analyze_events([event])["schemas"])
        for field, value in (("localCompletion", "guessed"), ("localInspectedStates", 8193),
                             ("localVerifiedTerminals", 65)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                analyze_events([{**event, field: value}])

    def test_schema_two_counts_explicit_backspace_actions(self):
        events = [
            {"schema": 2, "kind": "BACKSPACE", "reason": "NONE", "session": 7,
             "revision": 10, "operationId": 0},
            {"schema": 2, "kind": "EDITOR", "reason": "EDITOR_ACCEPTED", "session": 7,
             "revision": 10, "operationId": 31},
            {"schema": 2, "kind": "BACKSPACE", "reason": "NONE", "session": 7,
             "revision": 11, "operationId": 0},
        ]
        self.assertEqual(2, analyze_events(events)["backspaces"])

    def test_explicit_backspace_run_reports_deleted_and_retyped_word(self):
        def item(kind, revision, context, input_text=""):
            return {"schema": 2, "kind": kind, "reason": "NONE", "session": 8,
                "revision": revision, "context": context, "input": input_text,
                "original": "", "result": "", "candidates": []}
        report = analyze_events([
            item("BACKSPACE", 10, "это резултат"),
            item("EDITOR", 10, ""),
            item("BACKSPACE", 11, "это резулта"),
            item("INPUT", 12, "это резулт", "ь"),
            item("INPUT", 13, "это результ", "а"),
            item("INPUT", 14, "это результата", "т"),
            item("INPUT", 15, "это результат", " "),
        ])
        self.assertEqual([{"session": 8, "initialRevision": 10, "backspaces": 2,
            "evidence": "EXPLICIT_BACKSPACE_EVENTS", "beforeWord": "резултат",
            "afterWord": "результат", "deleted": "ат", "retyped": "ьат"}],
            report["manualEdits"])

    def test_original_restoration_changes_prior_final_word_only_after_exact_acceptance(self):
        correction = {"schema": 2, "kind": "MANUAL", "reason": "CORRECTION", "session": 7,
                      "revision": 10, "operationId": 4, "requestId": 2, "original": "teh", "result": "the"}
        accepted = {"schema": 2, "kind": "EDITOR", "reason": "EDITOR_ACCEPTED", "session": 7,
                    "revision": 10, "operationId": 4}
        original = {"schema": 2, "kind": "MANUAL", "reason": "ORIGINAL", "session": 7,
                    "revision": 11, "operationId": 5, "requestId": 2, "original": "the", "result": "teh"}
        terminal = {"schema": 2, "kind": "EDITOR", "reason": "EDITOR_ACCEPTED", "session": 7,
                    "revision": 11, "operationId": 5}
        for response in ([], [dict(terminal, operationId=99)], [dict(terminal, reason="EDITOR_REJECTED")]):
            with self.subTest(response=response):
                outcomes = analyze_events([correction, accepted, original] + response)["outcomes"]
                self.assertEqual(1, len(outcomes)); self.assertEqual("the", outcomes[0]["final"])
                self.assertEqual("APPLIED", outcomes[0]["outcome"])
        outcomes = analyze_events([correction, accepted, original, terminal])["outcomes"]
        self.assertEqual(1, len(outcomes)); self.assertEqual("teh", outcomes[0]["final"])
        self.assertEqual("RESTORED", outcomes[0]["outcome"])
        self.assertEqual(11, outcomes[0]["final_revision"])

    def test_original_restoration_cannot_cancel_a_different_candidate_request(self):
        events = [
            {"schema": 2, "kind": "MANUAL", "reason": "CORRECTION", "session": 7,
             "revision": 10, "operationId": 4, "requestId": 2, "original": "teh", "result": "the"},
            {"schema": 2, "kind": "EDITOR", "reason": "EDITOR_ACCEPTED", "session": 7,
             "revision": 10, "operationId": 4},
            {"schema": 2, "kind": "MANUAL", "reason": "ORIGINAL", "session": 7,
             "revision": 11, "operationId": 5, "requestId": 3, "original": "the", "result": "teh"},
            {"schema": 2, "kind": "EDITOR", "reason": "EDITOR_ACCEPTED", "session": 7,
             "revision": 11, "operationId": 5},
        ]
        self.assertEqual("the", analyze_events(events)["outcomes"][0]["final"])

    def test_schema_one_original_restoration_uses_only_accepted_legacy_editor_adjacency(self):
        events = [
            {"schema": 1, "kind": "MANUAL", "reason": "CORRECTION", "session": 7,
             "revision": 10, "original": "teh", "result": "the"},
            {"schema": 1, "kind": "EDITOR", "reason": "EDITOR_ACCEPTED", "session": 7, "revision": 11},
            {"schema": 1, "kind": "MANUAL", "reason": "ORIGINAL", "session": 7,
             "revision": 12, "original": "the", "result": "teh"},
        ]
        self.assertEqual("the", analyze_events(events)["outcomes"][0]["final"])
        events.append({"schema": 1, "kind": "EDITOR", "reason": "EDITOR_ACCEPTED", "session": 7, "revision": 13})
        self.assertEqual("teh", analyze_events(events)["outcomes"][0]["final"])

    def test_reset_session_start_revokes_pending_identity_before_numeric_ids_are_reused(self):
        for include_old_start in (False, True):
            events = ([{"schema": 2, "kind": "SESSION", "reason": "START", "session": 1, "revision": 2}]
                      if include_old_start else [])
            events.extend([
                {"schema": 2, "kind": "MANUAL", "reason": "CORRECTION", "session": 1,
                 "revision": 10, "operationId": 4, "original": "old", "result": "wrong"},
                {"schema": 2, "kind": "SESSION", "reason": "START", "session": 1, "revision": 2},
            ])
            terminal = {"schema": 2, "kind": "EDITOR", "reason": "EDITOR_ACCEPTED", "session": 1,
                        "revision": 10, "operationId": 4}
            self.assertEqual([], analyze_events(events + [terminal])["outcomes"])
            events.append({"schema": 2, "kind": "MANUAL", "reason": "CORRECTION", "session": 1,
                           "revision": 10, "operationId": 4, "original": "teh", "result": "the"})
            outcomes = analyze_events(events + [terminal])["outcomes"]
            self.assertEqual("teh", outcomes[0]["original"]); self.assertEqual("the", outcomes[0]["final"])

    def test_schema_two_missing_operation_identity_cannot_use_legacy_adjacency(self):
        for attempt_schema, editor_schema, attempt_id, editor_id in (
            (2, 2, None, 99), (2, 1, None, None), (2, 2, 0, 99),
            (2, 2, 4, None), (1, 2, None, None), (1, 2, None, 99),
        ):
            with self.subTest(attempt_schema=attempt_schema, editor_schema=editor_schema,
                              attempt_id=attempt_id, editor_id=editor_id):
                attempt = {"schema": attempt_schema, "kind": "MANUAL", "reason": "CORRECTION", "session": 7,
                           "revision": 10, "original": "teh", "result": "the"}
                editor = {"schema": editor_schema, "kind": "EDITOR", "reason": "EDITOR_ACCEPTED", "session": 7,
                          "revision": 11}
                if attempt_id is not None:
                    attempt["operationId"] = attempt_id
                if editor_id is not None:
                    editor["operationId"] = editor_id
                self.assertEqual([], analyze_events([attempt, editor])["outcomes"])

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
             "revision": 20, "operationId": 8, "original": "spelng", "result": "spelling",
             "elapsedMs": 4, "source": "LOCAL_POLICY", "futureOnly": {"ignored": True}},
            {"schema": 2, "kind": "EDITOR", "reason": "EDITOR_ACCEPTED", "session": 10,
             "revision": 20, "operationId": 8, "elapsedMs": 5, "source": "LOCAL_POLICY"},
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


class FeatureConfigurationTests(unittest.TestCase):
    def test_schema_four_preserves_enabled_and_effective_transitions(self):
        from typing_diagnostics_analyzer import FEATURE_KEYS
        disabled = dict.fromkeys(FEATURE_KEYS, False)
        configured = dict(disabled, qualityMetrics=True, visibleUndo=True)
        base = dict(schema=4, kind='SESSION', reason='START', session=1, revision=1,
                    localCompletion='NONE', localInspectedStates=0, localVerifiedTerminals=0,
                    features=configured, effectiveFeatures=disabled)
        active = dict(base, kind='CONFIGURATION', reason='NONE', revision=2, effectiveFeatures=configured)
        report = analyze_events([base, active, dict(active, kind='INPUT', revision=3)])
        self.assertEqual(2, len(report['featureConfigurations']))
        self.assertTrue(report['featureConfigurations'][0]['features']['visibleUndo'])
        self.assertFalse(report['featureConfigurations'][0]['effectiveFeatures']['visibleUndo'])
        self.assertTrue(report['featureConfigurations'][1]['effectiveFeatures']['visibleUndo'])

    def test_invalid_or_unconfigured_effective_features_rejected(self):
        from typing_diagnostics_analyzer import FEATURE_KEYS
        disabled = dict.fromkeys(FEATURE_KEYS, False)
        base = dict(schema=4, kind='CONFIGURATION', reason='NONE', session=1, revision=1,
                    localCompletion='NONE', localInspectedStates=0, localVerifiedTerminals=0,
                    features=disabled, effectiveFeatures=disabled)
        for changes in [dict(features=dict(disabled, qualityMetrics='yes')),
                        dict(effectiveFeatures=dict(disabled, qualityMetrics=True)), dict(features={})]:
            with self.assertRaises(ValueError):
                analyze_events([dict(base, **changes)])


    def test_schema_six_experiments_are_exact_and_tap_decisions_are_content_free(self):
        from typing_diagnostics_analyzer import FEATURE_KEYS_V5, FEATURE_KEYS_V6
        flags = dict.fromkeys(FEATURE_KEYS_V6, True)
        base = dict(schema=6, kind='TAP', reason='TOUCH_SHADOW', session=1, revision=1,
                    localCompletion='NONE', localInspectedStates=0, localVerifiedTerminals=0,
                    features=flags, effectiveFeatures=flags, typingProfile=0)
        report = analyze_events([base, dict(base, reason='TOUCH_REMAPPED')])
        self.assertEqual({'TOUCH_UNCHANGED': 0, 'TOUCH_SHADOW': 1, 'TOUCH_REMAPPED': 1},
                         report['dynamicTouchDecisions'])
        self.assertEqual([], report['outcomes'])  # A tap decision is not an acknowledged replacement.
        for wrong in (dict.fromkeys(FEATURE_KEYS_V5, True), dict(flags, compactContext='true'), dict(flags, coordinate=1)):
            with self.assertRaises(ValueError):
                analyze_events([dict(base, features=wrong)])

    def test_schema_six_manual_expansion_accepts_only_matching_old_or_new_complete_vocabularies(self):
        from typing_diagnostics_analyzer import FEATURE_KEYS_V6, FEATURE_KEYS_V6_MANUAL
        old = dict.fromkeys(FEATURE_KEYS_V6, False)
        new = dict.fromkeys(FEATURE_KEYS_V6_MANUAL, False)
        base = dict(schema=6, kind='TAP', reason='TOUCH_SHADOW', session=1, revision=1,
                    localCompletion='NONE', localInspectedStates=0, localVerifiedTerminals=0, typingProfile=0)
        for flags in (old, new, dict(new, manualCandidateExpansion=True)):
            report = analyze_events([dict(base, features=flags, effectiveFeatures=flags)])
            self.assertEqual(flags, report['featureConfigurations'][0]['features'])
        for configured, effective in ((old, new), (new, old),
                (dict(new, manualCandidateExpansion='true'), new),
                (new, dict(new, manualCandidateExpansion=1)),
                (dict(new, unknownFlag=False), new),
                (new, dict(new, manualCandidateExpansion=True))):
            with self.assertRaises(ValueError):
                analyze_events([dict(base, features=configured, effectiveFeatures=effective)])

    def test_schema_five_records_profile_only_transitions_and_four_new_flags(self):
        from typing_diagnostics_analyzer import FEATURE_KEYS_V5
        flags = dict.fromkeys(FEATURE_KEYS_V5, True)
        base = dict(schema=5, kind='CONFIGURATION', reason='NONE', session=1, revision=1,
                    localCompletion='NONE', localInspectedStates=0, localVerifiedTerminals=0,
                    features=flags, effectiveFeatures=flags, typingProfile=0)
        report = analyze_events([base, dict(base, revision=2, typingProfile=1)])
        self.assertEqual([0, 1], [item['typingProfile'] for item in report['featureConfigurations']])
        self.assertTrue(report['featureConfigurations'][1]['features']['protectedWords'])
        for invalid in (True, -1, 3, 'org.example.app', None):
            with self.assertRaises(ValueError):
                analyze_events([dict(base, typingProfile=invalid)])


if __name__ == "__main__":
    unittest.main()
