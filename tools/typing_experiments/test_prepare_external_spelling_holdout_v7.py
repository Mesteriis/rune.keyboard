import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).with_name("prepare_external_spelling_holdout_v7.py")
SPEC = importlib.util.spec_from_file_location("prepare_external_spelling_holdout_v7", SCRIPT)
holdout = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(holdout)


class FakeGenerator:
    @staticmethod
    def safe_typos(word, _language, _known, _seed):
        return [(word[:-1], "missing_letter")]


class ExternalHoldoutV7Test(unittest.TestCase):
    def test_build_rows_uses_new_identity_and_disjoint_families(self):
        pool = [{"word": f"слово{i}", "family": f"слово{i}", "prefix": "Контекст",
                 "selectionHash": f"{i:064x}"} for i in range(6)]
        rows = holdout.build_rows(pool, set(), FakeGenerator, typo_count=2, correct_count=2)
        self.assertTrue(all(row["corpusVersion"] == 7 and "-v7-" in row["id"] for row in rows))
        self.assertEqual(len(rows), len({row["family"] for row in rows}))


if __name__ == "__main__":
    unittest.main()
