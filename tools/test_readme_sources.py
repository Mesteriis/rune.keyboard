from pathlib import Path
import subprocess
import tempfile
import unittest

import check_readme_sources as gate


class ReadmeSourcesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        files = {
            'README.md': '[guide](docs/guide.md#section)\n```sh\npython3 tools/run.py\n./gradlew test\n```\n',
            'tools/typing_experiments/README.md': '`bare.py --help`\n`python3 -m unittest test_demo -v`\n',
            'docs/guide.md': '# Section\n', 'tools/run.py': '# fixture\n', 'gradlew': '# fixture\n',
            'tools/typing_experiments/bare.py': '# fixture\n',
            'tools/typing_experiments/test_demo.py': '# fixture\n',
        }
        for name, text in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        subprocess.run(['git', 'add', '.'], cwd=self.root, check=True)

    def inspect(self):
        return gate.inspect(self.root)

    def test_links_scripts_bare_names_and_test_modules_are_indexed(self):
        report = self.inspect()
        self.assertIn('tools/run.py', report['checkedPaths'])
        self.assertIn('tools/typing_experiments/bare.py', report['checkedPaths'])
        self.assertIn('tools/typing_experiments/test_demo.py', report['checkedPaths'])
        self.assertFalse(report['commandsExecuted'])

    def test_existing_untracked_script_is_not_source_closure(self):
        (self.root / 'tools/run.py').rename(self.root / 'tools/new.py')
        (self.root / 'README.md').write_text('`python3 tools/new.py`')
        with self.assertRaisesRegex(ValueError, 'UNTRACKED_OR_MISSING'):
            self.inspect()

    def test_missing_link_target_is_rejected(self):
        (self.root / 'docs/guide.md').unlink()
        with self.assertRaisesRegex(ValueError, 'UNTRACKED_OR_MISSING'):
            self.inspect()

    def test_missing_bare_script_is_rejected(self):
        (self.root / 'tools/typing_experiments/bare.py').unlink()
        with self.assertRaisesRegex(ValueError, 'UNTRACKED_OR_MISSING'):
            self.inspect()

    def test_unknown_unittest_module_is_rejected(self):
        (self.root / gate.DOCUMENTS[1]).write_text('`python3 -m unittest test_missing -v`')
        with self.assertRaisesRegex(ValueError, 'UNTRACKED_OR_MISSING'):
            self.inspect()

    def test_explicit_ignored_build_python_source_is_not_a_generated_data_exemption(self):
        (self.root / 'README.md').write_text('`python3 build/work/prepare.py`')
        with self.assertRaisesRegex(ValueError, 'UNTRACKED_OR_MISSING'):
            self.inspect()

    def test_remote_links_and_generated_command_data_are_separate_scope(self):
        (self.root / 'README.md').write_text('[remote](https://example.invalid/)\n'
            '```sh\npython3 tools/run.py --output build/run/result.json\n```\n')
        self.assertFalse(self.inspect()['generatedDataValidated'])
        self.assertFalse(self.inspect()['remoteLinksVerified'])

    def test_declared_gradle_output_is_recorded_as_generated_not_a_source_pass(self):
        (self.root / 'README.md').write_text('`app/build/reports/result.json`')
        report = self.inspect()
        self.assertEqual(['app/build/reports/result.json'], report['generatedArtifactPaths'])
        self.assertNotIn('app/build/reports/result.json', report['checkedPaths'])

    def test_python_script_in_gradle_output_still_requires_retained_source(self):
        (self.root / 'README.md').write_text('`python3 app/build/prepare.py`')
        with self.assertRaisesRegex(ValueError, 'UNTRACKED_OR_MISSING'):
            self.inspect()

    def test_link_escape_is_rejected(self):
        (self.root / 'README.md').write_text('[outside](../outside.md)')
        with self.assertRaisesRegex(ValueError, 'OUTSIDE_ROOT'):
            self.inspect()

    def test_external_symlink_cannot_satisfy_tracked_path(self):
        with tempfile.TemporaryDirectory() as folder:
            outside = Path(folder) / 'source.py'
            outside.write_text('# fixture')
            (self.root / 'tools/run.py').unlink()
            (self.root / 'tools/run.py').symlink_to(outside)
            with self.assertRaisesRegex(ValueError, 'OUTSIDE_ROOT_OR_SYMLINK'):
                self.inspect()

    def test_untracked_parent_alias_cannot_resolve_to_an_indexed_source(self):
        (self.root / 'docs/link').symlink_to(self.root / 'tools', target_is_directory=True)
        (self.root / 'README.md').write_text('[aliased](docs/link/run.py)')
        with self.assertRaisesRegex(ValueError, 'OUTSIDE_ROOT_OR_SYMLINK'):
            self.inspect()

    def test_readme_itself_cannot_be_an_external_symlink(self):
        with tempfile.TemporaryDirectory() as folder:
            outside = Path(folder) / 'README.md'
            outside.write_text('# fixture')
            (self.root / 'README.md').unlink()
            (self.root / 'README.md').symlink_to(outside)
            with self.assertRaisesRegex(ValueError, 'OUTSIDE_ROOT_OR_SYMLINK'):
                self.inspect()


if __name__ == '__main__':
    unittest.main()
