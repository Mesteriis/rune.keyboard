import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import check_packaged_provenance_paths as gate


class PackagedProvenancePathsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tracked = set()
        self.script = gate.SCRIPTS + 'train.py'
        self.policy = gate.SCRIPTS + 'policy.json'
        self.provenance = gate.ASSETS + '/experiments/provenance.json'
        self.write(self.script, b'# public synthetic training source\n')
        self.write(self.policy, b'{"synthetic":true}\n')
        self.data = {
            'sourceRepository': 'wikimedia/wikipedia',
            'sourcePath': '20231101.ru/train/0007.parquet',
            'trainingScripts': {'train.py': self.sha(self.script)},
            'automaticQualification': {'policyPath': self.policy,
                                       'policySha256': self.sha(self.policy)},
        }
        self.save()

    def write(self, name, raw):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        self.tracked.add(name)

    def sha(self, name):
        return hashlib.sha256((self.root / name).read_bytes()).hexdigest()

    def save(self):
        self.write(self.provenance, json.dumps(self.data).encode())

    def inspect(self):
        return gate.inspect(self.root, self.tracked)

    def test_current_and_dataset_relative_reference(self):
        result = self.inspect()
        self.assertEqual([self.policy], result['provenanceFiles'][0]['repositoryPaths'])
        self.assertFalse(result['modelExecutionEstablished'])
        self.assertFalse(result['transitiveDependencyCoverageEstablished'])

    def test_existing_untracked_policy_is_rejected(self):
        self.tracked.remove(self.policy)
        with self.assertRaisesRegex(ValueError, 'UNTRACKED_OR_UNSAFE_PATH'):
            self.inspect()

    def test_untracked_provenance_is_rejected(self):
        self.tracked.remove(self.provenance)
        with self.assertRaisesRegex(ValueError, 'UNTRACKED_OR_UNSAFE_PATH'):
            self.inspect()

    def test_missing_tracked_provenance_is_not_silently_skipped(self):
        (self.root / self.provenance).unlink()
        with self.assertRaises(FileNotFoundError):
            self.inspect()

    def test_new_untracked_provenance_is_not_silently_skipped(self):
        path = self.root / gate.ASSETS / 'new-provenance.json'
        path.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'UNTRACKED_OR_UNSAFE_PATH'):
            self.inspect()

    def test_changed_policy_is_rejected(self):
        self.write(self.policy, b'{"changed":true}')
        with self.assertRaisesRegex(ValueError, 'AUTOMATIC_POLICY_IDENTITY'):
            self.inspect()

    def test_changed_training_source_is_rejected(self):
        self.write(self.script, b'# changed')
        with self.assertRaisesRegex(ValueError, 'TRAINING_SCRIPT_IDENTITY'):
            self.inspect()

    def test_traversal_in_explicit_reference_is_rejected(self):
        self.data['description'] = 'tools/../outside.py'
        self.save()
        with self.assertRaisesRegex(ValueError, 'UNTRACKED_OR_UNSAFE_PATH'):
            self.inspect()

    def test_external_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            outside = Path(directory) / 'policy.json'
            outside.write_bytes((self.root / self.policy).read_bytes())
            (self.root / self.policy).unlink()
            (self.root / self.policy).symlink_to(outside)
            with self.assertRaisesRegex(ValueError, 'UNSAFE_PATH'):
                self.inspect()

    def test_exact_historical_archive_resolves_changed_current_test(self):
        (script, digest), archive = next(iter(gate.HISTORICAL.items()))
        # The real immutable historical bytes are source identity, not an executed fixture.
        self.write(archive, (gate.ROOT / archive).read_bytes())
        self.write(gate.SCRIPTS + script, b'# portable current test')
        self.data['trainingScripts'] = {script: digest}
        self.save()
        result = self.inspect()['provenanceFiles'][0]['trainingScripts'][0]
        self.assertEqual(archive, result['resolved'])
        self.write(archive, b'# tampered historical source')
        with self.assertRaisesRegex(ValueError, 'HISTORICAL_SCRIPT_IDENTITY'):
            self.inspect()


if __name__ == '__main__':
    unittest.main()
