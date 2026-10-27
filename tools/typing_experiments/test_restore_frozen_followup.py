import hashlib
import json
from pathlib import Path
import unittest
from restore_frozen_followup import restore, V1


class RestoreFollowupTest(unittest.TestCase):
    def test_exact_original_bytes_are_restored_and_compile_without_importing(self):
        directory = Path(__file__).with_name('frozen_sources')
        result = restore((directory/'prepare_joint_followup_b9cc4859e08021f8.py').read_bytes())
        self.assertEqual(V1, hashlib.sha256(result).hexdigest())
        self.assertEqual(result, (directory/'prepare_joint_followup_964b7c6505cf5b3a.py').read_bytes())
        compile(result, 'frozen-followup-v1', 'exec')

    def test_changed_source_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'RESTORE_SOURCE_IDENTITY'):
            restore(b'other code')

    def test_archived_manifest_binds_the_original_path(self):
        directory = Path(__file__).with_name('frozen_sources')
        entry = json.loads((directory/'manifest.json').read_text())['sources'][V1]
        self.assertEqual('tools/typing_experiments/prepare_joint_followup.py', entry['originalPath'])
        self.assertEqual(V1, hashlib.sha256((directory/entry['file']).read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()
