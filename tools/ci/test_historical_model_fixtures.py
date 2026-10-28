import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import historical_model_fixtures as fixtures


class HistoricalModelFixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta, cls.payloads = fixtures.verify()

    def test_full_original_references_and_data_are_retained(self):
        self.assertEqual(31, len(self.payloads))
        for name, expected in fixtures.MODEL_PINS.items():
            self.assertEqual(expected, fixtures.digest(self.payloads[name]))
            self.assertEqual(expected, self.meta['files'][name]['originalSha256'])
        word = json.loads(self.payloads['build/typing-word-ranking/data/manifest.json'])
        self.assertEqual(9000, sum(x['rows'] for x in word['partitions'].values()))

    def test_mutant_archive_cannot_be_admitted_by_rehashing_outer_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder) / 'data'
            shutil.copytree(fixtures.DATA, data)
            path = data / 'files.tar.gz';raw = path.read_bytes()
            path.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
            meta = json.loads((data / 'manifest.json').read_text())
            meta['archiveSha256'] = fixtures.digest(path.read_bytes())
            (data / 'manifest.json').write_text(json.dumps(meta))
            with self.assertRaisesRegex(ValueError, 'MODEL_FIXTURE_ARCHIVE_IDENTITY'):
                fixtures.read_bundle(data)

    def test_repository_paths_cannot_escape_the_declared_fixture_scope(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder) / 'data'
            shutil.copytree(fixtures.DATA, data)
            path = data / 'manifest.json';meta = json.loads(path.read_text())
            meta['repositoryFiles']['../../outside'] = {'profiles': ['baseline'], 'sha256': '0' * 64}
            path.write_text(json.dumps(meta))
            with self.assertRaisesRegex(ValueError, 'MODEL_FIXTURE_REPOSITORY_SCOPE'):
                fixtures.read_bundle(data)

    def test_refinement_metadata_rebases_every_checked_hash_and_cleans_up(self):
        before = fixtures.sources.sha(fixtures.DATA / 'files.tar.gz')
        with fixtures.workspace('refinement') as root:
            receipt_path = root / 'build/typing-refinement/candidates-v2/receipt.json'
            receipt = json.loads(receipt_path.read_text())
            for name, expected in receipt['files'].items():
                self.assertTrue(Path(name).is_relative_to(root))
                self.assertEqual(expected, fixtures.sources.sha(name))
            for name, expected in receipt['sources'].items():
                if '.external' not in name:
                    self.assertTrue(Path(name).is_relative_to(root))
                    self.assertEqual(expected, fixtures.sources.sha(name))
            binding = json.loads((root / 'build/typing-refinement/verified-observations/manifest.json').read_text())
            self.assertEqual(fixtures.sources.sha(receipt_path), binding['exportReceiptSha256'])
            self.assertEqual(fixtures.sources.sha(binding['dataManifest']), binding['dataManifestSha256'])
            model = root / 'build/typing-refinement/ranker/pairwise.cbm'
            self.assertEqual(fixtures.MODEL_PINS[str(model.relative_to(root))], fixtures.sources.sha(model))
            model.write_bytes(b'isolated mutation')
        self.assertFalse(root.exists())
        self.assertEqual(before, fixtures.sources.sha(fixtures.DATA / 'files.tar.gz'))

    def test_registration_preserves_prior_records_and_updates_only_word_pending_scope(self):
        ledger = fixtures.sources.load_ledger(fixtures.ROOT / 'tools/typing_experiments/holdout-ledger.json')
        base = copy.deepcopy(ledger)
        base['entries'] = [e for e in base['entries'] if e['id'] != fixtures.ENTRY]
        current = 'Original word-ranking text exposure now has permanent article/target-context exclusions; canonical families and full source sentences remain pending.'
        previous = 'Original word-ranking text exposure now has permanent article exclusions; canonical families, target contexts and full source sentences remain pending.'
        base['coverage']['pending'] = [t.replace(current, previous) for t in base['coverage']['pending']]
        with tempfile.TemporaryDirectory() as folder, patch.object(fixtures.sources, 'load_ledger', return_value=base):
            output = Path(folder) / 'ledger.json'
            fixtures.register(output)
            restored = json.loads(output.read_text())
            self.assertEqual(base['entries'], restored['entries'][:-1])
            self.assertEqual(ledger, restored)
            self.assertFalse(restored['coverage']['complete'])
            with self.assertRaises(FileExistsError):
                fixtures.register(output)

    def test_all_target_contexts_are_permanently_disclosed(self):
        from holdout_ledger import assert_disjoint
        ledger = fixtures.sources.load_ledger(fixtures.ROOT / 'tools/typing_experiments/holdout-ledger.json')
        entry = fixtures.context_entry(payloads=self.payloads)
        self.assertEqual(9000, entry['rowCount'])
        self.assertEqual(8991, len(entry['keys']['context']))
        self.assertEqual([fixtures.sources.ENTRY], entry['parentEntries'])
        for part in ('train', 'dev', 'test'):
            row = json.loads(self.payloads['build/typing-word-ranking/data/' + part + '-rows.jsonl'].splitlines()[0])
            row['typed'] = 'changed-typo'
            with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:context'):
                assert_disjoint([row], ledger, kinds=('context',), require_complete=False)
        changed = copy.deepcopy(ledger)
        changed['entries'] = [e for e in changed['entries'] if e['id'] != fixtures.ENTRY]
        with patch.object(fixtures.sources, 'load_ledger', return_value=changed), \
             self.assertRaisesRegex(ValueError, 'MODEL_FIXTURE_CONTEXT_EXCLUSION'):
            fixtures.verify()


if __name__ == '__main__':
    unittest.main()
