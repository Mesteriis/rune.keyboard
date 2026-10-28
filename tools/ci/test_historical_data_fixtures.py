import copy
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import historical_data_fixtures as fixtures


class HistoricalDataFixturesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payloads = fixtures.verify()

    def copy_bundle(self, root):
        data = root / 'bundle'
        shutil.copytree(fixtures.DATA, data)
        return data

    def test_original_manifests_and_all_advertised_files_are_retained(self):
        self.assertEqual(15, len(self.payloads))
        for directory, digest in fixtures.PINS.items():
            raw = self.payloads[directory + '/manifest.json']
            self.assertEqual(digest, hashlib.sha256(raw).hexdigest())
        meta = json.loads((fixtures.DATA / 'manifest.json').read_text())
        self.assertEqual(set(self.payloads), set(meta['files']))

    def test_archive_corruption_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            data = self.copy_bundle(Path(folder))
            path = data / 'files.tar.gz'
            path.write_bytes(path.read_bytes()[:-1] + b'X')
            with self.assertRaisesRegex(ValueError, 'HISTORICAL_ARCHIVE_IDENTITY'):
                fixtures.read_bundle(data)

    def test_symlink_archive_member_never_reaches_filesystem(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = self.copy_bundle(root)
            path = data / 'files.tar.gz'
            with tarfile.open(path, 'w:gz') as bundle:
                member = tarfile.TarInfo('../outside')
                member.type = tarfile.SYMTYPE
                member.linkname = str(root / 'outside')
                bundle.addfile(member)
            meta = json.loads((data / 'manifest.json').read_text())
            meta['archiveSha256'] = fixtures.sha(path.read_bytes())
            meta['files']['../outside'] = {'bytes': 0, 'sha256': fixtures.sha(b'')}
            (data / 'manifest.json').write_text(json.dumps(meta))
            with self.assertRaisesRegex(ValueError, 'HISTORICAL_ARCHIVE_MEMBER'):
                fixtures.read_bundle(data)
            self.assertFalse((root / 'outside').exists())

    def test_tampered_data_cannot_be_admitted_by_rehashing_outer_manifest(self):
        payloads = dict(self.payloads)
        name = 'typing-refinement/data/dev-text.jsonl'
        payloads[name] = b'{}\n'
        with self.assertRaisesRegex(ValueError, 'HISTORICAL_DATA_IDENTITY'):
            fixtures.check_payloads(payloads)
        payloads = dict(self.payloads)
        name = 'typing-refinement/data/manifest.json'
        payloads[name] = b'{}\n'
        with self.assertRaisesRegex(ValueError, 'HISTORICAL_MANIFEST_IDENTITY'):
            fixtures.check_payloads(payloads)

    def test_install_refuses_existing_data_and_preserves_unrelated_files(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(fixtures, 'verify', return_value=self.payloads):
            root = Path(folder)
            (root / 'typing-refinement').mkdir()
            sentinel = root / 'typing-refinement/unrelated'
            sentinel.write_text('keep')
            result = fixtures.install(root)
            self.assertEqual(15, result['files'])
            for name, raw in self.payloads.items():
                self.assertEqual(raw, (root / name).read_bytes())
            with self.assertRaisesRegex(ValueError, 'FRESH_HISTORICAL_DATA_REQUIRED'):
                fixtures.install(root)
            self.assertEqual('keep', sentinel.read_text())

    def test_missing_epoch_registration_cannot_pass_as_disclosed_data(self):
        ledger = copy.deepcopy(fixtures.load_ledger(fixtures.LEDGER))
        ledger['entries'] = [e for e in ledger['entries'] if e['id'] != fixtures.ENTRY]
        with patch.object(fixtures, 'load_ledger', return_value=ledger), \
             self.assertRaisesRegex(ValueError, 'HISTORICAL_LEDGER_BINDING'):
            fixtures.verify()

    def test_every_new_epoch_article_and_context_is_permanently_excluded(self):
        from holdout_ledger import assert_disjoint
        ledger = fixtures.validate_ledger(fixtures.load_ledger(fixtures.LEDGER))
        entry = fixtures.epoch_entry(self.payloads)
        self.assertEqual(230, len(entry['keys']['article']))
        self.assertEqual(1500, entry['rowCount'])
        self.assertIn('family', entry['missingAxes'])
        self.assertIn('sentence', entry['missingAxes'])
        original = json.loads(self.payloads['typing-extra-epochs/data/manifest.json'])
        ids = original['partitions']['test']['articles']
        self.assertEqual(set(entry['keys']['article']), fixtures.keys_for([{'article': a} for a in ids], 'article'))
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:article'):
            assert_disjoint([{'article': ids[0]}], ledger, kinds=('article',), require_complete=False)
        row = json.loads(self.payloads['typing-extra-epochs/data/test-rows.jsonl'].splitlines()[0])
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:context'):
            assert_disjoint([row], ledger, kinds=('context',), require_complete=False)


if __name__ == '__main__':
    unittest.main()
