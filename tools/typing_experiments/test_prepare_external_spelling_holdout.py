import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("prepare_external_spelling_holdout.py")
SPEC = importlib.util.spec_from_file_location("prepare_external_spelling_holdout", SCRIPT)
holdout = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(holdout)


class FakeGenerator:
    @staticmethod
    def safe_typos(word, _language, _known, _seed):
        return [(word[:-1], "missing_letter")]


class ExternalHoldoutTest(unittest.TestCase):
    def test_build_rows_is_family_disjoint_and_has_controls(self):
        pool = [{"word": f"слово{i}", "family": f"слово{i}", "prefix": "Это контекст",
                 "selectionHash": f"{i:064x}"} for i in range(8)]
        rows = holdout.build_rows(pool, set(), FakeGenerator, typo_count=3, correct_count=2)
        self.assertEqual({"typo": 3, "correct": 2},
                         {name: sum(row["cohort"] == name for row in rows)
                          for name in ("typo", "correct")})
        self.assertEqual(len(rows), len({row["family"] for row in rows}))
        self.assertTrue(all(row["split"] == "holdout" and row["corpusVersion"] == 6
                            for row in rows))
        self.assertTrue(all("expectedSpelling" not in row for row in rows
                            if row["cohort"] == "correct"))

    def test_exclusion_rows_are_bound_and_normalized(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rows.jsonl"
            path.write_text(json.dumps({"family": "Ёлка"}, ensure_ascii=False) + "\n")
            families, bindings, count = holdout.excluded_families(
                [path], lambda value: value.casefold().replace("ё", "е"))
            self.assertEqual({"елка"}, families)
            self.assertEqual(1, count)
            self.assertEqual(1, len(bindings))

    def test_build_rows_fails_closed_when_pool_is_short(self):
        with self.assertRaisesRegex(ValueError, "INSUFFICIENT_FRESH_HOLDOUT"):
            holdout.build_rows([], set(), FakeGenerator, typo_count=1, correct_count=1)


if __name__ == "__main__":
    unittest.main()
