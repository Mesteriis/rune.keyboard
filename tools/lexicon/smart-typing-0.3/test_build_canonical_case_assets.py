import tempfile
from pathlib import Path
import unittest

from build_canonical_case_assets import derive, encode


class CanonicalCaseAssetTest(unittest.TestCase):
    def test_derives_unique_title_forms_and_marks_lowercase_ambiguity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "forms.txt"
            source.write_text("A\nLondon\nMadrid\nJuan\njuan\nMay\nMAY\nmay\n", encoding="utf-8")
            self.assertEqual([
                ("juan", "Juan", False),
                ("london", "London", True),
                ("madrid", "Madrid", True),
                ("may", "May", False),
            ], derive(source))

    def test_excludes_single_letter_all_caps_from_title_case(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "forms.txt"
            source.write_text("A\nЯ\n", encoding="utf-8")
            self.assertEqual([], derive(source))

    def test_accepts_unicode_titlecase_initial(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "forms.txt"
            source.write_text("ǅuro\n", encoding="utf-8")
            self.assertEqual([("ǆuro", "ǅuro", True)], derive(source))

    def test_encoding_is_deterministic_and_bounded(self) -> None:
        rows = [("москва", "Москва", True), ("юлия", "Юлия", False)]
        self.assertEqual(encode(rows), encode(rows))
        self.assertTrue(encode(rows).startswith(b"RNC1"))


if __name__ == "__main__":
    unittest.main()
