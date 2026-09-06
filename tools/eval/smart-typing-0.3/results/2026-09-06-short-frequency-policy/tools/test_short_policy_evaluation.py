import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import short_policy_evaluation as policy
from test_final_product_replay import request, response


class ShortPolicyEvaluationTest(unittest.TestCase):
    def test_frozen_variant_and_adapter_are_bound(self):
        identity = policy.policy_identity()
        self.assertTrue(identity["policyChanged"])
        self.assertFalse(identity["productionPromotionApproved"])
        self.assertEqual(len(identity["files"]), 5)

    def test_wrong_variant_and_original_evaluator_are_rejected(self):
        for changed in (policy.VARIANT, policy.ORIGINAL, policy.PATCH,
                        policy.HERE / "final_product_replay.py"):
            original_sha = policy.base.sha256
            with self.subTest(changed=changed), mock.patch.object(policy.base, "sha256",
                    side_effect=lambda path: "wrong" if path == changed else original_sha(path)):
                with self.assertRaisesRegex(ValueError, "POLICY_SOURCE_DRIFT"):
                    policy.policy_identity()

    def test_compile_replaces_exactly_one_generator(self):
        other = Path("Other.kt")
        with mock.patch.object(policy, "_compile_inputs", return_value=([other, policy.ORIGINAL], [], other)):
            sources, _, _ = policy.compile_inputs(Path("java"))
        self.assertEqual(sources, [other, policy.VARIANT])
        for sources in ([other], [policy.ORIGINAL, policy.ORIGINAL], [policy.ORIGINAL, policy.VARIANT]):
            with mock.patch.object(policy, "_compile_inputs", return_value=(sources, [], other)):
                with self.assertRaisesRegex(ValueError, "GENERATOR_SOURCE_CLOSURE"):
                    policy.compile_inputs(Path("java"))

    def test_wrong_source_or_request_cache_rejected(self):
        item, score = request(), response()
        identity = policy.base.cache_identity_for_requests([item], "runner", "model", "new-policy-source", "same-coefficients")
        for key in ("sourceSha256", "requestsSha256", "payloadSha256", "configSha256"):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "CACHE_IDENTITY"):
                policy.base.validate_complete_cache([item], {"cacheIdentity": {**identity, key: "old"}}, [score], identity)
        policy.base.validate_complete_cache([item], {"cacheIdentity": identity}, [score], identity)

    def test_missing_duplicate_and_reordered_scores_rejected(self):
        item, score = request(), response()
        identity = policy.base.cache_identity_for_requests([item], "r", "m", "s", "c")
        for values in ([], [score, score], [{**score, "scores": list(reversed(score["scores"]))}]):
            with self.assertRaises(ValueError):
                policy.base.validate_complete_cache([item], {"cacheIdentity": identity}, values, identity)

    def test_calibration_report_required_before_freeze(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.object(policy.base, "load_export", return_value={}):
                with self.assertRaisesRegex(ValueError, "CALIBRATION_REPORT_REQUIRED"):
                    policy.policy_freeze_receipt(root, {})

    def test_calibration_cannot_follow_freeze_or_holdout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy.before_holdout(root)
            for name in ("policy-freeze.json", "holdout-scores"):
                (root / name).touch()
                with self.assertRaisesRegex(ValueError, "CALIBRATION_BEFORE_FREEZE_AND_HOLDOUT"):
                    policy.before_holdout(root)
                (root / name).unlink()

    def test_calibration_receipt_rejects_adapter_and_artifact_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "calibration-scores").mkdir()
            for name in ("export-receipt.json", "calibration-scores/complete.json", "evidence.jsonl"):
                (root / name).write_text("fixture")
            receipt = {"complete": True, "candidatePolicy": policy.policy_identity(), "policyChanged": True,
                "experiment": policy.EXPERIMENT, "split": "calibration", "holdoutObservedForSelection": False,
                "exportReceiptSha256": policy.base.sha256(root / "export-receipt.json"),
                "scoresCompleteSha256": policy.base.sha256(root / "calibration-scores/complete.json"),
                "artifacts": {"evidence.jsonl": policy.base.sha256(root / "evidence.jsonl")}}
            path = root / "calibration-report.json"
            path.write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, "CALIBRATION_ARTIFACT_INVENTORY"):
                policy.admit_calibration_report(root, {})
            path.write_text(json.dumps({**receipt, "candidatePolicy": {}}))
            with self.assertRaisesRegex(ValueError, "CALIBRATION_REPORT_IDENTITY"):
                policy.admit_calibration_report(root, {})
            path.write_text(json.dumps(receipt))
            (root / "evidence.jsonl").write_text("drift")
            with self.assertRaisesRegex(ValueError, "CALIBRATION_ARTIFACT_INVENTORY"):
                policy.admit_calibration_report(root, {})

    def test_complete_receipt_requires_controller_rows_evidence_and_derived_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "calibration-scores").mkdir()
            names = {"deliveries-calibration.tsv", "deliveries-calibration.jsonl",
                "replay-calibration-ready.jsonl", "replay-calibration-ready.log",
                "replay-calibration-unavailable.jsonl", "replay-calibration-unavailable.log",
                "row-evidence-calibration.jsonl"}
            for name in names | {"export-receipt.json", "calibration-scores/complete.json"}:
                (root / name).write_text("")
            rows = [{"id": str(i), "split": "calibration"} for i in range(6000)]
            values = {"replay-calibration-ready.jsonl": rows,
                "replay-calibration-unavailable.jsonl": rows,
                "row-evidence-calibration.jsonl": rows + rows,
                "requests-calibration.jsonl": [], "deliveries-calibration.jsonl": []}
            summary = {"languages": {}}
            receipt = {"complete": True, "candidatePolicy": policy.policy_identity(), "policyChanged": True,
                "experiment": policy.EXPERIMENT, "split": "calibration", "holdoutObservedForSelection": False,
                "exportReceiptSha256": policy.base.sha256(root / "export-receipt.json"),
                "scoresCompleteSha256": policy.base.sha256(root / "calibration-scores/complete.json"),
                "artifacts": {name: policy.base.sha256(root / name) for name in names},
                "summaries": {"ready": summary, "unavailable": summary}}
            path = root / "calibration-report.json"
            path.write_text(json.dumps(receipt))
            with mock.patch.object(policy, "split_rows", return_value=rows), \
                 mock.patch.object(policy.base, "read_jsonl", side_effect=lambda path: values[path.name]), \
                 mock.patch.object(policy, "evidence", side_effect=lambda row, *args: row), \
                 mock.patch.object(policy.base, "summarize_rows", return_value=summary), \
                 mock.patch.object(policy.base, "admit_score_stage", return_value=({}, {})):
                policy.admit_calibration_report(root, {})
                for artifacts in ({}, {key: value for key, value in receipt["artifacts"].items()
                                        if key != "replay-calibration-ready.jsonl"}):
                    path.write_text(json.dumps({**receipt, "artifacts": artifacts}))
                    with self.assertRaisesRegex(ValueError, "CALIBRATION_ARTIFACT_INVENTORY"):
                        policy.admit_calibration_report(root, {})
                path.write_text(json.dumps({**receipt, "complete": False}))
                with self.assertRaisesRegex(ValueError, "CALIBRATION_REPORT_IDENTITY"):
                    policy.admit_calibration_report(root, {})
                path.write_text(json.dumps({**receipt, "summaries": {}}))
                with self.assertRaisesRegex(ValueError, "CALIBRATION_SUMMARY_MISMATCH"):
                    policy.admit_calibration_report(root, {})
                path.write_text(json.dumps(receipt))
                for mode in ("ready", "unavailable"):
                    key = f"replay-calibration-{mode}.jsonl"
                    values[key] = rows[:-1]
                    with self.assertRaisesRegex(ValueError, "CALIBRATION_REPLAY_ROWS"):
                        policy.admit_calibration_report(root, {})
                    values[key] = rows
                values["row-evidence-calibration.jsonl"] = rows
                with self.assertRaisesRegex(ValueError, "CALIBRATION_EVIDENCE_MISMATCH"):
                    policy.admit_calibration_report(root, {})
                values["row-evidence-calibration.jsonl"] = rows + rows
                (root / "replay-calibration-ready.log").write_text("drift")
                with self.assertRaisesRegex(ValueError, "CALIBRATION_REPORT_ARTIFACT_DRIFT"):
                    policy.admit_calibration_report(root, {})

    def test_each_split_keeps_complete_denominators(self):
        rows = [{"id": f"{lang}-{cohort}-{i}", "language": lang, "cohort": cohort, "split": "calibration"}
                for lang in policy.base.LANGUAGES for cohort, count in policy.base.COHORT_COUNTS.items()
                for i in range(count)]
        with mock.patch.object(policy.base, "read_jsonl", return_value=rows):
            self.assertEqual(len(policy.split_rows(Path("fixture"), "calibration")), 6000)
        with mock.patch.object(policy.base, "read_jsonl", return_value=rows[:-1]):
            with self.assertRaisesRegex(ValueError, "REPLAY_SPLIT_ROWS"):
                policy.split_rows(Path("fixture"), "calibration")


if __name__ == "__main__":
    unittest.main()
