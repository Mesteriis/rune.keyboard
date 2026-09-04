import tempfile
from pathlib import Path
import unittest

from build_canonical_case_assets import derive, encode


class CanonicalCaseAssetTest(unittest.TestCase):
    def test_derives_unique_title_forms_and_marks_lowercase_ambiguity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "forms.txt"
            source.write_text("London\nMadrid\nJuan\njuan\nMay\nMAY\nmay\n", encoding="utf-8")
            self.assertEqual([
                ("juan", "Juan", False),
                ("london", "London", True),
                ("madrid", "Madrid", True),
                ("may", "May", False),
            ], derive(source))

    def test_encoding_is_deterministic_and_bounded(self) -> None:
        rows = [("москва", "Москва", True), ("юлия", "Юлия", False)]
        self.assertEqual(encode(rows), encode(rows))
        self.assertTrue(encode(rows).startswith(b"RNC1"))


if __name__ == "__main__":
    unittest.main()
