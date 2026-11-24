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

    def test_baseline_workspace_uses_the_original_session_context(self):
        (path, expected), = fixtures.sources.ARCHIVED_REPOSITORY_SOURCES
        with fixtures.workspace('baseline') as root:
            self.assertEqual(expected, fixtures.sources.sha(root / path))

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

    def test_word_workspace_restores_real_prior_exclusions_and_refuses_drift(self):
        import prepare_retrieval_test as retrieval
        import prepare_word_ranking as word

        with fixtures.workspace('word') as root, patch.object(retrieval, 'ROOT', root), patch.object(word, 'ROOT', root):
            articles, contexts, texts, hashes, scanned = retrieval.prior_data()
            self.assertEqual((6308, 18000, 1697, 3, 10880),
                             (len(articles), len(contexts), len(texts), len(hashes), scanned))
            data = root / 'build/typing-word-ranking/data/test-rows.jsonl'
            data.write_bytes(data.read_bytes() + b' ')
            with self.assertRaisesRegex(ValueError, 'PRIOR_DATA_IDENTITY'):
                retrieval.prior_data()

    def test_word_observations_projection_is_hash_pinned(self):
        raw = (fixtures.DATA / 'word-observations-projection.json').read_bytes()
        mutant = raw.replace(b'8a5a11', b'8b5a11', 1)
        self.assertNotEqual(raw, mutant)
        original = Path.read_bytes
        with patch.object(Path, 'read_bytes', autospec=True) as read:
            # Limit the substitution to the projection, while the archive verifier
            # continues to use the actual files.
            read.side_effect = lambda path: mutant if path == fixtures.DATA / 'word-observations-projection.json' else original(path)
            with self.assertRaisesRegex(ValueError, 'MODEL_FIXTURE_WORD_OBSERVATIONS_PROJECTION'):
                with fixtures.workspace('word'):
                    pass

    def test_portable_prior_cannot_be_used_for_independent_preparation(self):
        import prepare_retrieval_test as retrieval
        with self.assertRaisesRegex(ValueError, 'PORTABLE_PRIOR_HISTORICAL_ONLY'):
            retrieval.prepare(Path('missing'), Path('missing'), Path('missing'), prior_root=Path('fixture'))

    def test_retrieval_prior_snapshot_binds_all_inputs_and_detects_drift(self):
        import joint_public_sources
        import prepare_retrieval_test as retrieval

        with fixtures.workspace('word') as root:
            snapshot = retrieval.prior_input_snapshot(root)
            self.assertEqual(25, len(snapshot))
            import independent_corpus_guard as guard
            refinement = ('typing-refinement', 'verified-observations')
            epoch = ('typing-extra-epochs', 'observations')
            self.assertEqual(8, len(guard.prior_input_snapshot(root, (refinement,))))
            self.assertEqual(16, len(guard.prior_input_snapshot(root, (refinement, epoch))))
            retrieval.prior_data(root)
            joint_public_sources.verify(snapshot)
            for name in ('build/typing-word-ranking/observations/manifest.json',
                         'build/typing-refinement/data/train-rows.jsonl',
                         'build/typing-extra-epochs/data/test-text.jsonl'):
                path = root / name
                original = path.read_bytes()
                path.write_bytes(original + b' ')
                with self.assertRaisesRegex(ValueError, 'JOINT_PUBLIC_INPUT_DRIFT'):
                    joint_public_sources.verify(snapshot)
                path.write_bytes(original)
            joint_public_sources.verify(snapshot)

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
            self.assertEqual({k: v for k, v in ledger.items() if k != 'entries'},
                             {k: v for k, v in restored.items() if k != 'entries'})
            self.assertEqual({e['id']: e for e in ledger['entries']},
                             {e['id']: e for e in restored['entries']})
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
