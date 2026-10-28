from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parent))
from fresh_spelling_replay import validate_rows  # noqa: E402


def rows(version: int) -> list[dict]:
    result = []
    for cohort, count in (("typo", 1_000), ("correct", 700)):
        for index in range(count):
            row = {"id": f"{cohort}-{index}", "family": f"{cohort}-{index}",
                   "cohort": cohort, "language": "ru", "split": "holdout",
                   "task": "spelling", "corpusVersion": version}
            if cohort == "typo":
                row["expectedSpelling"] = "слово"
            result.append(row)
    return result


class FreshSpellingReplayTest(unittest.TestCase):
    def test_accepts_exact_version_and_rejects_previous_version(self):
        validate_rows(rows(9), 9)
        with self.assertRaisesRegex(ValueError, "HOLDOUT_SCOPE"):
            validate_rows(rows(8), 9)


if __name__ == "__main__":
    unittest.main()
