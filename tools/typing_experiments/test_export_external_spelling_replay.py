import base64
import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).with_name("export_external_spelling_replay.py")
SPEC = importlib.util.spec_from_file_location("export_external_spelling_replay", SCRIPT)
replay = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(replay)


def rows():
    result = []
    for cohort, count in (("typo", 1_000), ("correct", 700)):
        for index in range(count):
            row = {"id": f"{cohort}-{index}", "family": f"{cohort}-family-{index}",
                   "cohort": cohort, "language": "ru", "split": "holdout",
                   "task": "spelling", "corpusVersion": 6, "prefix": "Контекст",
                   "typed": f"слово{index}"}
            if cohort == "typo":
                row["expectedSpelling"] = f"слова{index}"
            result.append(row)
    return result


class ExternalReplayTest(unittest.TestCase):
    def test_validation_accepts_exact_frozen_shape(self):
        replay.validate_rows(rows())

    def test_label_free_input_contains_only_six_runtime_fields(self):
        row = rows()[0]
        line = replay.label_free_input_lines([row])[0].rstrip("\n").split("\t")
        self.assertEqual(6, len(line))
        self.assertEqual(row["id"], base64.b64decode(line[1]).decode())
        self.assertEqual(row["prefix"], base64.b64decode(line[4]).decode())
        self.assertEqual(row["typed"], base64.b64decode(line[5]).decode())
        self.assertNotIn(row["expectedSpelling"], "\t".join(line))

    def test_validation_rejects_family_overlap(self):
        values = rows()
        values[-1]["family"] = values[0]["family"]
        with self.assertRaisesRegex(ValueError, "HOLDOUT_FAMILY_DISJOINTNESS"):
            replay.validate_rows(values)


if __name__ == "__main__":
    unittest.main()
