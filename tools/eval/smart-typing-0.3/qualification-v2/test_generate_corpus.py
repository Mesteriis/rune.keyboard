#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("qualification_corpus", HERE / "generate_corpus.py")
CORPUS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CORPUS)


class QualificationCorpusTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
