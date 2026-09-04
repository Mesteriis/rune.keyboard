#!/usr/bin/env python3
"""Numerical and data-integrity regression tests; no model artifact needed."""
from __future__ import annotations
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import sys

import evaluate as ev
import generate_corpus as corpus


def row(sid: str = "test", split: str = "calibration", cohort: str = "typo") -> dict:
    return {"corpusVersion": 2, "expectedSpelling": "word", "id": sid, "language": "en", "split": split, "family": sid, "template": sid, "source": "test", "category": "test", "prefix": "a " + sid, "task": "spelling", "cohort": cohort, "typed": "wrod", "candidates": [" wrod", " word", " wrods"], "expectedCandidate": 1 if cohort == "typo" else 0, "noAuto": cohort == "protected"}


def response(sample: dict, means: tuple[float, ...] = (-4., -.1, -3.)) -> dict:
    return {"id": sample["id"], "scores": [{"id": i, "sumLogProbability": value * (i + 1), "scoredTokenCount": i + 1} for i, value in enumerate(means)], "durationMillis": 1.5}


class CorpusTests(unittest.TestCase):
    def test_full_corpus_counts_and_disjoint_splits(self) -> None:
        rows = ev.load_corpus()
        summary = ev.validate(rows)
        self.assertEqual(13200, summary["samples"])
        for language in ev.LANGUAGES:
            for split in ("calibration", "holdout"):
                subset = [r for r in rows if r["language"] == language and r["split"] == split]
                self.assertEqual(1000, sum(r["cohort"] == "typo" for r in subset))
                self.assertGreaterEqual(len({r["family"] for r in subset if r["cohort"] == "typo"}), 100)
                self.assertGreater(len({r["expectedCandidate"] for r in subset if r["cohort"] == "typo"}), 1)
                self.assertTrue(all(r["noAuto"] for r in subset if r["cohort"] == "protected"))

    def test_bounded_edit_neighbourhood_and_real_word_competitors(self) -> None:
        self.assertEqual(1, ev.edit_distance("teh", "the"))
        self.assertEqual(2, ev.edit_distance("correcion", "corrección"))
        known = json.loads((ev.ROOT / "nearby-words.json").read_text())
        rows = ev.load_corpus()
        for language in ev.LANGUAGES:
            for split in ("calibration", "holdout"):
                real_competitors = 0
                for sample in rows:
                    if sample["language"] != language or sample["split"] != split or sample["task"] != "spelling":
                        continue
                    limit = 1 if len(sample["typed"]) < 5 else 2
                    self.assertTrue(all(ev.edit_distance(sample["typed"].casefold(), candidate[1:].casefold()) <= limit for candidate in sample["candidates"]))
                    if sample["cohort"] == "correct":
                        real_competitors += any(candidate[1:].casefold() in known[language].get(sample["typed"].casefold(), []) for candidate in sample["candidates"][1:])
                self.assertGreater(real_competitors, 300)
        bad = row()
        bad["candidates"][2] = " unrelated"
        with self.assertRaisesRegex(ValueError, "neighbourhood"):
            ev.validate([bad], False)

    def test_orthographic_pairs_are_explicit_and_disjoint(self) -> None:
        rows = ev.load_corpus()
        groups = {split: set() for split in ("calibration", "holdout")}
        for language in ev.LANGUAGES:
            for split in groups:
                subset = [r for r in rows if r["language"] == language and r["split"] == split and "orthographicPolicy" in r]
                self.assertEqual({"en_optional_accent", "es_ambiguous_accent", "ru_yo_e"}, {r["orthographicKind"] for r in subset})
                for sample in subset:
                    self.assertIn(" " + sample["orthographicAlternative"], sample["candidates"])
                    self.assertNotEqual(sample["typed"], sample["orthographicAlternative"])
                    self.assertEqual(ev.orthographic_base(sample["typed"]), ev.orthographic_base(sample["orthographicAlternative"]))
                    self.assertEqual(0, sample["expectedCandidate"])
                    self.assertTrue(sample["noAuto"])
                    groups[split].add((language, ev.orthographic_base(sample["typed"])))
        self.assertFalse(groups["calibration"] & groups["holdout"])
        sky = [r for r in rows if r.get("typed") == "небо"]
        self.assertEqual(3, len(sky))
        self.assertTrue(all(r["category"] == "protected_correct_word" and "orthographicPolicy" not in r and " нёбо" not in r["candidates"] for r in sky))

    def test_orthographic_annotation_requires_actual_candidate_contrast(self) -> None:
        sample = next(r for r in ev.load_corpus() if "orthographicPolicy" in r)
        sample["candidates"].remove(" " + sample["orthographicAlternative"])
        with self.assertRaisesRegex(ValueError, "actual orthographic contrast"):
            ev.validate([sample], False)

    def test_expected_spelling_is_independent_of_label_index(self) -> None:
        sample = row()
        sample["expectedSpelling"] = "ward"
        with self.assertRaisesRegex(ValueError, "expected spelling"):
            ev.validate([sample], False)

    def test_manifest(self) -> None:
        manifest = json.loads((ev.ROOT / "manifest.json").read_text())
        self.assertEqual(2, manifest["version"])
        for name, sha in manifest["files"].items():
            self.assertEqual(sha, ev.file_hash(ev.ROOT / name))
        self.assertEqual(manifest["seedSha256"], ev.file_hash(ev.ROOT / "seeds.json"))
        self.assertEqual(manifest["nearbyWordsSha256"], ev.file_hash(ev.ROOT / "nearby-words.json"))
        self.assertEqual(manifest["generatorSha256"], ev.file_hash(ev.ROOT / "generate_corpus.py"))

    def test_duplicate_and_split_leakage_rejected(self) -> None:
        first, second = row(), row("second", "holdout")
        ev.validate([first, second], False)
        for key in ("family", "template"):
            changed = copy.deepcopy(second)
            changed[key] = first[key]
            with self.assertRaisesRegex(ValueError, "leakage"):
                ev.validate([first, changed], False)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            ev.validate([first, first], False)

    def test_punctuation_preserves_word_and_labels(self) -> None:
        samples = corpus.punctuation_rows()
        ev.validate(samples, False)
        sample = copy.deepcopy(samples[0])
        sample["candidates"][-1] += " extra"
        with self.assertRaisesRegex(ValueError, "punctuation"):
            ev.validate([sample], False)

    def test_protection_and_original_are_required(self) -> None:
        sample = row(cohort="protected")
        sample["noAuto"] = False
        with self.assertRaisesRegex(ValueError, "protected"):
            ev.validate([sample], False)
        sample = row()
        sample["candidates"][0] = " discarded"
        with self.assertRaisesRegex(ValueError, "original"):
            ev.validate([sample], False)


class NumericTests(unittest.TestCase):
    def test_average_not_sum_and_stable_confidence(self) -> None:
        sample = row()
        feature = ev.features(sample, response(sample, (-2., -1.5, -2.5)))
        self.assertEqual(1, feature["best"])
        self.assertAlmostEqual(.5, feature["margin"])
        self.assertAlmostEqual(1 / (1 + math.exp(-.5) + math.exp(-1)), feature["confidence"])

    def test_ties_abstain_and_original_wins_tie(self) -> None:
        sample = row()
        feature = ev.features(sample, response(sample, (-1., -1., -2.)))
        self.assertEqual(0, feature["best"])
        self.assertFalse(ev.automatic(sample, feature, {"margin": 0., "confidence": 0.}))

    def test_zero_token_or_error_abstains(self) -> None:
        sample = row()
        output = response(sample)
        output["scores"][1].update(scoredTokenCount=0, sumLogProbability=0.)
        self.assertIsNone(ev.features(sample, output))
        self.assertIsNone(ev.features(sample, {"id": sample["id"], "error": "SCORING_FAILED"}))
        self.assertFalse(ev.automatic(row(cohort="protected"), {"best": 1, "margin": 99, "confidence": 1}, {"margin": 0, "confidence": 0}))

    def test_invalid_response_rejected(self) -> None:
        sample = row()
        changes = [lambda v: v.update(id="different"), lambda v: v.update(text="forbidden"), lambda v: v["scores"][0].update(sumLogProbability=float("nan")), lambda v: v["scores"][0].update(id=1), lambda v: v["scores"][0].update(scoredTokenCount=-1), lambda v: v.update(durationMillis=-1), lambda v: v["scores"][0].update(scoredTokenCount=257), lambda v: v["scores"][0].update(scoredTokenCount=0), lambda v: v.update(error="arbitrary text")]
        for mutate in changes:
            output = response(sample)
            mutate(output)
            with self.assertRaises(ValueError):
                ev.validate_response(sample, output)

    def test_gate_denominators_and_insufficient_auto_count(self) -> None:
        examples = [row("typo"), row("correct", cohort="correct"), row("protected", cohort="protected"), row("missing")]
        scores = {r["id"]: response(r) for r in examples[:-1]}
        metrics = ev.language_metrics(examples, scores, {"margin": 0, "confidence": 0})
        self.assertEqual(2, metrics["automaticReplacements"])
        self.assertEqual(.5, metrics["precision"]["value"])
        self.assertEqual(1, metrics["falseChange"]["numerator"])
        self.assertEqual(2, metrics["falseChange"]["denominator"])
        self.assertEqual(1., metrics["falseChangeByCohort"]["correct"]["value"])
        self.assertEqual(0., metrics["falseChangeByCohort"]["protected"]["value"])
        self.assertEqual(.5, metrics["typoCorrectionCoverage"]["value"])
        self.assertFalse(metrics["passesRowGate"])
        self.assertEqual(1, metrics["missingScores"])

    def test_explicit_abstention_and_oracle_candidate_recall(self) -> None:
        typo, missing_gold = row("good"), row("missing-gold")
        missing_gold["candidates"] = [" wrod", " wrods"]
        protected = row("policy", cohort="protected")
        rejected = row("error")
        samples = [typo, missing_gold, protected, rejected]
        scores = {typo["id"]: response(typo), protected["id"]: response(protected), rejected["id"]: {"id": rejected["id"], "error": "SCORING_FAILED"}}
        metric = ev.language_metrics(samples, scores, {"margin": 0, "confidence": 0})
        self.assertEqual((3, 4, .75), tuple(metric["abstentionAllSpelling"][key] for key in ("numerator", "denominator", "value")))
        self.assertEqual((2, 3, 2/3), tuple(metric["preparedOracleCandidateRecall"][key] for key in ("numerator", "denominator", "value")))
        empty = ev.language_metrics([], {}, {"margin": 0, "confidence": 0})
        self.assertIsNone(empty["abstentionAllSpelling"]["value"])
        self.assertIsNone(empty["preparedOracleCandidateRecall"]["value"])

    def test_report_schema_and_markdown_require_explicit_metrics(self) -> None:
        sample = row()
        metric = ev.language_metrics([sample], {}, {"margin": 0, "confidence": 0})
        value = {"preparedCandidateRowGatePass": False, "frozenConfigSha256": "test", "identity": {}, "limitations": [], "splits": {"calibration": {"en": metric}, "holdout": {"en": metric}}}
        markdown = ev.markdown_report(value)
        self.assertTrue(markdown.startswith("# Rune Text candidate"))
        self.assertIn("Abstention (no auto/all spelling)", markdown)
        self.assertIn("Prepared oracle candidate recall (contained/all typos)", markdown)
        self.assertIn("100.00% (1/1)", markdown)
        schema = json.loads((ev.ROOT / "expected-report-schema.json").read_text())
        self.assertEqual(2, schema["properties"]["version"]["const"])
        self.assertTrue({"abstentionAllSpelling", "preparedOracleCandidateRecall"}.issubset(schema["$defs"]["metrics"]["required"]))

    def test_zero_replacements_has_undefined_precision(self) -> None:
        sample = row()
        metrics = ev.language_metrics([sample], {}, {"margin": 0, "confidence": 0})
        self.assertIsNone(metrics["precision"]["value"])
        self.assertFalse(metrics["passesRowGate"])
        self.assertEqual(0., metrics["top1Typo"]["value"])
        self.assertIsNone(ev.wilson(0, 0))
        self.assertAlmostEqual(.98736, ev.wilson(300, 300)[0], places=4)

    def test_calibration_independent_of_holdout(self) -> None:
        samples = [row("c"), row("h", "holdout")]
        scores = {r["id"]: response(r) for r in samples}
        identity = {"modelSha256": "model", "runnerSha256": "runner"}
        original = ev.calibrate(samples, scores, identity)
        samples[1]["expectedCandidate"] = 2
        scores["h"] = response(samples[1], (-.1, -20, -30))
        self.assertEqual(original, ev.calibrate(samples, scores, identity))
        scores["c"] = response(samples[0], (-.1, -20, -30))
        self.assertNotEqual(original, ev.calibrate(samples, scores, identity))

    def test_conservative_calibration_uses_wilson_bounds_and_minimum_volume(self) -> None:
        identity = {"modelSha256": "model", "runnerSha256": "runner"}

        def calibration_set(typo_count: int) -> tuple[list[dict], dict]:
            samples = [row(f"typo-{index}") for index in range(typo_count)]
            samples += [row(f"correct-{index}", cohort="correct") for index in range(1000)]
            scores = {
                sample["id"]: response(sample, (-4., -.1, -3.))
                if sample["cohort"] == "typo" else response(sample, (-.1, -4., -5.))
                for sample in samples
            }
            return samples, scores

        insufficient, insufficient_scores = calibration_set(300)
        legacy = ev.calibrate(insufficient, insufficient_scores, identity,
                              "legacy-point-estimate")
        conservative = ev.calibrate(insufficient, insufficient_scores, identity)
        self.assertNotEqual(1e9, legacy["languages"]["en"]["margin"])
        self.assertEqual({"margin": 1e9, "confidence": 1.0},
                         conservative["languages"]["en"])

        sufficient, sufficient_scores = calibration_set(500)
        conservative = ev.calibrate(sufficient, sufficient_scores, identity)
        self.assertEqual(2, conservative["version"])
        self.assertEqual("wilson95", conservative["selectionSafety"]["method"])
        self.assertNotEqual(1e9, conservative["languages"]["en"]["margin"])

    def test_unknown_calibration_selection_safety_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown calibration selection safety"):
            ev.calibrate([], {}, {"modelSha256": "model", "runnerSha256": "runner"},
                         "unsupported")

    def test_frozen_config_modification_rejected(self) -> None:
        samples = [row()]
        scores = {samples[0]["id"]: response(samples[0])}
        identity = {"modelSha256": "model", "runnerSha256": "runner"}
        frozen = ev.calibrate(samples, scores, identity)
        frozen["languages"]["en"]["margin"] += 1
        with self.assertRaisesRegex(ValueError, "modified"):
            ev.report(samples, scores, identity, frozen)


class CacheTests(unittest.TestCase):
    def test_identity_and_duplicate_guard(self) -> None:
        sample = row()
        identity = {"protocol": ev.PROTOCOL, "corpusSha256": ev.digest([sample]), "runnerSha256": "a", "modelSha256": "b"}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cache.jsonl"
            header = ev.canonical({"cacheIdentity": identity}) + b"\n"
            output = ev.canonical(response(sample)) + b"\n"
            path.write_bytes(header + output)
            _, results = ev.load_cache(path, [sample], identity)
            self.assertEqual(1, len(results))
            with self.assertRaisesRegex(ValueError, "mismatch"):
                ev.load_cache(path, [sample], {**identity, "runnerSha256": "changed"})
            path.write_bytes(header + output + output)
            with self.assertRaisesRegex(ValueError, "duplicate"):
                ev.load_cache(path, [sample])


class ScoringLifecycleTests(unittest.TestCase):
    def identity(self, samples: list[dict]) -> dict:
        return {"protocol": ev.PROTOCOL, "corpusSha256": ev.digest(samples), "runnerSha256": "test-only", "modelSha256": "test-only"}

    def test_persistent_runner_resume_and_freeze_order(self) -> None:
        samples = [row("first"), row("second"), row("third", "holdout")]
        identity = self.identity(samples)
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            runner, cache = folder / "runner", folder / "cache.jsonl"
            start_file = folder / "starts"
            runner.write_text("#!" + sys.executable + "\n" + "import json,sys\n" + "from pathlib import Path\n" + "p=Path(" + repr(str(start_file)) + ")\np.write_text(p.read_text()+'x' if p.exists() else 'x')\n" + "for line in sys.stdin:\n r=json.loads(line)\n print(json.dumps({'id':r['id'],'scores':[{'id':i,'sumLogProbability':-float(i+1),'scoredTokenCount':1} for i in range(len(r['candidates']))],'durationMillis':1}),flush=True)\n")
            runner.chmod(0o700)
            with mock.patch.object(ev, "cache_identity", return_value=identity):
                with self.assertRaisesRegex(ValueError, "requires"):
                    ev.score_corpus(samples, runner, folder / "unused", cache, 2, split="holdout")
                ev.score_corpus(samples, runner, folder / "unused", cache, 2)
                self.assertEqual("x", start_file.read_text())
                _, scores = ev.load_cache(cache, samples)
                self.assertEqual({"first", "second"}, set(scores))
                ev.score_corpus(samples, runner, folder / "unused", cache, 2)
                self.assertEqual("x", start_file.read_text())
                frozen_path = folder / "frozen.json"
                frozen_path.write_text(json.dumps(ev.calibrate(samples, scores, identity)))
                ev.score_corpus(samples, runner, folder / "unused", cache, 2, split="holdout", config_path=frozen_path)
                self.assertEqual("xx", start_file.read_text())
                _, scores = ev.load_cache(cache, samples)
                self.assertEqual(3, len(scores))
                with self.assertRaisesRegex(ValueError, "after holdout"):
                    ev.score_corpus(samples, runner, folder / "unused", cache, 2)

    def test_truncated_tail_repair_never_discards_complete_errors(self) -> None:
        sample = row()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cache.jsonl"
            complete = ev.canonical({"cacheIdentity": self.identity([sample])}) + b"\n" + ev.canonical({"id": sample["id"], "error": "SCORING_FAILED"}) + b"\n"
            path.write_bytes(complete + b'{"id":')
            with self.assertRaisesRegex(ValueError, "incomplete"):
                ev.load_cache(path, [sample])
            self.assertTrue(ev.repair_incomplete_tail(path, [sample]))
            self.assertEqual(complete, path.read_bytes())
            self.assertEqual("SCORING_FAILED", ev.load_cache(path, [sample])[1][sample["id"]]["error"])
            path.write_bytes(complete + b'{not-json}\npartial')
            with self.assertRaises(ValueError):
                ev.repair_incomplete_tail(path, [sample])
            self.assertTrue(path.read_bytes().endswith(b"partial"))

    def test_wrong_model_is_rejected_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "invalid.gguf"
            model.write_bytes(b"GGUF")
            with self.assertRaisesRegex(ValueError, "expected size and digest"):
                ev.cache_identity([row()], model, model)

    def test_explicit_model_identity_accepts_only_exact_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "candidate.gguf"
            runner = Path(directory) / "runner"
            artifact.write_bytes(b"candidate model")
            runner.write_bytes(b"runner")
            expected_sha = ev.file_hash(artifact)
            identity = ev.cache_identity(
                [row()], runner, artifact,
                expected_model_sha256=expected_sha,
                expected_model_size=artifact.stat().st_size,
            )
            self.assertEqual(expected_sha, identity["modelSha256"])
            for digest, size in ((expected_sha.upper(), artifact.stat().st_size),
                                 ("0" * 63, artifact.stat().st_size),
                                 (expected_sha, 0),
                                 (expected_sha, True)):
                with self.subTest(digest=digest, size=size):
                    with self.assertRaisesRegex(ValueError, "invalid expected model identity"):
                        ev.cache_identity([row()], runner, artifact, digest, size)
            with self.assertRaisesRegex(ValueError, "expected size and digest"):
                ev.cache_identity([row()], runner, artifact, "0" * 64,
                                  artifact.stat().st_size)

    def test_timeout_kills_runner_without_caching_result(self) -> None:
        samples = [row()]
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            runner = folder / "runner"
            runner.write_text("#!" + sys.executable + "\nimport time\ntime.sleep(10)\n")
            runner.chmod(0o700)
            with mock.patch.object(ev, "cache_identity", return_value=self.identity(samples)):
                with self.assertRaises(TimeoutError):
                    ev.score_corpus(samples, runner, folder / "unused", folder / "cache", .05)
            self.assertEqual({}, ev.load_cache(folder / "cache", samples)[1])


if __name__ == "__main__":
    unittest.main()
