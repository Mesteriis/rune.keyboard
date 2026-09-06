import json
import math
import os
import base64
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import final_product_replay as replay


def request(identifier="en-calibration-1", split="calibration"):
    return {
        "id": identifier,
        "split": split,
        "sessionId": 1,
        "revision": 7,
        "requestId": 11,
        "language": "en",
        "prefix": "hello ",
        "candidateIds": [0, 1],
        "continuations": ["helo", "hello"],
    }


def response(identifier="en-calibration-1"):
    return {
        "id": identifier,
        "durationMillis": 1.25,
        "scores": [
            {"id": 0, "sumLogProbability": -3.0, "scoredTokenCount": 1},
            {"id": 1, "sumLogProbability": -1.0, "scoredTokenCount": 1},
        ],
    }


class FinalProductReplayTest(unittest.TestCase):
    def test_compile_sources_are_versioned_without_ignored_results(self):
        sources = replay.final_product_sources()
        self.assertGreater(len(sources), 20)
        self.assertTrue(all(path.is_file() for path in sources))
        self.assertTrue(all("/results/" not in str(path) for path in sources))

    def test_successful_scores_are_controller_deliverable_at_exact_token_boundaries(self):
        for count in (1, 255):
            value = response()
            value["scores"] = [{**score, "scoredTokenCount": count} for score in value["scores"]]
            replay.validate_response(request(), value)
        for count in (0, 256):
            value = response()
            value["scores"] = [{**score, "sumLogProbability": 0.0 if count == 0 else -1.0,
                                "scoredTokenCount": count} for score in value["scores"]]
            with self.subTest(count=count), self.assertRaises(ValueError):
                replay.validate_response(request(), value)

    @unittest.skipUnless(os.environ.get("FINAL_REPLAY_EXPORT"), "set FINAL_REPLAY_EXPORT for Kotlin admission test")
    def test_kotlin_ready_rejects_live_payload_drift_and_missing_delivery(self):
        root = Path(os.environ["FINAL_REPLAY_EXPORT"])
        receipt = json.loads((root / "export-receipt.json").read_text())
        observations = replay.read_jsonl(root / "observations.jsonl")
        observation = next(item for item in observations if item.get("actualModelRequest"))
        live = observation["actualModelRequest"]
        row = "\t".join(["0", base64.b64encode(observation["id"].encode()).decode(),
            observation["split"], observation["language"],
            base64.b64encode(observation["prefix"].encode()).decode(),
            base64.b64encode(observation["typed"].encode()).decode()]) + "\n"
        request = {"id": observation["id"], "split": observation["split"],
            "language": observation["language"], "sessionId": live["sessionId"],
            "revision": live["revision"], "requestId": 1, "prefix": live["prefix"],
            "candidateIds": live["candidateIds"], "continuations": live["continuations"]}
        native = {"id": request["id"], "durationMillis": 0.0,
            "scores": [{"id": value, "sumLogProbability": -1.0, "scoredTokenCount": 1}
                       for value in request["candidateIds"]]}
        command = receipt["commands"]["export"][:-4]
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory); inputs = directory / "inputs.tsv"; inputs.write_text(row)
            valid = directory / "valid.tsv"
            valid.write_text(replay.delivery_tsv_line(replay.delivery_for(request, native)) + "\n")
            successful = subprocess.run([*command, str(inputs), str(replay.ASSETS), "ready",
                observation["split"], str(valid)], capture_output=True)
            self.assertEqual(successful.returncode, 0, successful.stderr.decode())
            drifted_request = {**request, "continuations": [request["continuations"][0] + "x",
                *request["continuations"][1:]]}
            drifted = directory / "drifted.tsv"
            drifted.write_text(replay.delivery_tsv_line(replay.delivery_for(drifted_request, native)) + "\n")
            refused = subprocess.run([*command, str(inputs), str(replay.ASSETS), "ready",
                observation["split"], str(drifted)], capture_output=True)
            self.assertNotEqual(refused.returncode, 0)
            missing = directory / "missing.tsv"; missing.write_text("")
            refused = subprocess.run([*command, str(inputs), str(replay.ASSETS), "ready",
                observation["split"], str(missing)], capture_output=True)
            self.assertNotEqual(refused.returncode, 0)

    def test_actual_native_envelope_and_strict_malformed_variants(self):
        replay.validate_response(request(), response())
        invalid = [
            {k: v for k, v in response().items() if k != "durationMillis"},
            {**response(), "durationMillis": -1},
            {**response(), "extra": "forbidden"},
            {**response(), "scores": [{"id": False, "sumLogProbability": -3.0,
                "scoredTokenCount": 1}, response()["scores"][1]]},
            {**response(), "scores": [{**response()["scores"][0], "extra": 1},
                response()["scores"][1]]},
            {"id": request()["id"], "error": "ARBITRARY"},
        ]
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    replay.validate_response(request(), value)

    def test_model_request_projection_excludes_labels_and_binds_live_identity(self):
        projected = replay.runner_request(request())
        self.assertEqual(projected, {
            "id": "en-calibration-1",
            "prefix": "hello ",
            "candidates": ["helo", "hello"],
        })
        self.assertFalse({"cohort", "expectedSpelling", "noAuto"} & projected.keys())

    def test_complete_cache_rejects_identity_drift_duplicates_foreign_missing_and_invalid_numeric(self):
        requests = [request(), request("en-calibration-2")]
        identity = replay.cache_identity_for_requests(requests, "runner", "model", "source", "config")
        valid = [response(), response("en-calibration-2")]
        replay.validate_complete_cache(requests, {"cacheIdentity": identity}, valid, identity)
        mutations = [
            ({"cacheIdentity": {**identity, "sourceSha256": "other"}}, valid),
            ({"cacheIdentity": identity}, [valid[0], valid[0]]),
            ({"cacheIdentity": identity}, [valid[0], response("foreign")]),
            ({"cacheIdentity": identity}, [valid[0]]),
            ({"cacheIdentity": identity}, [valid[0], {**valid[1], "scores": [
                {"id": 0, "sumLogProbability": math.nan, "scoredTokenCount": 1},
                {"id": 1, "sumLogProbability": -1.0, "scoredTokenCount": 1},
            ]}]),
        ]
        for header, records in mutations:
            with self.subTest(header=header, count=len(records)):
                with self.assertRaises(ValueError):
                    replay.validate_complete_cache(requests, header, records, identity)
        changed_requests = [{**requests[0], "continuations": ["helo", "hullo"]}, requests[1]]
        changed_identity = replay.cache_identity_for_requests(changed_requests, "runner", "model", "source", "config")
        self.assertNotEqual(identity["payloadSha256"], changed_identity["payloadSha256"])
        with self.assertRaises(ValueError):
            replay.validate_complete_cache(changed_requests, {"cacheIdentity": identity}, valid, changed_identity)

    def test_model_error_is_complete_retained_abstention(self):
        requests = [request()]
        identity = replay.cache_identity_for_requests(requests, "runner", "model", "source", "config")
        error = {"id": requests[0]["id"], "error": "SCORING_FAILED"}
        admitted = replay.validate_complete_cache(requests, {"cacheIdentity": identity}, [error], identity)
        self.assertEqual(admitted[requests[0]["id"]], error)
        self.assertEqual(replay.delivery_for(requests[0], error)["code"], "UNAVAILABLE")
        delivery = replay.delivery_for(requests[0], response())
        self.assertEqual(delivery["prefix"], requests[0]["prefix"])
        self.assertEqual(delivery["continuations"], requests[0]["continuations"])
        self.assertEqual(delivery["candidateIds"], requests[0]["candidateIds"])
        self.assertEqual(delivery["language"], "en")

    def test_point_gates_use_exact_integer_ratios_and_separate_spelling_volume(self):
        self.assertFalse(replay.fixed_policy_gates(682, 718, 0, 1000, 718)["precisionPass"])
        self.assertTrue(replay.fixed_policy_gates(684, 720, 5, 1000, 300)["allPass"])
        self.assertFalse(replay.fixed_policy_gates(684, 720, 6, 1000, 300)["falseChangePass"])
        self.assertFalse(replay.fixed_policy_gates(684, 720, 0, 1000, 299,
                                                   mechanical_changes=500)["volumePass"])

    def test_release_approval_requires_each_language_gate(self):
        passed = {"en": {"fixedPointPolicyGates": {"allPass": True}},
                  "es": {"fixedPointPolicyGates": {"allPass": True}},
                  "ru": {"fixedPointPolicyGates": {"allPass": True}}}
        self.assertTrue(replay.holdout_release_approved(passed))
        passed["ru"]["fixedPointPolicyGates"]["allPass"] = False
        self.assertFalse(replay.holdout_release_approved(passed))
        self.assertFalse(replay.fixed_policy_gates(684, 720, 0, 1000, 300,
            original_retained=1999, total_rows=2000, undo_exact=2000)["originalAlwaysAvailablePass"])
        self.assertFalse(replay.fixed_policy_gates(684, 720, 0, 1000, 300,
            original_retained=2000, total_rows=2000, undo_exact=1999)["exactImmediateUndoPass"])

    def test_final_product_gate_uses_aggregate_negative_changes(self):
        metrics = {
            "rows": 2000,
            "ordinarySpelling": {"automaticChanges": 300, "correctChanges": 300,
                "falseChanges": {"numerator": 0, "denominator": 1000}},
            "aggregateFinalText": {"falseChanges": {"numerator": 10, "denominator": 1000}},
            "mechanical": {"changedRows": 500},
            "originalRetention": {"numerator": 2000, "denominator": 2000},
            "exactUndo": {"numerator": 2000, "denominator": 2000},
        }
        gates = replay.product_policy_gates(metrics)
        self.assertTrue(gates["ordinarySpellingFalseChangePass"])
        self.assertFalse(gates["aggregateFalseChangePass"])
        self.assertFalse(gates["allPass"])

    def test_final_product_gate_uses_the_automatic_edit_undo_denominator(self):
        metrics = {
            "rows": 2000,
            "ordinarySpelling": {"automaticChanges": 300, "correctChanges": 300,
                "falseChanges": {"numerator": 0, "denominator": 1000}},
            "aggregateFinalText": {"falseChanges": {"numerator": 0, "denominator": 1000}},
            "mechanical": {"changedRows": 0},
            "originalRetention": {"numerator": 1901, "denominator": 1901},
            "exactUndo": {"numerator": 300, "denominator": 300},
        }
        self.assertTrue(replay.product_policy_gates(metrics)["exactImmediateUndoPass"])

    def test_fragment_original_uses_explicit_role_and_actual_owned_token(self):
        observation = {"actualOriginal": "score", "candidateView": {"candidates": [
            {"id": "original:1:2:3", "role": "ORIGINAL", "text": "score"},
            {"id": "correction:1", "role": "CORRECTION", "text": "samples[10].score"},
        ]}}
        result = replay.original_retention(observation, "samples[10].score")
        self.assertEqual(result, {"applicable": True, "retained": True, "actualOriginal": "score",
                                  "corpusTokenMatchesActualOriginal": False})

    def test_protected_token_without_candidate_set_is_not_an_original_availability_trial(self):
        result = replay.original_retention({"actualOriginal": "", "candidateView": {"candidates": []}}, "feature/name")
        self.assertFalse(result["applicable"])
        self.assertIsNone(result["retained"])

    def test_undo_gate_counts_only_automatic_edits(self):
        rows = [
            {"input": {"language": "en", "cohort": "typo"},
             "evaluation": {"spellingAutoEdit": True, "canonicalAutoEdit": False,
                 "mechanicalChange": False, "undoExact": True, "correctFinalReplacement": True,
                 "candidateRecall": True, "originalRetained": True, "originalApplicable": True,
                 "fullFinalTextChanged": True, "modelRequested": True, "modelError": False, "modelRefused": False}},
            {"input": {"language": "en", "cohort": "protected"},
             "evaluation": {"spellingAutoEdit": False, "canonicalAutoEdit": False,
                 "mechanicalChange": False, "undoExact": False, "correctFinalReplacement": False,
                 "candidateRecall": None, "originalRetained": None, "originalApplicable": False,
                 "fullFinalTextChanged": False, "modelRequested": False, "modelError": False, "modelRefused": False}},
        ]
        undo = replay.summarize_rows(rows)["languages"]["en"]["exactUndo"]
        self.assertEqual({"numerator": undo["numerator"], "denominator": undo["denominator"]},
                         {"numerator": 1, "denominator": 1})

    def test_bound_java_rejects_alternate_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            home = base / "jdk"; bound = home / "bin/java"; alternate = base / "other-java"
            for relative in replay.JDK_RUNTIME_INVENTORY:
                path = home / relative; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(relative.encode())
            alternate.write_bytes(b"other")
            receipt = json.loads(json.dumps(
                {"bindings": {"javaRuntime": replay.java_runtime_binding(bound)}}, sort_keys=True))
            self.assertEqual(replay.select_bound_java(receipt), bound.resolve())
            with self.assertRaises(ValueError):
                replay.select_bound_java(receipt, alternate)
            (home / "lib/server/libjvm.dylib").write_bytes(b"mutated")
            with self.assertRaises(ValueError):
                replay.select_bound_java(receipt)

    def test_freeze_and_policy_admission_derive_identity_and_detect_post_freeze_cache_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            export_path = root / "export-receipt.json"; export_path.write_text("{}\n")
            export = {"sourceFreezeSha256": "source-freeze"}
            requests = [request()]
            replay.write_jsonl(root / "requests-calibration.jsonl", requests)
            score_dir = root / "calibration-scores"; score_dir.mkdir()
            identity = replay.expected_score_identity(export, requests)
            cache = score_dir / "scores.jsonl"
            replay.write_jsonl(cache, [{"cacheIdentity": identity}, response()])
            complete = replay.score_complete_receipt("calibration", requests, [response()], identity,
                replay.sha256(cache), replay.sha256(export_path), None)
            replay.write_json(score_dir / "complete.json", complete)
            with mock.patch.object(replay, "load_export", return_value=export), \
                 mock.patch.object(replay, "verify_bound_files", return_value=None):
                replay.freeze_policy(SimpleNamespace(root=str(root)))
                replay.admit_policy_freeze(root, export)
                foreign = {**identity, "runnerSha256": "0" * 64}
                replay.write_jsonl(root / "foreign.jsonl", [{"cacheIdentity": foreign}, response()])
                cache.write_bytes((root / "foreign.jsonl").read_bytes())
                complete["identity"] = foreign
                complete["scoresSha256"] = replay.sha256(cache)
                (score_dir / "complete.json").write_text(json.dumps(complete) + "\n")
                with self.assertRaises(ValueError):
                    replay.admit_score_stage(root, "calibration", export)
                with self.assertRaises(ValueError):
                    replay.admit_policy_freeze(root, export)

    def test_report_counts_full_text_canonical_mechanical_original_and_undo(self):
        rows = [
            {"input": {"id": "t", "language": "en", "cohort": "typo", "noAuto": False},
             "evaluation": {"modelRequested": True, "modelError": False, "modelRefused": False,
                 "originalRetained": True, "candidateRecall": True, "spellingAutoEdit": True,
                 "canonicalAutoEdit": False, "mechanicalChange": False, "fullFinalTextChanged": True,
                 "correctFinalReplacement": True, "undoExact": True}},
            {"input": {"id": "c", "language": "en", "cohort": "correct", "noAuto": False},
             "evaluation": {"modelRequested": False, "modelError": False, "modelRefused": False,
                 "originalRetained": True, "candidateRecall": None, "spellingAutoEdit": False,
                 "canonicalAutoEdit": True, "mechanicalChange": True, "fullFinalTextChanged": True,
                 "correctFinalReplacement": False, "undoExact": True}},
            {"input": {"id": "p", "language": "en", "cohort": "protected", "noAuto": True},
             "evaluation": {"modelRequested": True, "modelError": True, "modelRefused": False,
                 "originalRetained": True, "candidateRecall": None, "spellingAutoEdit": False,
                 "canonicalAutoEdit": False, "mechanicalChange": False, "fullFinalTextChanged": False,
                 "correctFinalReplacement": False, "undoExact": True}},
        ]
        report = replay.summarize_rows(rows)["languages"]["en"]
        self.assertEqual(report["cohorts"]["correct"]["rows"], 1)
        self.assertEqual(report["cohorts"]["protected"]["rows"], 1)
        self.assertEqual(report["ordinarySpelling"]["automaticChanges"], 1)
        self.assertEqual(report["canonical"]["automaticChanges"], 1)
        self.assertEqual(report["canonical"]["falseChanges"]["numerator"], 1)
        self.assertEqual(report["mechanical"]["changedRows"], 1)
        self.assertEqual(report["mechanical"]["falseChangesByCohort"]["correct"]["denominator"], 1)
        self.assertEqual(report["aggregateFinalText"]["changedRows"], 2)
        self.assertEqual(report["aggregateFinalText"]["falseChanges"]["numerator"], 1)
        self.assertEqual(report["originalRetention"]["numerator"], 3)
        self.assertEqual(report["exactUndo"]["numerator"], 2)
        self.assertEqual(report["exactUndo"]["denominator"], 2)
        self.assertEqual(report["model"]["errors"], 1)

    def test_bound_receipt_detects_modified_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.kt"
            path.write_text("one")
            receipt = {"files": {str(path): replay.sha256(path)}}
            replay.verify_bound_files(receipt)
            path.write_text("two")
            with self.assertRaises(ValueError):
                replay.verify_bound_files(receipt)


if __name__ == "__main__":
    unittest.main()
