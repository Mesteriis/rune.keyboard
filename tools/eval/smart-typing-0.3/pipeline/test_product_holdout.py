import unittest
import json
from pathlib import Path
import tempfile

from evaluate_product_holdout import metrics
from export_product_holdout import evaluator, holdout_rows, summary
from score_product_holdout import requests_from, score_requests


def row(identifier="en-holdout-1", cohort="typo", expected="hello"):
    value = {"id": identifier, "split": "holdout", "language": "en", "task": "spelling",
             "cohort": cohort, "typed": "helo", "prefix": "We say", "noAuto": False}
    if cohort == "typo": value["expectedSpelling"] = expected
    return value


def generation(identifier="en-holdout-1", alternatives=True):
    return {"id": identifier, "original": "helo", "prohibitsAutoReplace": False,
            "alternatives": ([{"id": 1, "text": "hello"}] if alternatives else [])}


class ProductHoldoutTest(unittest.TestCase):
    def test_final_qualification_corpus_is_selectable_without_mixing_evaluator_code(self):
        corpus = Path(__file__).resolve().parent.parent / "qualification-v2/corpus"
        ev, rows = holdout_rows(corpus)
        self.assertEqual(6000, len(rows))
        self.assertEqual({"en", "ru", "es"}, {item["language"] for item in rows})
        self.assertTrue(all(item["split"] == "holdout" and item["task"] == "spelling"
                            for item in rows))
        self.assertEqual(6000, sum(item["split"] == "holdout" for item in rows))
        self.assertTrue(callable(ev.cache_identity))

    def test_requests_are_holdout_only_and_never_include_labels(self):
        request = requests_from([row()], [generation()])[0]
        self.assertEqual(request, {"id": "en-holdout-1", "split": "holdout",
            "prefix": "We say ", "candidates": ["helo", "hello"]})
        with self.assertRaises(ValueError):
            requests_from([{**row(), "split": "calibration"}], [generation()])

    def test_original_only_rows_are_omitted_from_model_but_retained_in_export(self):
        self.assertEqual(requests_from([row()], [generation(alternatives=False)]), [])
        report = summary([row()], [generation(alternatives=False)], evaluator())
        self.assertTrue(report["languages"]["en"]["originalAvailable"])
        self.assertEqual(report["languages"]["en"]["candidateRecall"]["numerator"], 0)

    def test_quality_gate_counts_incorrect_and_protected_changes(self):
        rows = [row(), row("en-holdout-2", "protected")]
        generated = [generation(), {**generation("en-holdout-2"), "original": "token"}]
        rows[1]["typed"] = "token"
        result = metrics(rows, generated, [1, 1], evaluator())
        self.assertEqual(result["automaticReplacements"], 2)
        self.assertEqual(result["correctReplacements"], 1)
        self.assertEqual(result["falseChange"]["numerator"], 1)
        self.assertFalse(result["gate"]["pass"])

    def test_no_replacements_cannot_pass_precision_or_volume(self):
        result = metrics([row()], [generation()], [0], evaluator())
        self.assertFalse(result["gate"]["minimum300"])
        self.assertFalse(result["gate"]["precisionAtLeastTarget"])
        self.assertFalse(result["gate"]["pass"])

    def test_precision_target_is_explicit_and_bounded_to_supported_profiles(self):
        rows = [row(f"en-holdout-{index}") for index in range(20)]
        generated = [generation(item["id"]) for item in rows]
        decisions = [1] * 19 + [2]
        result = metrics(rows, generated, decisions, evaluator(), minimum_precision_percent=95)
        self.assertEqual(95, result["gate"]["minimumPrecisionPercent"])
        self.assertTrue(result["gate"]["precisionAtLeastTarget"])
        self.assertFalse(result["gate"]["precisionAtLeast99Percent"])

    def test_holdout_transport_scores_limit_then_resumes_without_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = root / "runner.py"
            runner.write_text("""#!/usr/bin/env python3
import json,sys
for line in sys.stdin:
 r=json.loads(line); print(json.dumps({'id':r['id'],'scores':[{'id':i,'sumLogProbability':-1.0-i,'scoredTokenCount':1} for i in range(len(r['candidates']))],'durationMillis':1}),flush=True)
""")
            runner.chmod(0o755)
            model = root / "model.gguf"
            model.write_bytes(b"fixture")
            requests = [
                {"id": "one", "split": "holdout", "prefix": "a ", "candidates": ["x", "y"]},
                {"id": "two", "split": "holdout", "prefix": "b ", "candidates": ["x", "z"]},
            ]
            cache = root / "scores.jsonl"
            class FakeEvaluator:
                @staticmethod
                def canonical(value):
                    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
                @staticmethod
                def cache_identity(_requests, _runner, _model):
                    return {"protocol": "rune-score-jsonl-v1", "fixture": True}
                @staticmethod
                def validate_response(request, response):
                    if response["id"] != request["id"] or len(response["scores"]) != len(request["candidates"]):
                        raise ValueError("RESPONSE")
                @staticmethod
                def load_cache(path, requests, identity):
                    lines = [json.loads(line) for line in path.read_text().splitlines()]
                    if lines[0] != {"cacheIdentity": identity}:
                        raise ValueError("IDENTITY")
                    known = {request["id"] for request in requests}
                    scores = {item["id"]: item for item in lines[1:]}
                    if not set(scores) <= known:
                        raise ValueError("UNKNOWN")
                    return identity, scores
            ev = FakeEvaluator()
            score_requests(requests, runner, model, cache, ev, limit=1)
            self.assertEqual(len(cache.read_text().splitlines()), 2)
            score_requests(requests, runner, model, cache, ev)
            identity, scores = ev.load_cache(cache, requests, ev.cache_identity(requests, runner, model))
            self.assertEqual(set(scores), {"one", "two"})
            self.assertEqual(identity["protocol"], "rune-score-jsonl-v1")

    def test_holdout_transport_binds_explicit_candidate_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = root / "runner.py"
            runner.write_text("""#!/usr/bin/env python3
import json,sys
for line in sys.stdin:
 r=json.loads(line); print(json.dumps({'id':r['id'],'scores':[{'id':i,'sumLogProbability':-1.0-i,'scoredTokenCount':1} for i in range(len(r['candidates']))],'durationMillis':1}),flush=True)
""")
            runner.chmod(0o755)
            model = root / "candidate.gguf"
            model.write_bytes(b"candidate")
            request = {"id": "one", "split": "holdout", "prefix": "a ",
                       "candidates": ["x", "y"]}
            ev = evaluator()
            digest = ev.file_hash(model)
            cache = root / "scores.jsonl"
            score_requests([request], runner, model, cache, ev,
                           expected_model_sha256=digest,
                           expected_model_size=model.stat().st_size)
            identity = ev.cache_identity([request], runner, model, digest,
                                         model.stat().st_size)
            self.assertEqual(digest, ev.load_cache(cache, [request], identity)[0]["modelSha256"])


if __name__ == "__main__":
    unittest.main()
