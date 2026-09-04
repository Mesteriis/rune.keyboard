#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("pair_data", HERE / "generate_pairwise_data.py")
DATA = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DATA)
FUSE_SPEC = importlib.util.spec_from_file_location("fuse_candidate", HERE / "fuse_candidate.py")
FUSE = importlib.util.module_from_spec(FUSE_SPEC)
FUSE_SPEC.loader.exec_module(FUSE)
GGUF_SPEC = importlib.util.spec_from_file_location("build_gguf", HERE / "build_gguf.py")
GGUF = importlib.util.module_from_spec(GGUF_SPEC)
GGUF_SPEC.loader.exec_module(GGUF)
SAMPLING_SPEC = importlib.util.spec_from_file_location("validation_sampling", HERE / "validation_sampling.py")
SAMPLING = importlib.util.module_from_spec(SAMPLING_SPEC)
SAMPLING_SPEC.loader.exec_module(SAMPLING)
CONTEXT_SPEC = importlib.util.spec_from_file_location(
    "prepare_wikipedia_context", HERE / "prepare_wikipedia_context.py")
CONTEXT = importlib.util.module_from_spec(CONTEXT_SPEC)
CONTEXT_SPEC.loader.exec_module(CONTEXT)


class PairwiseDataTest(unittest.TestCase):
    def test_family_groups_accents_and_yo(self):
        self.assertEqual(DATA.family("всё"), DATA.family("все"))
        self.assertEqual(DATA.family("acción"), DATA.family("accion"))

    def test_mutations_exclude_valid_words_and_are_stable(self):
        first = DATA.mutations("keyboard", "en", {"keyboard", "keyboards"}, "seed")
        second = DATA.mutations("keyboard", "en", {"keyboard", "keyboards"}, "seed")
        self.assertEqual(first, second)
        self.assertNotIn("keyboards", [value for value, _ in first])
        self.assertGreaterEqual(len({category for _, category in first}), 4)

    def test_write_rows_is_canonical_jsonl(self):
        rows = [{"rejected": " worl", "chosen": " world", "prefix": "Hello", "id": "x"}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rows.jsonl"
            DATA.write_rows(path, rows)
            self.assertEqual(json.loads(path.read_text()), rows[0])
            self.assertEqual(path.read_bytes(), DATA.canonical(rows[0]) + b"\n")

    def test_configuration_preserves_runtime_compute_class(self):
        config = json.loads((HERE / "training-config.json").read_text())
        self.assertEqual(config["baseModel"], "Qwen/Qwen3-0.6B-Base")
        self.assertEqual(config["output"], {
            "architecture": "qwen3", "quantization": "Q4_K_M", "runtimeAdapter": False})
        self.assertLessEqual(config["maximumSequenceTokens"], 256)

    def test_candidate_04_expands_training_only_and_preserves_runtime_compute_class(self):
        previous = json.loads((HERE / "training-config.json").read_text())
        candidate = json.loads((HERE / "training-config-candidate-04.json").read_text())
        self.assertEqual(candidate["baseModel"], previous["baseModel"])
        self.assertEqual(candidate["baseRevision"], previous["baseRevision"])
        self.assertEqual(candidate["objective"], previous["objective"])
        self.assertEqual(candidate["output"], previous["output"])
        self.assertGreater(candidate["trainWordsPerLanguage"], previous["trainWordsPerLanguage"])
        self.assertGreater(candidate["wikipediaContext"]["trainingRowsPerLanguage"],
                           previous["wikipediaContext"]["trainingRowsPerLanguage"])
        self.assertGreater(candidate["validationWordsPerLanguage"],
                           previous["validationWordsPerLanguage"])
        self.assertLessEqual(candidate["maximumSequenceTokens"], 256)

    def test_candidate_05_prioritizes_hard_negatives_without_expanding_runtime_model(self):
        previous = json.loads((HERE / "training-config-candidate-04.json").read_text())
        candidate = json.loads((HERE / "training-config-candidate-05.json").read_text())
        self.assertEqual(candidate["baseModel"], previous["baseModel"])
        self.assertEqual(candidate["baseRevision"], previous["baseRevision"])
        self.assertEqual(candidate["objective"], previous["objective"])
        self.assertEqual(candidate["output"], previous["output"])
        self.assertGreater(candidate["productCalibration"]["trainingRepeat"],
                           previous["productCalibration"]["trainingRepeat"])
        self.assertGreater(candidate["training"]["iterations"],
                           previous["training"]["iterations"])
        self.assertLessEqual(
            candidate["wikipediaContext"]["trainingRowsPerLanguage"]
            + candidate["wikipediaContext"]["validationRowsPerLanguage"], 13_500)
        self.assertLessEqual(candidate["maximumSequenceTokens"], 256)

    def test_fused_architecture_contract_is_complete(self):
        self.assertEqual(FUSE.ARCHITECTURE_KEYS, (
            "model_type", "hidden_size", "intermediate_size", "num_hidden_layers",
            "num_attention_heads", "num_key_value_heads", "vocab_size", "head_dim"))

    def test_every_artifact_stage_records_source_identity(self):
        for name in ("download_wikipedia_context.py", "prepare_wikipedia_context.py",
                     "generate_pairwise_data.py", "train_pairwise.py",
                     "fuse_candidate.py", "build_gguf.py"):
            if name.startswith("download_"):
                self.assertIn('"sha256"', (HERE / name).read_text())
            else:
                self.assertIn('"sources"', (HERE / name).read_text())

    def test_production_export_source_closure_includes_canonical_case_contract(self):
        exporter = (HERE.parents[1] / "eval/smart-typing-0.3/pipeline/export_calibration.py").read_text()
        self.assertIn('"CanonicalCaseLexicon"', exporter)

    def test_candidate_size_does_not_expand_current_compute_class(self):
        self.assertEqual(GGUF.ASSET, "rune-text-v1-0.2.0-q4_k_m.gguf")
        self.assertLessEqual(GGUF.MAXIMUM_ARTIFACT_BYTES, 420_000_000)

    def test_converter_toolchain_is_fully_pinned(self):
        lock = json.loads((HERE / "converter-toolchain-lock.json").read_text())
        self.assertEqual(set(lock), {
            "python", "torch", "transformers", "tokenizers", "sentencepiece"})

    def test_validation_sample_is_language_balanced(self):
        languages = ["en"] * 1000 + ["ru"] * 1000 + ["es"] * 1000
        selected = SAMPLING.balanced_indices(languages, 500)
        counts = {language: sum(languages[index] == language for index in selected)
                  for language in ("en", "ru", "es")}
        self.assertEqual(sum(counts.values()), 500)
        self.assertLessEqual(max(counts.values()) - min(counts.values()), 1)
        self.assertEqual(selected, SAMPLING.balanced_indices(languages, 500))

    def test_product_pairs_use_context_and_never_holdout(self):
        rows = [{"id": "en-calibration-typo-0", "language": "en", "split": "calibration",
                 "task": "spelling", "cohort": "typo", "noAuto": False,
                 "expectedSpelling": "word", "typed": "wrod", "family": "word",
                 "prefix": "Check the", "category": "transposition"}]
        generated = [{"id": rows[0]["id"], "original": "wrod",
                      "alternatives": [{"id": 1, "text": "ward"}, {"id": 2, "text": "word"}]}]
        train, valid = DATA.product_pairs(rows, generated, 3, 80, 2)
        pairs = train + valid
        self.assertTrue(pairs)
        self.assertTrue(all(row["prefix"] == "Check the " and row["chosen"] == "word"
                            and row["rejected"] != "word" for row in pairs))
        self.assertTrue(all("holdout" not in row["id"] for row in pairs))

    def test_product_pairs_teach_original_against_wrong_generated_alternatives(self):
        rows = [
            {"id": "en-calibration-correct-0", "language": "en", "split": "calibration",
             "task": "spelling", "cohort": "correct", "noAuto": False,
             "typed": "their", "family": "their", "prefix": "Check", "category": "correct_word"},
            {"id": "en-calibration-protected-0", "language": "en", "split": "calibration",
             "task": "spelling", "cohort": "protected", "noAuto": True,
             "typed": "GitHub", "family": "github", "prefix": "Open", "category": "mixed_case"},
        ]
        generated = [
            {"id": rows[0]["id"], "original": "their",
             "alternatives": [{"id": 1, "text": "there"}, {"id": 2, "text": "thier"}]},
            {"id": rows[1]["id"], "original": "GitHub", "alternatives": []},
        ]
        train, valid = DATA.product_pairs(rows, generated, 3, 80, 2)
        pairs = train + valid
        self.assertEqual({row["chosen"] for row in pairs}, {"their"})
        self.assertEqual({row["rejected"] for row in pairs}, {"there", "thier"})
        self.assertTrue(all(row["category"] == "product_original:correct_word" for row in pairs))

    def test_product_calibration_uses_central_evaluator_for_nested_corpus(self):
        self.assertEqual(DATA.EVALUATOR,
                         HERE.parents[1] / "eval/smart-typing-0.3/evaluate.py")
        source = (HERE / "generate_pairwise_data.py").read_text()
        self.assertIn("evaluator.load_corpus(corpus)", source)

    def test_wikipedia_context_uses_real_prefix_and_safe_mutation(self):
        rows = CONTEXT.context_pairs(
            "People often use a compact keyboard for writing.", "en",
            {"people", "often", "use", "compact", "keyboard", "writing"}, set(),
            4, 20, 4, 256, 3042026)
        keyboard = [row for row in rows if row["chosen"] == "keyboard"]
        self.assertEqual(len(keyboard), 1)
        self.assertEqual(keyboard[0]["prefix"], "People often use a compact ")
        self.assertNotIn(keyboard[0]["rejected"], {
            "people", "often", "use", "compact", "keyboard", "writing"})
        self.assertEqual(keyboard[0]["source"], "wikimedia_wikipedia_20231101")

    def test_wikipedia_prefix_is_utf8_bounded_at_a_word_boundary(self):
        prefix = CONTEXT.bounded_prefix("раз два три четыре пять ", 22)
        self.assertLessEqual(len(prefix.encode("utf-8")), 22)
        self.assertTrue(prefix.endswith(" "))
        self.assertFalse(prefix.startswith(" "))

    def test_wikipedia_selection_keeps_one_context_per_family(self):
        rows = [
            {"family": "word", "selectionHash": "b", "id": "second"},
            {"family": "word", "selectionHash": "a", "id": "first"},
            {"family": "other", "selectionHash": "c", "id": "other"},
        ]
        self.assertEqual([row["id"] for row in CONTEXT.select_unique(rows, 2)],
                         ["first", "other"])

    def test_wikipedia_split_excludes_existing_and_is_family_disjoint(self):
        pool = [{"id": f"pool-{index}", "language": language, "family": f"family-{index}",
                 "split": "pool", "source": "wikimedia_wikipedia_20231101"}
                for language in DATA.LANGUAGES for index in range(8)]
        existing_train = [{"language": language, "family": "family-0"}
                          for language in DATA.LANGUAGES]
        train, valid, receipt = DATA.split_context_pool(
            pool, existing_train, [], 3042026, 3, 2)
        self.assertEqual(len(train), 9)
        self.assertEqual(len(valid), 6)
        self.assertFalse({(row["language"], row["family"]) for row in train} &
                         {(row["language"], row["family"]) for row in valid})
        self.assertTrue(all(row["family"] != "family-0" for row in train + valid))
        self.assertTrue(all(receipt[language]["eligibleAfterExistingFamilies"] == 7
                            for language in DATA.LANGUAGES))


if __name__ == "__main__":
    unittest.main()
