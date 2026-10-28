import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).with_name("export_external_spelling_replay_v8.py")
SPEC = importlib.util.spec_from_file_location("export_external_spelling_replay_v8", SCRIPT)
replay = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(replay)


class ExternalReplayV8Test(unittest.TestCase):
    def test_rejects_wrong_corpus_version(self):
        rows = []
        for cohort, count in (("typo", 1_000), ("correct", 700)):
            for index in range(count):
                row = {"id": f"{cohort}-{index}", "family": f"{cohort}-{index}",
                       "cohort": cohort, "language": "ru", "split": "holdout",
                       "task": "spelling", "corpusVersion": 7}
                if cohort == "typo":
                    row["expectedSpelling"] = "слово"
                rows.append(row)
        with self.assertRaisesRegex(ValueError, "HOLDOUT_SCOPE"):
            replay.validate_rows(rows)


if __name__ == "__main__":
    unittest.main()
