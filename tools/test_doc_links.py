from pathlib import Path
import subprocess
import tempfile
import unittest

import check_doc_links as gate


class DocLinksTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        for name, text in {'README.md': '[a](docs/a.md)\n', 'docs/a.md': '[b](b.md)\n',
                           'docs/b.md': '# B\n', 'image.png': 'fixture'}.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        subprocess.run(['git', 'add', '.'], cwd=self.root, check=True)

    def inspect(self, **kwargs):
        return gate.inspect(self.root, documents=('README.md',), **kwargs)

    def test_follows_transitive_links_and_stops_cycles(self):
        (self.root / 'docs/b.md').write_text('[cycle](a.md#heading)\n')
        result = self.inspect()
        self.assertEqual({'README.md', 'docs/a.md', 'docs/b.md'}, set(result['documents']))
        self.assertFalse(result['commandsExecuted'])
        self.assertFalse(result['anchorsVerified'])

    def test_missing_transitive_target_is_rejected(self):
        (self.root / 'docs/b.md').unlink()
        with self.assertRaisesRegex(ValueError, 'DOC_LINK_MISSING'):
            self.inspect()

    def test_existing_untracked_target_is_rejected(self):
        (self.root / 'docs/new.md').write_text('# new')
        (self.root / 'docs/a.md').write_text('[new](new.md)')
        with self.assertRaisesRegex(ValueError, 'DOC_LINK_UNTRACKED'):
            self.inspect()

    def test_fenced_examples_and_remote_links_are_not_local_navigation(self):
        (self.root / 'docs/a.md').write_text('```md\n[example](missing.md)\n```\n'
                                           '[remote](https://example.invalid/)\n')
        self.assertFalse(self.inspect()['remoteLinksVerified'])

    def test_graph_limit_cannot_be_a_truncated_pass(self):
        with self.assertRaisesRegex(ValueError, 'DOC_LINK_GRAPH_BOUND'):
            self.inspect(maximum_documents=1)

    def test_parent_symlink_cannot_satisfy_a_navigation_target(self):
        (self.root / 'docs/alias').symlink_to(self.root / 'docs', target_is_directory=True)
        (self.root / 'README.md').write_text('[alias](docs/alias/b.md)')
        with self.assertRaisesRegex(ValueError, 'OUTSIDE_ROOT_OR_SYMLINK'):
            self.inspect()

    def submodule(self):
        repo = self.root / 'vendor/native'
        repo.mkdir(parents=True)
        subprocess.run(['git', 'init', '-q', str(repo)], check=True)
        (repo / 'LICENSE').write_text('public fixture license\n')
        subprocess.run(['git', 'add', '.'], cwd=repo, check=True)
        self.commit(repo)
        pin = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo).decode().strip()
        subprocess.run(['git', 'update-index', '--add', '--cacheinfo', '160000', pin,
                        'vendor/native'], cwd=self.root, check=True)
        (self.root / 'README.md').write_text('[license](vendor/native/LICENSE)')
        return repo, pin

    @staticmethod
    def commit(repo):
        subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                        '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null',
                        'commit', '-qm', 'fixture'], cwd=repo, check=True)

    def test_submodule_file_is_verified_at_exact_parent_gitlink_pin(self):
        _, pin = self.submodule()
        result = self.inspect()
        self.assertEqual(pin, result['pinnedSubmoduleFiles']['vendor/native/LICENSE']['commit'])

    def test_submodule_working_file_drift_is_rejected(self):
        repo, _ = self.submodule()
        (repo / 'LICENSE').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'DOC_SUBMODULE_FILE_DRIFT'):
            self.inspect()

    def test_submodule_head_drift_is_rejected_even_if_license_matches(self):
        repo, _ = self.submodule()
        (repo / 'other').write_text('new')
        subprocess.run(['git', 'add', 'other'], cwd=repo, check=True)
        self.commit(repo)
        with self.assertRaisesRegex(ValueError, 'DOC_SUBMODULE_HEAD_DRIFT'):
            self.inspect()


if __name__ == '__main__':
    unittest.main()
