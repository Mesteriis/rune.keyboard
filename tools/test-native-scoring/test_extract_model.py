import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import extract_model


class ModelExtractionTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.archive = self.root / "artifact.zip"
        self.destination = self.root / "model.gguf"
        self.payload = b"synthetic GGUF bytes"
        for name, value in (
            ("MODEL_SIZE", len(self.payload)),
            ("MODEL_SHA256", hashlib.sha256(self.payload).hexdigest()),
        ):
            self.enterContext(patch.object(extract_model, name, value))

    def write_archive(self, entries):
        with zipfile.ZipFile(self.archive, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in entries:
                archive.writestr(name, data)

    def test_nested_verified_inner_file_only(self):
        self.write_archive([
            ("output/" + extract_model.MODEL_NAME, self.payload),
            ("unrelated.txt", b"not extracted"),
        ])
        extract_model.extract_model(self.archive, self.destination)
        self.assertEqual(self.payload, self.destination.read_bytes())
        self.assertEqual({"artifact.zip", "model.gguf"}, {p.name for p in self.root.iterdir()})

    def test_wrong_digest_preserves_existing_destination_and_cleans_temporary(self):
        self.destination.write_bytes(b"previous verified model")
        self.write_archive([(extract_model.MODEL_NAME, b"x" * len(self.payload))])
        with self.assertRaises(ValueError):
            extract_model.extract_model(self.archive, self.destination)
        self.assertEqual(b"previous verified model", self.destination.read_bytes())
        self.assertEqual([], list(self.root.glob(".verified-model-*")))

    def test_missing_ambiguous_wrong_size_and_unsafe_names_fail(self):
        for entries in (
            [("different.gguf", self.payload)],
            [("one/" + extract_model.MODEL_NAME, self.payload),
             ("two/" + extract_model.MODEL_NAME, self.payload)],
            [(extract_model.MODEL_NAME, self.payload + b"extra")],
            [("../" + extract_model.MODEL_NAME, self.payload)],
            [("/" + extract_model.MODEL_NAME, self.payload)],
        ):
            with self.subTest(entries=[name for name, _ in entries]):
                self.write_archive(entries)
                with self.assertRaises(ValueError):
                    extract_model.extract_model(self.archive, self.destination)
                self.assertFalse(self.destination.exists())

    def test_oversized_archive_fails_before_zip_open(self):
        self.archive.write_bytes(b"not a zip")
        with patch.object(extract_model, "MAX_ARCHIVE_SIZE", 1):
            with self.assertRaises(ValueError):
                extract_model.extract_model(self.archive, self.destination)


if __name__ == "__main__":
    unittest.main()
