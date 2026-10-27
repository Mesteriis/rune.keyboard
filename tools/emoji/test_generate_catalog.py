from __future__ import annotations

import contextlib
import copy
import io
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import generate_catalog as catalog
import fetch_sources


class EmojiCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = catalog.load_manifest()
        cls.sources = catalog.load_sources(cls.manifest)

    def test_archive_rebuild_is_byte_identical(self):
        self.assertEqual(catalog.ARCHIVE.read_bytes(), catalog.make_archive(self.sources))

    def test_complete_catalog_is_deterministic_offline_and_within_budget(self):
        with mock.patch.object(socket, "socket", side_effect=AssertionError("Unexpected network")):
            first = catalog.build()
            self.assertEqual(first, catalog.build())
        metadata = json.loads(first["catalog-manifest.json"])
        self.assertEqual(1898, metadata["entries"])
        self.assertEqual(9, len(metadata["groups"]))
        self.assertEqual(3773, metadata["statusCounts"]["fully-qualified"])
        self.assertEqual(1875, metadata["omittedSkinToneEntries"])
        self.assertLessEqual(len(first["catalog-v1.tsv"]), 320_000)
        rows = [line.split("\t") for line in first["catalog-v1.tsv"].decode().splitlines()[1:]]
        self.assertEqual(9, sum(row[0] == "G" for row in rows))
        emojis = [row for row in rows if row[0] == "E"]
        self.assertEqual(1898, len({row[2] for row in emojis}))
        self.assertTrue(all(len(row) == 6 and all(row[3:]) for row in emojis))
        for language in catalog.LANGUAGES:
            self.assertEqual(1898, sum(metadata["lookupCounts"][language].values()))

    def test_zwj_flags_and_variation_selectors_are_preserved_without_tone_variants(self):
        rows = [line.split("\t") for line in catalog.build()["catalog-v1.tsv"].decode().splitlines() if line.startswith("E\t")]
        by_glyph = {row[2]: row for row in rows}
        for glyph in ("👨‍👩‍👧‍👦", "🇪🇸", "❤️", "👍"):
            self.assertIn(glyph, by_glyph)
        self.assertNotIn("👍🏽", by_glyph)
        self.assertFalse(any(any(0x1F3FB <= ord(char) <= 0x1F3FF for char in glyph) for glyph in by_glyph))
        self.assertEqual(["grinning face", "широко улыбается", "cara sonriendo"], by_glyph["😀"][3:])
        self.assertEqual("flags", by_glyph["🇪🇸"][1])

    def test_changed_archive_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.zip"
            raw = bytearray(catalog.ARCHIVE.read_bytes()); raw[-1] ^= 1; path.write_bytes(raw)
            with self.assertRaisesRegex(catalog.CatalogError, "SOURCE_ARCHIVE_IDENTITY"):
                catalog.load_sources(self.manifest, path)

    def test_unexpected_archive_members_are_rejected_even_with_new_outer_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.zip"
            raw = catalog.make_archive({**self.sources, "extra.txt": b"unexpected"}); path.write_bytes(raw)
            metadata = copy.deepcopy(self.manifest)
            metadata["archive"].update(bytes=len(raw), sha256=catalog.sha(raw))
            with self.assertRaisesRegex(catalog.CatalogError, "ARCHIVE_MEMBER_SET"):
                catalog.load_sources(metadata, path)

    def test_member_hashes_are_checked_separately(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.zip"
            members = dict(self.sources); members["LICENSE.txt"] = b"X" * len(members["LICENSE.txt"])
            raw = catalog.make_archive(members); path.write_bytes(raw)
            metadata = copy.deepcopy(self.manifest); metadata["archive"].update(bytes=len(raw), sha256=catalog.sha(raw))
            with self.assertRaisesRegex(catalog.CatalogError, "ARCHIVE_MEMBER_IDENTITY"):
                catalog.load_sources(metadata, path)

    def test_missing_russian_label_never_falls_back_to_english(self):
        original = catalog.load_names
        def missing(sources, language):
            result = original(sources, language)
            if language == "ru":
                result.pop("😀")
            return result
        with mock.patch.object(catalog, "load_names", side_effect=missing):
            with self.assertRaisesRegex(catalog.CatalogError, "MISSING_NAME_RU"):
                catalog.build()

    def test_cldr_identity_and_conflicting_names_are_rejected(self):
        sources = dict(self.sources)
        document = json.loads(sources["annotations-en.json"])
        document["annotations"]["identity"]["language"] = "ru"
        sources["annotations-en.json"] = catalog.json_bytes(document)
        with self.assertRaisesRegex(catalog.CatalogError, "CLDR_IDENTITY"):
            catalog.load_names(sources, "en")
        sources = dict(self.sources)
        document = json.loads(sources["derived-en.json"])
        document["annotationsDerived"]["annotations"]["😀"] = {"tts": ["conflicting label"]}
        sources["derived-en.json"] = catalog.json_bytes(document)
        with self.assertRaisesRegex(catalog.CatalogError, "CONFLICTING_CLDR_TTS"):
            catalog.load_names(sources, "en")

    def test_duplicate_json_keys_and_control_characters_are_rejected(self):
        with self.assertRaisesRegex(catalog.CatalogError, "DUPLICATE_JSON_KEY"):
            catalog.parse_json(b'{"name":1,"name":2}')
        for name in ("x\ty", "x\ny", "x\u2028y"):
            with self.assertRaisesRegex(catalog.CatalogError, "NAME_CONTROL"):
                catalog.field(name)
        with self.assertRaisesRegex(catalog.CatalogError, "NAME_ENCODING"):
            catalog.field("\ud800")

    def test_emoji_version_and_duplicate_rows_are_rejected(self):
        with self.assertRaisesRegex(catalog.CatalogError, "EMOJI_VERSION"):
            catalog.parse_emojis(self.sources["emoji-test.txt"].replace(b"Version: 15.1", b"Version: 16.0"))
        row = "1F600 ; fully-qualified # 😀 E1.0 grinning face\n"
        with self.assertRaisesRegex(catalog.CatalogError, "DUPLICATE_EMOJI"):
            catalog.parse_emojis(("# Version: 15.1\n# group: Smileys & Emotion\n" + row + row).encode())

    def test_category_order_and_budget_are_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "categories.json"
            document = json.loads(catalog.CATEGORIES.read_bytes()); document["groups"].reverse()
            path.write_bytes(catalog.json_bytes(document))
            with self.assertRaisesRegex(catalog.CatalogError, "CATEGORY_ORDER"):
                catalog.build(categories=path)
        with mock.patch.object(catalog, "MAX_CATALOG_BYTES", 1):
            with self.assertRaisesRegex(catalog.CatalogError, "CATALOG_SIZE_BUDGET"):
                catalog.build()

    def test_failed_validation_does_not_modify_existing_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); bad = root / "bad.zip"; bad.write_bytes(b"bad archive")
            target = root / "output"; target.mkdir(); (target / "catalog-v1.tsv").write_bytes(b"owner bytes")
            args = ["generate_catalog.py", "--source-archive", str(bad), "--output-dir", str(target)]
            with mock.patch.object(sys, "argv", args), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as result:
                    catalog.main()
            self.assertEqual(1, result.exception.code)
            self.assertEqual({"catalog-v1.tsv": b"owner bytes"}, {p.name: p.read_bytes() for p in target.iterdir()})

    def test_clean_relocated_sources_reproduce_without_build_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); tools = root / "tools/emoji"; (tools / "sources").mkdir(parents=True)
            for source in (Path(catalog.__file__), catalog.MANIFEST, catalog.CATEGORIES):
                shutil.copyfile(source, tools / source.name)
            shutil.copyfile(catalog.ARCHIVE, tools / "sources" / catalog.ARCHIVE.name)
            command = [sys.executable, str(tools / "generate_catalog.py")]
            run = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(0, run.returncode, run.stderr)
            self.assertFalse((root / "build").exists())
            output = root / "app/src/main/assets/emoji"
            self.assertEqual(catalog.build(), {p.name: p.read_bytes() for p in output.iterdir()})
            checked = subprocess.run(command + ["--check"], capture_output=True, text=True)
            self.assertEqual(0, checked.returncode, checked.stderr)
            (output / "catalog-v1.tsv").write_bytes(b"changed")
            checked = subprocess.run(command + ["--check"], capture_output=True, text=True)
            self.assertEqual(1, checked.returncode)
            self.assertIn("GENERATED_FILE_MISMATCH", checked.stderr)
            self.assertEqual(b"changed", (output / "catalog-v1.tsv").read_bytes())

    def test_existing_source_archive_is_verified_without_network(self):
        with mock.patch.object(fetch_sources.urllib.request, "urlopen", side_effect=AssertionError("Unexpected network")):
            fetch_sources.fetch_to(catalog.ARCHIVE)

    def test_fetch_refuses_bad_member_without_writing_archive(self):
        class Response:
            def __init__(self, url): self.url = url
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def geturl(self): return self.url
            def read(self, length): return b"bad source"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "restored.zip"
            with mock.patch.object(fetch_sources.urllib.request, "urlopen", side_effect=lambda request, timeout: Response(request.full_url)):
                with self.assertRaisesRegex(catalog.CatalogError, "FETCH_MEMBER_IDENTITY"):
                    fetch_sources.fetch_to(output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
