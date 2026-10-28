from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parent))
from fresh_spelling_holdout import HoldoutSpec, build_rows  # noqa: E402


class FakeGenerator:
    @staticmethod
    def safe_typos(word, _language, _known, _seed):
        return [(word[:-1], "missing_letter")]


class FreshSpellingHoldoutTest(unittest.TestCase):
    def test_spec_and_rows_are_version_and_shard_bound(self):
        spec = HoldoutSpec(9, "0014", "a" * 64, 123, 456)
        pool = [{"word": f"слово{i}", "family": f"слово{i}", "prefix": "Контекст",
                 "selectionHash": f"{i:064x}"} for i in range(6)]
        rows = build_rows(spec, pool, set(), FakeGenerator, typo_count=2, correct_count=2)
        self.assertTrue(all(row["corpusVersion"] == 9 and "-v9-" in row["id"] for row in rows))
        self.assertTrue(all("ru-0014" in row["source"] for row in rows))
        self.assertEqual(len(rows), len({row["family"] for row in rows}))

    def test_invalid_spec_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "HOLDOUT_SPEC"):
            HoldoutSpec(7, "14", "a" * 64, 123, 456)
        with self.assertRaisesRegex(ValueError, "SOURCE_SHA256"):
            HoldoutSpec(9, "0014", "z" * 64, 123, 456)


if __name__ == "__main__":
    unittest.main()
