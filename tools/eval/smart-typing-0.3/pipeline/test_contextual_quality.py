import base64
import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import contextual_quality as cq
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

    def test_original_and_punctuation_ties_abstain(self):
        records = [{"id": name, "variants": [{"id": i} for i in range(7)]} for name in ("one", "two")]
        def response(identifier, values):
            return {"id": identifier, "scores": [{"id": i, "sumLogProbability": value,
                    "scoredTokenCount": 1} for i, value in enumerate(values)], "durationMillis": 1}
        scores = {"one": response("one", [-1, -1, -2, -3, -4, -5, -6]),
                  "two": response("two", [-2, -1, -1, -3, -4, -5, -6])}
        self.assertEqual(decisions(records, scores), [0, 0])

    def test_totals_and_both_exact_margin_boundaries(self):
        record = {"id": "one", "variants": [{"id": i} for i in range(7)]}
        cases = [([-2, -3, -10, -10, -10, -10, -10], [1, 2, 1, 1, 1, 1, 1], 0),
                 ([-8, -1, -5, -12, -12, -12, -12], [1, 1, 255, 1, 1, 1, 1], 1),
                 ([-1.5, -1, -5, -12, -12, -12, -12], [1] * 7, 0),
                 ([-1.500001, -1, -5, -12, -12, -12, -12], [1] * 7, 1),
                 ([-8, -1, -4.999999, -12, -12, -12, -12], [1] * 7, 0)]
        for totals, counts, expected in cases:
            response = {"scores": [{"id": i, "sumLogProbability": total, "scoredTokenCount": count}
                                   for i, (total, count) in enumerate(zip(totals, counts))]}
            with self.subTest(totals=totals):
                self.assertEqual([expected], decisions([record], {"one": response}))

    def test_invalid_numeric_records_abstain(self):
        record = {"id": "one", "variants": [{"id": i} for i in range(7)]}
        valid = [{"id": i, "sumLogProbability": -1 if i == 1 else -10,
                  "scoredTokenCount": 1} for i in range(7)]
        for key, values in (("scoredTokenCount", [0, -1, 256, True]),
                            ("sumLogProbability", [float("nan"), float("inf"), float("-inf"), 0.1]),
                            ("id", [-1, 1, 8])):
            for value in values:
                scores = copy.deepcopy(valid)
                scores[-1][key] = value
                with self.subTest(key=key, value=value):
                    self.assertEqual([0], decisions([record], {"one": {"scores": scores}}))

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
        self.assertEqual(decisions([{"id": "one", "variants": [{"id": i} for i in range(7)]}],
                                  {"one": {"id": "one", "error": "SCORING_FAILED"}}), [0])

    def test_independently_reordered_expected_and_score_ids_preserve_result(self):
        scores = [{"id": i, "sumLogProbability": -1 if i == 6 else -10, "scoredTokenCount": 1}
                  for i in range(7)]
        for expected in (list(range(7)), list(reversed(range(7)))):
            for returned in (scores, list(reversed(scores))):
                self.assertEqual(6, cq.choose(expected, returned))

    def test_missing_duplicate_unknown_or_malformed_ids_abstain(self):
        scores = [{"id": i, "sumLogProbability": -1 if i == 1 else -10, "scoredTokenCount": 1}
                  for i in range(3)]
        for malformed in ([], scores[:2], scores + scores[:1], [scores[0], scores[1], scores[1]],
                          [scores[0], scores[1], {**scores[2], "id": 4}],
                          [scores[0], scores[1], {"id": 2}]):
            self.assertEqual(0, cq.choose([0, 1, 2], malformed))
        for expected in ([], [0], [0, 1], [1, 2, 3], [0, 1, 1], [0, 1, -1],
                         [0, True, 2], [0, 1.0, 2], [0, 1, 2**31], list(range(9))):
            self.assertEqual(0, cq.choose(expected, scores))

    def test_excluded_rows_cannot_acquire_invented_scores(self):
        with self.assertRaisesRegex(ValueError, "EXCLUDED_ROW_SCORED"):
            decisions([{"id": "excluded", "variants": []}], {"excluded": {"scores": []}})

    def test_metric_counts_wilson_intervals_and_zero_automatic_replacements_remain(self):
        records = [{"id": name, "variants": [{"id": i} for i in range(3)],
                    "ambiguous": ambiguous, "expectedCandidate": 1}
                   for name, ambiguous in (("clear", False), ("missing", False), ("ambiguous", True))]
        response = {"scores": [{"id": i, "sumLogProbability": -1 if i == 1 else -10,
                                "scoredTokenCount": 1} for i in range(3)]}
        actual = metrics(records, {"clear": response, "ambiguous": response})
        self.assertEqual((3, 2, 1, 1, 1, 0), tuple(actual[key] for key in
            ("rows", "unambiguousRows", "ambiguousRows", "suggestions", "correctSuggestions", "automaticReplacements")))
        self.assertEqual(cq.evaluator().rate(1, 1), actual["suggestionPrecision"])
        self.assertEqual(cq.evaluator().rate(1, 2), actual["unambiguousAbstention"])
        self.assertEqual(cq.evaluator().rate(1, 1), actual["ambiguousNonSpaceSuggestion"])


class ContextualProvenanceTest(unittest.TestCase):
    """Exercise file/digest gates; real compiler parity is a separate verify-policy command."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="contextual-unit-", dir=cq.shared.REPO / "build")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.java = self.root / "java"
        self.java.write_bytes(b"synthetic Java launcher")
        self.jars = [self.root / f"tool-{index}.jar" for index in range(3)]
        for jar in self.jars: jar.write_bytes(b"synthetic compiler dependency")
        patch = mock.patch.object(cq, "toolchain", return_value=self.jars)
        patch.start(); self.addCleanup(patch.stop)

    def fake_process(self, command, **kwargs):
        if command[-1] == "-version":
            return subprocess.CompletedProcess(command, 0, b"", b'openjdk version "17.synthetic"\n')
        if "org.jetbrains.kotlin.cli.jvm.K2JVMCompiler" in command:
            Path(command[command.index("-d") + 1]).write_bytes(b"synthetic compiled policy")
        else:
            kwargs["stdout"].write(cq.parity_expected(cq.parity_cases()).encode())
        return subprocess.CompletedProcess(command, 0)

    def verification(self):
        directory = self.root / "verification"
        with mock.patch.object(cq.subprocess, "run", side_effect=self.fake_process), redirect_stdout(io.StringIO()):
            cq.verification_run(SimpleNamespace(output=directory, java=self.java, gradle_cache=self.root))
        return directory

    def signed_write(self, path, content, digest_name):
        content = {key: value for key, value in content.items() if key != digest_name}
        path.write_text(json.dumps({**content, digest_name: cq.evaluator().digest(content)}))

    def frozen(self, verification):
        directory = self.root / "export"
        directory.mkdir()
        (directory / "provenance.json").write_text("synthetic export receipt")
        scoring = self.root / "scores"
        scoring.mkdir()
        (scoring / "complete.json").write_text("synthetic calibration receipt")
        records = [{"id": f"synthetic-{index}", "split": "calibration", "language": ("en", "ru", "es")[index % 3],
                    "ambiguous": False, "expectedCandidate": 0, "variants": []} for index in range(600)]
        complete = {**cq.policy_binding(), "split": "calibration", "frozenConfigSha256": None,
                    "exportReceiptSha256": cq.shared.sha(directory / "provenance.json"),
                    "scoresSha256": "synthetic", "identity": {"protocol": "synthetic", "runnerSha256": "runner", "modelSha256": "model"}}
        output = self.root / "freeze"
        with mock.patch.object(cq, "load_export", return_value=records), \
             mock.patch.object(cq, "load_scores", return_value=(complete, {})), redirect_stdout(io.StringIO()):
            cq.freeze_run(SimpleNamespace(export=directory, scoring=scoring, output=output, policy_verification=verification))
        return output / "config.json", complete["exportReceiptSha256"]

    def test_valid_verification_is_required_and_bound_into_v2_freeze(self):
        verification = self.verification()
        receipt = cq.load_verification(verification)
        self.assertEqual(len(cq.parity_cases()), receipt["cases"])
        path, export_hash = self.frozen(verification)
        config = cq.load_frozen(path, export_hash)
        self.assertEqual(2, config["schemaVersion"])
        self.assertEqual(cq.policy_binding()["policy"], config["policy"])
        self.assertEqual(cq.shared.sha(verification / "verification.json"), config["policyVerificationSha256"])
        self.assertFalse(config["thresholdSearchPerformed"])

    def test_freeze_rejects_missing_verification_before_loading_data(self):
        with self.assertRaises(FileNotFoundError):
            cq.freeze_run(SimpleNamespace(policy_verification=self.root / "missing"))

    def test_rehashed_legacy_configs_exports_and_score_receipts_are_rejected(self):
        old = {"schemaVersion": 1, "scope": "contextual-fixed-rule-calibration", "minimumDelta": 0.0,
               "selectionRule": "best non-original average log probability strictly greater than Original; stable lower ID"}
        path = self.root / "config.json"
        self.signed_write(path, old, "configSha256")
        with self.assertRaisesRegex(ValueError, "FROZEN_POLICY"):
            cq.load_frozen(path, "unused")
        (self.root / "provenance.json").write_text(json.dumps(old))
        with self.assertRaisesRegex(ValueError, "EXPORT_POLICY"):
            cq.load_export(self.root)
        (self.root / "complete.json").write_text(json.dumps(old))
        with self.assertRaisesRegex(ValueError, "SCORES_POLICY"):
            cq.load_scores(self.root, [])

    def test_rehashed_threshold_source_version_and_export_mutations_fail_closed(self):
        verification = self.verification()
        path, export_hash = self.frozen(verification)
        valid = json.loads(path.read_text())
        mutations = [{**valid, "policySourceSha256": "wrong"}, {**valid, "qualitySourceSha256": "wrong"},
                     {**valid, "engineSha256": "wrong"},
                     {**valid, "schemaVersion": 1}, {**valid, "exportReceiptSha256": "wrong"},
                     {**valid, "policyVerificationSha256": "wrong"}]
        for key, value in (("originalAdvantage", 0.0), ("rivalAdvantage", 3.0),
                           ("originalComparison", ">="), ("tokenCountRange", [True, 255]), ("rule", "average")):
            mutations.append({**valid, "policy": {**valid["policy"], key: value}})
        for config in mutations:
            self.signed_write(path, config, "configSha256")
            with self.subTest(config=config), self.assertRaises(ValueError):
                cq.load_frozen(path, export_hash)

    def test_changed_current_threshold_or_policy_source_invalidates_verification(self):
        verification = self.verification()
        replacement = self.root / "changed-policy.kt"
        replacement.write_text("different source")
        for target, value in (("ORIGINAL_ADVANTAGE", 0.0), ("RIVAL_ADVANTAGE", 0.0), ("POLICY", replacement)):
            with mock.patch.object(cq, target, value), self.assertRaisesRegex(ValueError, "VERIFICATION_POLICY"):
                cq.load_verification(verification)

    def test_artifact_and_receipt_tampering_invalidates_verification(self):
        verification = self.verification()
        for name in cq.VERIFICATION_FILES:
            path = verification / name
            original = path.read_bytes()
            path.write_bytes(original + b"tampered")
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "VERIFICATION_IDENTITY"):
                cq.load_verification(verification)
            path.write_bytes(original)
        path = verification / "verification.json"
        receipt = json.loads(path.read_text())
        path.write_text(json.dumps({**receipt, "cases": 0}))
        with self.assertRaisesRegex(ValueError, "VERIFICATION_RECEIPT"):
            cq.load_verification(verification)

    def test_rehashed_wrong_probe_commands_or_output_do_not_authorize_freeze(self):
        verification = self.verification()
        path = verification / "verification.json"
        receipt = json.loads(path.read_text())
        changed = copy.deepcopy(receipt)
        changed["compileCommand"][-1] = "different-probe.kt"
        self.signed_write(path, changed, "receiptSha256")
        with self.assertRaisesRegex(ValueError, "VERIFICATION_TOOLCHAIN"):
            cq.load_verification(verification)
        (verification / "actual.tsv").write_text("0\t999\n")
        changed = copy.deepcopy(receipt)
        changed["files"]["actual.tsv"] = cq.shared.sha(verification / "actual.tsv")
        self.signed_write(path, changed, "receiptSha256")
        with self.assertRaisesRegex(ValueError, "VERIFICATION_OUTPUT"):
            cq.load_verification(verification)

    def test_compile_probe_and_java_failures_leave_no_verification_receipt(self):
        for stage in ("version", "compile", "probe"):
            output = self.root / stage
            def fail(command, **kwargs):
                current = "version" if command[-1] == "-version" else \
                    "compile" if "org.jetbrains.kotlin.cli.jvm.K2JVMCompiler" in command else "probe"
                if current == stage: raise subprocess.CalledProcessError(1, command)
                return self.fake_process(command, **kwargs)
            with mock.patch.object(cq.subprocess, "run", side_effect=fail), self.assertRaises(subprocess.CalledProcessError):
                cq.verification_run(SimpleNamespace(output=output, java=self.java, gradle_cache=self.root))
            self.assertFalse((output / "verification.json").exists())

    def test_wrong_parity_output_and_wrong_java_version_leave_no_receipt(self):
        for mode in ("mismatch", "old-java"):
            output = self.root / mode
            def respond(command, **kwargs):
                if mode == "old-java" and command[-1] == "-version":
                    return subprocess.CompletedProcess(command, 0, b"", b'openjdk version "11.0"\n')
                result = self.fake_process(command, **kwargs)
                if mode == "mismatch" and command[-1].endswith("inputs.tsv"):
                    kwargs["stdout"].write(b"extra output\n")
                return result
            with mock.patch.object(cq.subprocess, "run", side_effect=respond), self.assertRaisesRegex(ValueError, "POLICY_PARITY|JAVA_17"):
                cq.verification_run(SimpleNamespace(output=output, java=self.java, gradle_cache=self.root))
            self.assertFalse((output / "verification.json").exists())

    def test_model_backend_guards_still_reject_runner_model_and_protocol_drift(self):
        identity = {"protocol": "p", "modelSha256": "m", "runnerSha256": "r", "corpusSha256": "calibration"}
        cq.require_backend(identity, {**identity, "corpusSha256": "holdout"})
        for key in ("protocol", "modelSha256", "runnerSha256"):
            with self.assertRaisesRegex(ValueError, "FROZEN_MODEL_IDENTITY"):
                cq.require_backend(identity, {**identity, key: "changed"})

    def test_current_score_cache_binds_the_run_receipt_and_rejects_mutation(self):
        identity = {"protocol": cq.evaluator().PROTOCOL, "corpusSha256": cq.evaluator().digest([]),
                    "runnerSha256": "synthetic-runner", "modelSha256": "synthetic-model"}
        cache = self.root / "scores.jsonl"
        cache.write_text(json.dumps({"cacheIdentity": identity}) + "\n")
        run_input = {**cq.policy_binding(), "scope": "contextual-calibration-scores", "split": "calibration",
                     "requests": 0, "identity": identity, "exportReceiptSha256": "synthetic-export",
                     "frozenConfigSha256": None}
        complete = {**run_input, "scores": 0, "runtimeErrors": 0, "scoresSha256": cq.shared.sha(cache)}
        (self.root / "run-input.json").write_text(json.dumps(run_input))
        (self.root / "complete.json").write_text(json.dumps(complete))
        self.assertEqual((complete, {}), cq.load_scores(self.root, []))
        (self.root / "run-input.json").write_text(json.dumps({**run_input, "exportReceiptSha256": "changed"}))
        with self.assertRaisesRegex(ValueError, "SCORES_RECEIPT"):
            cq.load_scores(self.root, [])
        (self.root / "run-input.json").write_text(json.dumps(run_input))
        cache.write_text(cache.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "COMPLETE_SCORES"):
            cq.load_scores(self.root, [])

    def test_exact_backend_config_is_accepted_and_runner_mutation_is_rejected(self):
        runner, model = self.root / "runner", self.root / "model"
        runner.write_bytes(b"synthetic runner")
        model.write_bytes(b"synthetic model")
        identity = {"runnerSha256": cq.shared.sha(runner), "modelSha256": cq.shared.sha(model)}
        config = self.root / "backend.json"
        self.signed_write(config, {"modelIdentity": identity}, "configSha256")
        self.assertEqual(identity, cq.verified_model(config, runner, model))
        runner.write_bytes(b"changed runner")
        with self.assertRaisesRegex(ValueError, "MODEL_IDENTITY"):
            cq.verified_model(config, runner, model)

    def scoring_fixture(self, name, split):
        directory = self.root / name
        directory.mkdir()
        export = directory / "export"
        export.mkdir()
        (export / "provenance.json").write_text("synthetic current export")
        runner, model, config = (directory / name for name in ("runner", "model", "backend.json"))
        runner.write_bytes(b"synthetic runner, never executed")
        model.write_bytes(b"synthetic model")
        self.signed_write(config, {"modelIdentity": {"runnerSha256": cq.shared.sha(runner),
                         "modelSha256": cq.shared.sha(model)}}, "configSha256")
        records = [{"id": f"synthetic-{i}", "split": split, "prefix": "synthetic ",
                    "variants": [{"id": j, "continuation": f"fixture-{j}"} for j in range(7)] if i == 0 else []}
                   for i in range(600)]
        selected = cq.requests(records, split)
        identity = cq.evaluator().cache_identity(selected, runner, model, cq.shared.sha(model), model.stat().st_size)
        frozen = {"configSha256": "synthetic-frozen-config", "modelIdentity": identity}
        run_input = {**cq.policy_binding(), "scope": f"contextual-{split}-scores", "split": split,
                     "requests": 1, "identity": identity,
                     "exportReceiptSha256": cq.shared.sha(export / "provenance.json"),
                     "frozenConfigSha256": frozen["configSha256"] if split == "holdout" else None}
        response = {"id": "synthetic-0", "durationMillis": 1,
                    "scores": [{"id": i, "sumLogProbability": -1 if i == 1 else -10,
                                "scoredTokenCount": 1} for i in range(7)]}
        cache = json.dumps({"cacheIdentity": identity}) + "\n" + json.dumps(response) + "\n"
        output = directory / "output"
        output.mkdir()
        args = SimpleNamespace(export=export, output=output, model_config=config, runner=runner, model=model,
            split=split, frozen_config=directory / "frozen.json", limit=None, expected_model_bytes=model.stat().st_size)
        return args, records, frozen, run_input, cache

    def test_score_run_rejects_orphan_cache_or_completion_before_receipt_or_scorer(self):
        for split in ("calibration", "holdout"):
            for artifacts in (("scores.jsonl",), ("complete.json",), ("scores.jsonl", "complete.json")):
                with self.subTest(split=split, artifacts=artifacts):
                    args, records, frozen, _, cache = self.scoring_fixture(f"{split}-{len(artifacts)}-{artifacts[0]}", split)
                    for name in artifacts:
                        (args.output / name).write_text(cache if name == "scores.jsonl" else "orphan completion")
                    before = {path.name: path.read_bytes() for path in args.output.iterdir()}
                    scorer_entries = []
                    def synthetic_scorer(*unused_args):
                        scorer_entries.append(True)
                        if not (args.output / "scores.jsonl").exists():
                            (args.output / "scores.jsonl").write_text(cache)
                    with mock.patch.object(cq, "load_export", return_value=records), \
                         mock.patch.object(cq, "load_frozen", return_value=frozen), \
                         mock.patch.object(cq, "score_requests", side_effect=synthetic_scorer), redirect_stdout(io.StringIO()):
                        with self.assertRaisesRegex(ValueError, "ORPHAN_SCORE_ARTIFACTS"):
                            cq.score_run(args)
                    self.assertEqual([], scorer_entries)
                    self.assertFalse((args.output / "run-input.json").exists())
                    self.assertEqual(before, {path.name: path.read_bytes() for path in args.output.iterdir()})

    def test_score_run_resumes_only_exact_v2_receipt_and_preserves_complete_cache(self):
        for split in ("calibration", "holdout"):
            args, records, frozen, run_input, cache = self.scoring_fixture(f"resume-{split}", split)
            (args.output / "scores.jsonl").write_text(cache)
            (args.output / "run-input.json").write_text(json.dumps(run_input))
            complete = {**run_input, "scores": 1, "runtimeErrors": 0,
                        "scoresSha256": cq.shared.sha(args.output / "scores.jsonl")}
            (args.output / "complete.json").write_text(json.dumps(complete))
            before = {path.name: path.read_bytes() for path in args.output.iterdir()}
            with mock.patch.object(cq, "load_export", return_value=records), \
                 mock.patch.object(cq, "load_frozen", return_value=frozen), \
                 mock.patch.object(cq.subprocess, "Popen", side_effect=AssertionError("Cached resume must not execute a runner")), \
                 redirect_stdout(io.StringIO()):
                cq.score_run(args)
                self.assertEqual(before, {path.name: path.read_bytes() for path in args.output.iterdir()})
                self.assertEqual(complete, cq.load_scores(args.output, cq.requests(records, split))[0])
                (args.output / "run-input.json").write_text(json.dumps({**run_input, "schemaVersion": 1}))
                with self.assertRaisesRegex(ValueError, "RESUME_IDENTITY"):
                    cq.score_run(args)


if __name__ == "__main__": unittest.main()
