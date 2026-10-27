import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import fdroid_prepared_source as prepared
import release_source_check as source
import test_release_source_check as fixtures


class PreparedSourceTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ReleaseSourceTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.repo = self.fixture.repo
        self.git = self.fixture.git
        self.commit = self.fixture.commit

    def policy(self, module=False):
        if module:
            self.fixture.submodule()
        self.changes = [dict(path='source.txt', action='replace',
            beforeSha256=hashlib.sha256((self.repo / 'source.txt').read_bytes()).hexdigest(),
            afterSha256=hashlib.sha256(b'approved prepared source\n').hexdigest())]
        for name in ['wrapper.jar'] + (['module/source.txt'] if module else []):
            path = self.repo / name
            if not path.exists(): path.write_bytes(b'test wrapper')
            self.changes.append(dict(path=name, action='delete', beforeSha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        (self.repo / 'fdroid').mkdir()
        self.path = self.repo / prepared.POLICY
        self.write_policy()
        self.commit(self.repo)

    def write_policy(self):
        self.path.write_text(json.dumps(dict(schema=1, preparer=prepared.PREPARER, changes=self.changes)))

    def transform(self):
        (self.repo / 'source.txt').write_bytes(b'approved prepared source\n')
        for row in self.changes:
            if row['action'] == 'delete': (self.repo / row['path']).unlink()

    def refuses(self, code):
        with self.assertRaisesRegex(source.SourceCheckError, code): prepared.check_prepared(self.repo)

    def test_exact_preparation_passes_but_default_mode_stays_strict(self):
        self.policy(module=True); self.transform()
        report = prepared.check_prepared(self.repo)
        self.assertTrue(report['passed']); self.assertEqual(3, report['approvedChanges'])
        self.assertEqual(1, report['submodules']); self.assertEqual(prepared.PREPARER, report['preparedSource'])
        self.assertFalse(source.check(self.repo)['passed'])
        (self.repo / 'build').mkdir(); (self.repo / 'build/artifact').write_bytes(b'generated')
        self.assertEqual(report, prepared.check_prepared(self.repo))

    def test_clean_or_partial_preparation_is_not_accepted_as_full_preparation(self):
        self.policy(); self.refuses('REPLACEMENT_HASH')
        (self.repo / 'source.txt').write_bytes(b'approved prepared source\n')
        self.refuses('EXPECTED_DELETE')

    def test_unlisted_staged_unstaged_and_untracked_changes_are_refused(self):
        self.policy(); (self.repo / 'other.txt').write_text('original'); self.commit(self.repo); self.transform()
        (self.repo / 'other.txt').write_text('unreviewed'); self.refuses('SOURCE_DELTA')
        self.git(self.repo, 'add', 'other.txt'); self.refuses('SOURCE_DELTA')
        self.git(self.repo, 'restore', '--staged', 'other.txt'); self.git(self.repo, 'restore', 'other.txt')
        (self.repo / 'untracked.txt').write_text('unreviewed'); self.refuses('SOURCE_DELTA')

    def test_staging_approved_changes_is_not_a_prepared_worktree(self):
        self.policy(); self.transform(); self.git(self.repo, 'add', 'source.txt'); self.refuses('SOURCE_DELTA')

    def test_changed_replacement_and_executable_mode_are_refused(self):
        self.policy(); self.transform()
        (self.repo / 'source.txt').write_text('extra change'); self.refuses('REPLACEMENT_HASH')
        (self.repo / 'source.txt').write_bytes(b'approved prepared source\n')
        (self.repo / 'source.txt').chmod(0o755); self.refuses('FILE_MODE')

    def test_current_policy_must_equal_committed_policy(self):
        self.policy(); self.transform(); self.path.write_text(self.path.read_text() + '\n')
        self.refuses('POLICY_DIRTY')

    def test_policy_hashes_are_checked_against_git_objects(self):
        self.policy(); self.changes[0]['beforeSha256'] = '0' * 64; self.write_policy(); self.commit(self.repo)
        self.transform(); self.refuses('BASE_HASH')

    def test_submodule_additional_dirty_file_and_revision_drift_are_refused(self):
        self.policy(module=True); self.transform(); module = self.repo / 'module'
        (module / 'extra.txt').write_text('unreviewed'); self.refuses('SOURCE_DELTA')
        (module / 'extra.txt').unlink(); self.git(module, 'restore', 'source.txt')
        self.git(module, 'config', 'user.name', 'Fixture'); self.git(module, 'config', 'user.email', 'fixture@example.invalid')
        self.git(module, 'config', 'commit.gpgsign', 'false')
        (module / 'other.txt').write_text('new revision'); self.commit(module)
        (module / 'source.txt').unlink(); self.refuses('SUBMODULE_NOT_READY')

    def test_uninitialized_submodule_is_refused(self):
        self.policy(module=True)
        self.git(self.repo, 'submodule', 'deinit', 'module')
        self.transform_root_only(); self.refuses('SUBMODULE_NOT_READY')

    def transform_root_only(self):
        (self.repo / 'source.txt').write_bytes(b'approved prepared source\n')
        (self.repo / 'wrapper.jar').unlink()

    def test_renamed_paths_are_refused_even_when_prepared_files_match(self):
        self.policy(); (self.repo / 'other.txt').write_text('fixture'); self.commit(self.repo); self.transform()
        self.git(self.repo, 'mv', 'other.txt', 'name with\nnewline.txt'); self.refuses('SOURCE_DELTA')

    def test_symlinks_cannot_replace_policy_or_deleted_file(self):
        self.policy(); self.transform(); (self.repo / 'wrapper.jar').symlink_to('missing')
        self.refuses('SYMLINK'); (self.repo / 'wrapper.jar').unlink()
        raw = self.path.read_bytes(); self.path.unlink(); (self.repo / 'local.properties').write_bytes(raw)
        self.path.symlink_to('../local.properties'); self.refuses('SYMLINK')

    def test_git_index_flags_cannot_hide_additional_source_edits(self):
        for flag in ['--assume-unchanged', '--skip-worktree']:
            with self.subTest(flag=flag):
                if not hasattr(self, 'changes'): self.policy(); self.transform()
                self.git(self.repo, 'update-index', flag, '.gitignore')
                (self.repo / '.gitignore').write_text('unreviewed')
                self.refuses('INDEX_FLAGS')
                self.git(self.repo, 'update-index', '--no-assume-unchanged', '.gitignore')
                self.git(self.repo, 'update-index', '--no-skip-worktree', '.gitignore')
                self.git(self.repo, 'restore', '.gitignore')

    def test_invalid_policy_shape_paths_hashes_and_duplicate_keys_are_refused(self):
        self.policy(); original = json.loads(self.path.read_text())
        cases = [b'{}', b'{"schema":1,"schema":1}', b'[]']
        for key, value in [('path', '.'), ('path', '../outside'), ('path', '/absolute'), ('path', 'source.txt/../outside'),
                           ('path', '.git/config'), ('path', 'source\\name'), ('path', 'name\nline'),
                           ('beforeSha256', 'not-a-hash'), ('action', 'arbitrary')]:
            change = dict(original['changes'][0]); change[key] = value
            cases.append(json.dumps(dict(original, changes=[change])).encode())
        cases.append(json.dumps(dict(original, changes=[original['changes'][0]] * 2)).encode())
        cases.append(json.dumps(dict(original, unknown=True)).encode())
        for raw in cases:
            with self.subTest(raw=raw):
                with self.assertRaises(source.SourceCheckError): prepared.parse_policy(raw)

    def test_io_errors_use_a_fixed_code_without_exposing_the_path(self):
        self.policy(); self.transform()
        with patch.object(Path, 'read_bytes', side_effect=PermissionError('private-test-path')):
            self.refuses('^RELEASE_PREPARED_IO$')

    def test_cli_explicit_mode_and_fixed_failure_do_not_print_local_names(self):
        self.policy(); self.transform()
        command = [sys.executable, str(Path(source.__file__)), '--root', str(self.repo), '--prepared-source', prepared.PREPARER]
        passed = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(0, passed.returncode); self.assertTrue(json.loads(passed.stdout)['passed'])
        name = 'private-test-filename.txt'; (self.repo / name).write_text('fixture')
        failed = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(1, failed.returncode); self.assertIn('RELEASE_PREPARED_SOURCE_DELTA', failed.stderr)
        self.assertNotIn(name, failed.stderr + failed.stdout); self.assertNotIn(str(self.repo), failed.stderr + failed.stdout)


if __name__ == '__main__':
    unittest.main()
