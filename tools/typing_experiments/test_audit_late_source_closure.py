import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from audit_late_source_closure import audit, references, relative


class LateSourceClosureTest(unittest.TestCase):
    def fixture(self, folder):
        root = Path(folder)
        archive = root / 'archive'
        archive.mkdir()
        payload = b"raise RuntimeError('must never execute archived source')\n"
        sha = hashlib.sha256(payload).hexdigest()
        (archive / 'source.py').write_bytes(payload)
        metadata = dict(sourceHashes={'build/train.py': sha})
        plan = root / 'build/plan.json'
        plan.parent.mkdir()
        plan.write_text(json.dumps(metadata))
        manifest = dict(schema=1, purpose='DECLARED_LATE_TRAINING_SOURCE_BYTES_ONLY',
                        sources={'build/train.py': dict(file='source.py', sha256=sha)},
                        receipts={'build/plan.json': dict(sha256=hashlib.sha256(plan.read_bytes()).hexdigest(),
                                                        sources=metadata['sourceHashes'])})
        (archive / 'manifest.json').write_text(json.dumps(manifest))
        return root, archive, manifest

    def write(self, archive, manifest):
        (archive / 'manifest.json').write_text(json.dumps(manifest))

    def test_all_late_references_survive_without_build_or_model_execution(self):
        result = audit()
        self.assertEqual(56, result['sourcePaths'])
        self.assertFalse(result['scriptsExecuted'])
        self.assertFalse(result['modelExecutionEstablished'])
        self.assertFalse(result['transitiveDependencyCoverageEstablished'])

    def test_source_only_and_historical_modes_do_not_execute_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root, archive, _ = self.fixture(folder)
            self.assertFalse(audit(archive)['historicalReceiptsVerified'])
            self.assertTrue(audit(archive, root)['historicalReceiptsVerified'])
            (archive / 'source.py').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'ARCHIVE_IDENTITY'):
                audit(archive)

    def test_stale_receipt_or_rebound_reference_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            root, archive, manifest = self.fixture(folder)
            (root / 'build/plan.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'RECEIPT_IDENTITY'):
                audit(archive, root)
            manifest['receipts']['build/plan.json']['sha256'] = hashlib.sha256(b'{}').hexdigest()
            self.write(archive, manifest)
            with self.assertRaisesRegex(ValueError, 'EMPTY'):
                audit(archive, root)

    def test_missing_reference_and_unused_archive_entry_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            _, archive, manifest = self.fixture(folder)
            manifest['receipts']['build/plan.json']['sources']['build/train.py'] = 'f' * 64
            self.write(archive, manifest)
            with self.assertRaisesRegex(ValueError, 'REFERENCE'):
                audit(archive)
            manifest['receipts']['build/plan.json']['sources'] = {'build/other.py': manifest['sources']['build/train.py']['sha256']}
            manifest['sources']['build/other.py'] = manifest['sources']['build/train.py']
            self.write(archive, manifest)
            with self.assertRaisesRegex(ValueError, 'UNUSED'):
                audit(archive)

    def test_paths_cannot_escape_archive_or_import_foreign_roots(self):
        for path in ('../x', '/x', 'a/../x', './x', 'a//x', 'a\\x', ''):
            with self.assertRaisesRegex(ValueError, 'PATH'):
                relative(path)
        with tempfile.TemporaryDirectory() as folder:
            root, archive, manifest = self.fixture(folder)
            with self.assertRaisesRegex(ValueError, 'PATH'):
                references(dict(sourceHashes={'/foreign/source.py': 'a' * 64}), root)
            manifest['sources']['build/train.py']['file'] = '../source.py'
            self.write(archive, manifest)
            with self.assertRaisesRegex(ValueError, 'PATH'):
                audit(archive)

    def test_absolute_and_relative_aliases_cannot_silently_replace_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaisesRegex(ValueError, 'DUPLICATE'):
                references(dict(sourceHashes={'build/a.py': 'a' * 64,
                           str(root / 'build/a.py'): 'b' * 64}), root)


if __name__ == '__main__':
    unittest.main()
