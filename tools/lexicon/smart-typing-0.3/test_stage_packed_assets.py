"""Tiny local staging regressions; no dictionary regeneration, Android or network."""
import hashlib
from pathlib import Path
import tempfile
import unittest

from stage_packed_assets import PREFIX, output_root, stage


class AssetStagingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        # Canonicalize only the temporary project root (macOS may use a /var alias).
        self.root = Path(self.temp.name).resolve()
        self.output = self.root / 'build/stage'
        self.source = self.root / 'source'
        self.source.write_bytes(b'RNK1-public-fixture')
        self.entry = {'path': PREFIX + 'smarttyping/lexicon/frequency/en.ranks', 'source': self.source,
                      'bytes': self.source.stat().st_size, 'sha256': hashlib.sha256(self.source.read_bytes()).hexdigest(),
                      'component': 'frequency-CC-BY-SA-4.0', 'compression': 'STORE'}

    def tearDown(self):
        self.temp.cleanup()

    def test_exact_copy_inventory_and_idempotent_rerun(self):
        first = stage([self.entry], self.output)
        manifest = (self.output / 'asset-inventory.json').read_bytes()
        self.assertEqual(self.source.read_bytes(), (self.output / self.entry['path']).read_bytes())
        self.assertEqual(first, stage([self.entry], self.output))
        self.assertEqual(manifest, (self.output / 'asset-inventory.json').read_bytes())
        self.assertNotIn('source', first[0])

    def test_all_input_hashes_checked_before_any_copy(self):
        invalid = dict(self.entry, path=PREFIX + 'smarttyping/lexicon/ru.trie', sha256='0' * 64)
        with self.assertRaisesRegex(ValueError, '^INPUT_HASH$'):
            stage([self.entry, invalid], self.output)
        self.assertFalse(self.output.exists())

    def test_existing_drift_and_unlisted_files_are_never_overwritten(self):
        stage([self.entry], self.output)
        destination = self.output / self.entry['path']
        destination.write_bytes(b'existing-drift')
        with self.assertRaisesRegex(ValueError, '^OUTPUT_DRIFT$'):
            stage([self.entry], self.output)
        self.assertEqual(b'existing-drift', destination.read_bytes())
        destination.write_bytes(self.source.read_bytes())
        extra = self.output / PREFIX / 'unlisted.txt'
        extra.write_text('unlisted')
        with self.assertRaisesRegex(ValueError, '^UNLISTED_ASSET$'):
            stage([self.entry], self.output)
        self.assertEqual('unlisted', extra.read_text())

    def test_inventory_drift_is_rejected_before_any_asset_copy(self):
        self.output.mkdir(parents=True)
        record = self.output / 'asset-inventory.json'
        record.write_text('existing-drift')
        with self.assertRaisesRegex(ValueError, '^INVENTORY_DRIFT$'):
            stage([self.entry], self.output)
        self.assertFalse((self.output / PREFIX).exists())
        self.assertEqual('existing-drift', record.read_text())

    def test_output_scope_traversal_and_symlinks_fail_closed(self):
        self.assertEqual(self.output, output_root(self.output, self.root))
        for invalid in (self.root, self.root / 'build', self.root / 'app', self.root / 'build/../outside'):
            with self.assertRaisesRegex(ValueError, '^OUTPUT_SCOPE$'):
                output_root(invalid, self.root)
        (self.root / 'build').mkdir()
        self.output.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, '^OUTPUT_SYMLINK$'):
            output_root(self.output, self.root)
        with self.assertRaisesRegex(ValueError, '^OUTPUT_SYMLINK$'):
            stage([self.entry], self.output)


if __name__ == '__main__':
    unittest.main()
