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

    def test_fused_architecture_contract_is_complete(self):
        self.assertEqual(FUSE.ARCHITECTURE_KEYS, (
            "model_type", "hidden_size", "intermediate_size", "num_hidden_layers",
            "num_attention_heads", "num_key_value_heads", "vocab_size", "head_dim"))

    def test_every_artifact_stage_records_source_identity(self):
        for name in ("generate_pairwise_data.py", "train_pairwise.py",
                     "fuse_candidate.py", "build_gguf.py"):
            self.assertIn('"sources"', (HERE / name).read_text())

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


if __name__ == "__main__":
    unittest.main()
