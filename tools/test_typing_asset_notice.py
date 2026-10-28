import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import check_typing_asset_notice as gate


class TypingAssetNoticeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.assets = self.root / gate.ASSETS
        self.assets.mkdir(parents=True)
        self.provenance = self.assets / 'provenance.json'
        self.policy = self.root / gate.POLICY
        self.policy.parent.mkdir(parents=True)
        self.notice = self.assets / 'NOTICE.md'
        entries = []
        data = {'assets': {}}
        for name, action in [('model.bin', 'ignore'), ('table.ctx', 'inventory')]:
            path = self.assets / name
            path.write_bytes(b'\x00public-synthetic-fixture')
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            data['assets'][name] = {'sha256': digest, 'bytes': path.stat().st_size}
            entries.append(dict(path=path.relative_to(self.root).as_posix(), bytes=path.stat().st_size,
                                sha256=digest, action=action,
                                provenance=self.provenance.relative_to(self.root).as_posix()))
        self.provenance.write_text(json.dumps(data))
        for entry in entries:
            entry['provenanceSha256'] = hashlib.sha256(self.provenance.read_bytes()).hexdigest()
        self.policy.write_text(json.dumps(dict(schema=1, sourceCommit='0' * 40,
                                              scannerVersion='2.4.5', entries=entries)))
        self.notice.write_text('<!-- Q2:BinaryNotice:begin -->\n'
                               '| `model.bin` | Public synthetic fixture | `provenance.json` |\n'
                               '| `table.ctx` | Public synthetic fixture | `provenance.json` |\n'
                               '<!-- Q2:BinaryNotice:end -->\n')

    def test_complete_bound_notice(self):
        self.assertEqual([], gate.inspect(self.root))

    def test_missing_row_is_rejected(self):
        self.notice.write_text(self.notice.read_text().replace('| `model.bin`', '| `other.bin`'))
        self.assertIn('NUMERIC_NOTICE_INVENTORY', gate.inspect(self.root))

    def test_duplicate_row_cannot_hide_missing_coverage(self):
        self.notice.write_text(self.notice.read_text().replace('| `table.ctx`', '| `model.bin`'))
        self.assertIn('NUMERIC_NOTICE_INVENTORY', gate.inspect(self.root))

    def test_wrong_declared_provenance_filename_is_rejected(self):
        self.notice.write_text(self.notice.read_text().replace('`provenance.json`', '`unrelated.json`', 1))
        self.assertIn('NUMERIC_NOTICE_PROVENANCE model.bin', gate.inspect(self.root))

    def test_rehashed_provenance_still_must_declare_asset_digest(self):
        self.provenance.write_text('{"assets":{}}')
        data = json.loads(self.policy.read_text())
        for entry in data['entries']:
            entry['provenanceSha256'] = hashlib.sha256(self.provenance.read_bytes()).hexdigest()
        self.policy.write_text(json.dumps(data))
        self.assertIn('NUMERIC_NOTICE_DECLARED_DIGEST model.bin', gate.inspect(self.root))

    def test_unregistered_asset_cannot_inherit_a_notice(self):
        (self.assets / 'other.bin').write_bytes(b'new')
        self.assertIn('UNREADABLE_OR_UNREVIEWED_NUMERIC_NOTICE', gate.inspect(self.root))

    def test_binary_change_cannot_be_only_a_notice_update(self):
        (self.assets / 'model.bin').write_bytes(b'changed')
        self.assertIn('UNREADABLE_OR_UNREVIEWED_NUMERIC_NOTICE', gate.inspect(self.root))

    def test_inventory_data_cannot_be_changed_to_scanignore(self):
        data = json.loads(self.policy.read_text())
        data['entries'][1]['action'] = 'ignore'
        self.policy.write_text(json.dumps(data))
        self.assertIn('UNREADABLE_OR_UNREVIEWED_NUMERIC_NOTICE', gate.inspect(self.root))

    def test_notice_cannot_follow_an_external_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            external = Path(directory) / 'NOTICE.md'
            external.write_text(self.notice.read_text())
            self.notice.unlink()
            self.notice.symlink_to(external)
            self.assertIn('UNREADABLE_OR_UNREVIEWED_NUMERIC_NOTICE', gate.inspect(self.root))


if __name__ == '__main__':
    unittest.main()
