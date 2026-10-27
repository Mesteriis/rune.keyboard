import copy
import json
from pathlib import Path
import tempfile
import unittest

import fdroid_data_policy as policy


class DataPolicyTest(unittest.TestCase):
    def fixture(self, directory):
        root = Path(directory)
        paths = ['app/src/main/assets/weights.bin', 'app/src/main/assets/context.ctx',
                 'app/src/test/resources/parity/model.bin', 'tools/typing_experiments/baseline/model.bin']
        provenance = root / 'app/src/main/assets/provenance.json'
        provenance.parent.mkdir(parents=True); provenance.write_bytes(b'{"declared":"test-only"}')
        entries = []
        for name in paths:
            path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'data\x00fixture')
            action = 'delete' if name.startswith('tools/') else ('inventory' if path.suffix == '.ctx' else 'ignore')
            entries.append(dict(path=name, bytes=path.stat().st_size, sha256=policy.digest(path), action=action,
                                provenance=provenance.relative_to(root).as_posix(), provenanceSha256=policy.digest(provenance)))
        value = dict(schema=1, sourceCommit='0' * 40, scannerVersion='2.4.5', entries=entries)
        return root, value

    def test_exact_data_and_declared_provenance_produce_literal_suppressions(self):
        with tempfile.TemporaryDirectory() as directory:
            root, value = self.fixture(directory)
            report = policy.check(root, policy.parse_policy(json.dumps(value).encode()))
            self.assertTrue(report['passed']); self.assertEqual(4, report['entries'])
            self.assertEqual(['app/src/main/assets/context.ctx'], report['inventoryOnly'])
            self.assertEqual(2, len(report['scanignore'])); self.assertEqual(1, len(report['scandelete']))

    def test_unknown_numeric_asset_fails_without_expanding_the_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            root, value = self.fixture(directory)
            (root / 'app/src/main/assets/unreviewed.bin').write_bytes(b'new\x00binary')
            with self.assertRaisesRegex(policy.DataPolicyError, 'UNREVIEWED_OR_STALE_DATA_SET'):
                policy.check(root, value)

    def test_filename_and_directory_prefix_collisions_cannot_inherit_an_exception(self):
        for folder in (False, True):
            with tempfile.TemporaryDirectory() as directory:
                root, value = self.fixture(directory)
                extra = root / 'app/src/main/assets/weights.bin.extra.so'
                if folder: extra.mkdir()
                else: extra.write_bytes(b'\x7fELF\x00')
                with self.assertRaisesRegex(policy.DataPolicyError, 'SCANNER_PREFIX_COLLISION'):
                    policy.check(root, value)

    def test_changed_data_or_declared_provenance_hash_refuses(self):
        for provenance in (False, True):
            with tempfile.TemporaryDirectory() as directory:
                root, value = self.fixture(directory)
                field = 'provenance' if provenance else 'path'
                (root / value['entries'][0][field]).write_bytes(b'changed')
                code = 'DECLARED_PROVENANCE_DRIFT' if provenance else 'DATA_BYTES_DRIFT'
                with self.assertRaisesRegex(policy.DataPolicyError, code): policy.check(root, value)

    def test_unused_index_suppression_and_stale_policy_refuse(self):
        with tempfile.TemporaryDirectory() as directory:
            root, value = self.fixture(directory)
            value['entries'][1]['action'] = 'ignore'
            with self.assertRaisesRegex(policy.DataPolicyError, 'SCANNER_ACTION_MISMATCH'): policy.check(root, value)
            value['entries'][1]['action'] = 'inventory'
            (root / value['entries'][0]['path']).unlink()
            with self.assertRaisesRegex(policy.DataPolicyError, 'UNREVIEWED_OR_STALE_DATA_SET'): policy.check(root, value)

    def test_private_or_escaping_provenance_paths_are_not_read(self):
        for name in ('keystore.properties', '../outside.json', 'build/private.json', 'app/src/main/assets/../../../../private.json'):
            with tempfile.TemporaryDirectory() as directory:
                root, value = self.fixture(directory); value['entries'][0]['provenance'] = name
                with self.assertRaises(policy.DataPolicyError): policy.check(root, value)

    def test_duplicate_json_keys_entries_and_symlinks_refuse(self):
        with self.assertRaisesRegex(policy.DataPolicyError, 'DUPLICATE_POLICY_KEY'):
            policy.parse_policy(b'{"schema":1,"schema":1}')
        with tempfile.TemporaryDirectory() as directory:
            root, value = self.fixture(directory); value['entries'].append(copy.deepcopy(value['entries'][0]))
            with self.assertRaisesRegex(policy.DataPolicyError, 'DUPLICATE_DATA_ENTRY'): policy.check(root, value)
            value['entries'].pop()
            path = root / value['entries'][0]['path']; path.unlink(); path.symlink_to(root / value['entries'][1]['path'])
            with self.assertRaisesRegex(policy.DataPolicyError, 'POLICY_FILE_MISSING_OR_UNSAFE'): policy.check(root, value)


if __name__ == '__main__':
    unittest.main()
