#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("qualification_corpus", HERE / "generate_corpus.py")
CORPUS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CORPUS)


class QualificationCorpusTest(unittest.TestCase):
    def test_source_shards_are_pinned_and_distinct_from_training_v2_and_v3(self):
        current = json.loads((HERE / "source-lock.json").read_text())
        training = json.loads((HERE.parents[2] / "model/rune-text-0.2/source-lock.json").read_text())
        priors = [json.loads((HERE.parent / f"qualification-v{version}/source-lock.json").read_text())
                  for version in (2, 3)]
        paths = {item["repositoryPath"] for item in current["files"].values()}
        previous = {item["repositoryPath"] for item in training["wikipediaContext"]["files"].values()}
        for prior in priors:
            previous.update(item["repositoryPath"] for item in prior["files"].values())
        self.assertFalse(paths & previous)
        self.assertEqual(3, len(paths))
        for item in current["files"].values():
            self.assertGreater(item["bytes"], 100_000_000)
            self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")

    def test_protected_matrix_has_exact_split_counts_and_all_categories(self):
        expected_categories = {
            "name", "surname", "brand", "command", "camel_case", "snake_case",
            "kebab_case", "identifier_python", "identifier_cpp", "identifier_kotlin",
            "all_caps", "digits", "ambiguous_accent", "mixed", "hostname",
        }
        for language in CORPUS.LANGUAGES:
            rows = CORPUS.protected_rows(language)
            for split in ("calibration", "holdout"):
                selected = [row for row in rows if row["split"] == split]
                self.assertEqual(len(selected), 300)
                self.assertTrue(all(row["corpusVersion"] == 4 and "-v4-" in row["id"]
                                    for row in selected))
                self.assertEqual({row["category"] for row in selected}, expected_categories)
                self.assertTrue(all(row["expectedCandidate"] == 0 and row["noAuto"]
                                    for row in selected))
                self.assertEqual({row["orthographicKind"] for row in selected
                                  if "orthographicKind" in row}, {
                                      "en_optional_accent", "es_ambiguous_accent", "ru_yo_e"})

    def test_safe_typos_are_one_edit_and_never_known_words(self):
        known = {"keyboard", "keyboards"}
        values = CORPUS.safe_typos("keyboard", "en", known, "fixed")
        self.assertTrue(values)
        self.assertTrue(all(value not in known for value, _ in values))
        self.assertEqual(values, CORPUS.safe_typos("keyboard", "en", known, "fixed"))

    def test_bounded_punctuation_reservoir_keeps_smallest_hashes(self):
        heap, seen = [], set()
        for value in (9, 4, 7, 1, 3):
            identity = f"{value:064x}"
            CORPUS.keep_bounded(heap, seen, {"selectionHash": identity}, limit=3)
        self.assertEqual({int(entry[1], 16) for entry in heap}, {1, 3, 4})

    def test_all_prior_corpora_are_excluded_from_family_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            training = root / "training"
            training.mkdir()
            for name in ("train.jsonl", "valid.jsonl"):
                (training / name).write_text(json.dumps({"language": "en", "family": name}) + "\n")
            corpora = []
            for ordinal in range(2):
                corpus = root / f"corpus-{ordinal}"
                corpus.mkdir()
                corpora.append(corpus)
                for language in CORPUS.LANGUAGES:
                    for task in ("spelling", "punctuation"):
                        row = {"family": f"{language}-{task}-{ordinal}"}
                        (corpus / f"{task}-{language}.jsonl").write_text(json.dumps(row) + "\n")
            seen = CORPUS.seen_families(training, corpora)
            self.assertTrue({"train.jsonl", "valid.jsonl", "en-spelling-0", "en-spelling-1"}
                            .issubset(seen["en"]))


if __name__ == "__main__":
    unittest.main()
