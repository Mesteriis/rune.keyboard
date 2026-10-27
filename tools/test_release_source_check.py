import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import release_source_check as source


class ReleaseSourceTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.base = Path(self.directory.name)
        environment = patch.dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
        environment.start(); self.addCleanup(environment.stop)
        self.repo = self.repository(self.base / 'source checkout')

    def git(self, root, *args):
        result = subprocess.run(['git', '-C', str(root), *args], capture_output=True)
        self.assertEqual(0, result.returncode, 'Fixture Git command failed')
        return result.stdout

    def repository(self, root):
        root.mkdir()
        self.git(root, 'init', '-q')
        self.git(root, 'config', 'user.name', 'Source fixture')
        self.git(root, 'config', 'user.email', 'fixture@example.invalid')
        self.git(root, 'config', 'commit.gpgsign', 'false')
        (root / '.gitignore').write_text('build/\nlocal.properties\n')
        (root / 'source.txt').write_text('tracked source\n')
        self.commit(root)
        return root

    def commit(self, root):
        self.git(root, 'add', '--all')
        self.git(root, 'commit', '-q', '-m', 'Synthetic source fixture')

    def submodule(self):
        module = self.repository(self.base / 'module-origin')
        self.git(self.repo, '-c', 'protocol.file.allow=always', 'submodule', 'add', '-q', str(module), 'module')
        self.commit(self.repo)
        return self.repo / 'module'

    def test_clean_committed_source_and_intentionally_ignored_local_outputs_pass(self):
        before = source.check(self.repo)
        self.assertTrue(before['passed']); self.assertEqual(0, before['statusEntries'])
        (self.repo / 'local.properties').write_text('test-only local setting')
        (self.repo / 'build').mkdir(); (self.repo / 'build/artifact').write_bytes(b'generated')
        self.assertEqual(before, source.check(self.repo))

    def test_unstaged_staged_deleted_and_untracked_sources_refuse(self):
        path = self.repo / 'source.txt'
        path.write_text('modified\n'); self.assertFalse(source.check(self.repo)['passed'])
        self.git(self.repo, 'add', 'source.txt'); self.assertFalse(source.check(self.repo)['passed'])
        self.commit(self.repo)
        path.unlink(); self.assertFalse(source.check(self.repo)['passed'])
        self.git(self.repo, 'restore', 'source.txt')
        (self.repo / 'extra.txt').write_text('untracked')
        self.assertEqual('RELEASE_SOURCE_DIRTY', source.check(self.repo)['reason'])
        self.assertIsNone(source.check(self.repo)['submodules'])

    def test_nul_protocol_handles_renames_spaces_and_newlines_as_one_record(self):
        self.git(self.repo, 'mv', 'source.txt', 'new name\nline.txt')
        self.assertEqual(1, source.check(self.repo)['statusEntries'])
        self.assertEqual(1, source.status_count(b'R  new name\nline.txt\x00source.txt\x00'))
        for malformed in (b'?? path', b'R  new\x00', b'bad\x00'):
            with self.assertRaises(source.SourceCheckError): source.status_count(malformed)

    def test_uninitialized_submodule_is_not_a_clean_release_even_if_status_is_empty(self):
        self.submodule()
        self.assertTrue(source.check(self.repo)['passed'])
        self.git(self.repo, 'submodule', 'deinit', 'module')
        self.assertEqual(b'', self.git(self.repo, 'status', '--porcelain=v1'))
        report = source.check(self.repo)
        self.assertFalse(report['passed']); self.assertEqual('RELEASE_SUBMODULE_NOT_READY', report['reason'])

    def test_dirty_submodule_cannot_hide_behind_local_ignore_configuration(self):
        module = self.submodule()
        self.git(self.repo, 'config', 'submodule.module.ignore', 'all')
        (module / 'untracked.txt').write_text('unreviewed')
        self.assertEqual(b'', self.git(self.repo, 'status', '--porcelain=v1'))
        self.assertFalse(source.check(self.repo)['passed'])

    def test_submodule_new_commit_requires_parent_source_commit(self):
        module = self.submodule()
        self.git(module, 'config', 'user.name', 'Source fixture')
        self.git(module, 'config', 'user.email', 'fixture@example.invalid')
        self.git(module, 'config', 'commit.gpgsign', 'false')
        (module / 'source.txt').write_text('different revision\n'); self.commit(module)
        self.assertFalse(source.check(self.repo)['passed'])
        self.commit(self.repo)
        self.assertTrue(source.check(self.repo)['passed'])

    def test_non_git_and_nested_roots_do_not_claim_a_source_identity(self):
        nested = self.repo / 'nested'; nested.mkdir()
        with self.assertRaisesRegex(source.SourceCheckError, 'RELEASE_ROOT_MISMATCH'): source.check(nested)
        missing = self.base / 'not-a-repository'; missing.mkdir()
        with self.assertRaisesRegex(source.SourceCheckError, 'RELEASE_GIT_QUERY_FAILED'): source.check(missing)

    def test_cli_refuses_dirty_source_without_printing_untracked_names(self):
        filename = 'private-test-filename.txt'
        (self.repo / filename).write_text('fixture')
        result = subprocess.run([sys.executable, str(Path(source.__file__)), '--root', str(self.repo)], capture_output=True, text=True)
        self.assertEqual(1, result.returncode)
        self.assertEqual(1, json.loads(result.stdout)['statusEntries'])
        self.assertIn('RELEASE_SOURCE_DIRTY', result.stderr)
        self.assertNotIn(filename, result.stdout + result.stderr)
        self.assertNotIn(str(self.repo), result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
