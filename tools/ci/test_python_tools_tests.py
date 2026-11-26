import json
import contextlib
import io
from pathlib import Path
import subprocess
import tempfile
import unittest

import python_tools_tests as runner


class PythonToolsTestsTest(unittest.TestCase):
    def fixture(self, root, sources):
        subprocess.run(['git', 'init', '-q', str(root)], check=True)
        names = []
        for name, source in sources.items():
            path = root / 'tools/typing_experiments' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source)
            names.append(str(path.relative_to(root)))
        subprocess.run(['git', 'add', 'tools'], cwd=root, check=True)
        manifest = root / 'inventory.json'
        manifest.write_text(json.dumps({'schemaVersion': 1, 'profiles': {
            'stdlib': sorted(names), 'scientific': [], 'historical-artifacts': []}}))
        return manifest

    def test_inventory_matches_every_tracked_module(self):
        data = runner.validate()
        modules = {'test_available_v6_historical_artifacts.py', 'test_recover_available_v6_contexts.py',
                   'test_recover_available_v6_targets.py', 'test_verify_available_v6_observation.py'}
        expected = {'tools/typing_experiments/' + name for name in modules}
        self.assertEqual(expected, set(data['profiles']['historical-artifacts']))
        for profile in ('stdlib', 'scientific'):
            self.assertTrue(expected.isdisjoint(data['profiles'][profile]))
        self.assertTrue(data['profiles']['scientific'])
        self.assertTrue(data['profiles']['stdlib'])

    def test_new_tracked_test_requires_explicit_assignment(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = self.fixture(root, {'test_a.py': ''})
            (root / 'tools/morphology').mkdir()
            (root / 'tools/morphology/test_b.py').write_text('')
            subprocess.run(['git', 'add', 'tools'], cwd=root, check=True)
            with self.assertRaisesRegex(ValueError, 'TEST_INVENTORY_DRIFT'):
                runner.validate(root, manifest)

    def test_duplicate_assignment_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = self.fixture(root, {'test_a.py': ''})
            data = json.loads(manifest.read_text())
            data['profiles']['scientific'] = data['profiles']['stdlib']
            manifest.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'TEST_INVENTORY_DRIFT'):
                runner.validate(root, manifest)

    def test_real_failure_preserves_exit_log_and_continues(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = self.fixture(root, {
                'test_a.py': 'raise RuntimeError("EXPECTED_IMPORT_FAILURE")\n',
                'test_b.py': 'import unittest\nclass Good(unittest.TestCase):\n def test_ok(self): self.assertTrue(True)\n'})
            output = root / 'results'
            self.assertEqual(1, runner.run('stdlib', output, root=root, manifest=manifest))
            result = json.loads((output / 'receipt.json').read_text())
            self.assertEqual('FAIL', result['status'])
            self.assertEqual([1, 0], [r['exitCode'] for r in result['modules']])
            self.assertIn('EXPECTED_IMPORT_FAILURE', next(output.glob('*test_a.py.log')).read_text())
            with self.assertRaises(FileExistsError):
                runner.run('stdlib', output, root=root, manifest=manifest)

    def test_empty_suite_is_never_pass_and_skip_is_disclosed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = self.fixture(root, {
                'test_a.py': '',
                'test_b.py': 'import unittest\nclass Skip(unittest.TestCase):\n @unittest.skip("EXPECTED_SKIP")\n def test_skip(self): pass\n'})
            output = root / 'results'
            self.assertEqual(1, runner.run('stdlib', output, root=root, manifest=manifest))
            receipt = json.loads((output / 'receipt.json').read_text())
            modules = receipt['modules']
            self.assertEqual(1, modules[0]['exitCode'])
            self.assertEqual(0, modules[0]['unittest']['tests'])
            self.assertEqual('EXPECTED_SKIP', modules[1]['unittest']['skipped'][0]['reason'])
            self.assertEqual({'modules':2,'failedModules':1,'timedOutModules':0,'modulesWithoutReceipt':0,
                              'tests':1,'failures':0,'errors':0,'expectedFailures':0,
                              'unexpectedSuccesses':0,'skipped':1}, receipt['totals'])

    def test_empty_profile_is_not_a_successful_run(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = self.fixture(root, {'test_a.py': ''})
            output = root / 'results'
            self.assertEqual(1, runner.run('scientific', output, root=root, manifest=manifest))
            self.assertEqual('FAIL', json.loads((output / 'receipt.json').read_text())['status'])

    def test_success_summary_counts_real_skips(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = self.fixture(root, {'test_a.py': 'import unittest\nclass Cases(unittest.TestCase):\n'
                ' def test_pass(self): pass\n @unittest.skip("EXPECTED_SKIP")\n def test_skip(self): pass\n'})
            output = root / 'results'; printed = io.StringIO()
            with contextlib.redirect_stdout(printed):
                self.assertEqual(0, runner.run('stdlib', output, root=root, manifest=manifest))
            receipt = json.loads((output / 'receipt.json').read_text())
            summary = json.loads(printed.getvalue().splitlines()[-1])
            self.assertEqual('PASS', summary['status'])
            self.assertEqual(2, summary['tests'])
            self.assertEqual(1, summary['skipped'])
            self.assertEqual(receipt['totals']['skipped'], summary['skipped'])

    def test_real_timeout_is_never_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = self.fixture(root, {'test_a.py': 'import time\ntime.sleep(10)\n'})
            output = root / 'results'
            self.assertEqual(1, runner.run('stdlib', output, root=root, manifest=manifest, timeout=.1))
            result = json.loads((output / 'receipt.json').read_text())
            self.assertEqual('FAIL', result['status'])
            self.assertEqual(124, result['modules'][0]['exitCode'])
            self.assertTrue(result['modules'][0]['timedOut'])
            self.assertEqual(1,result['totals']['timedOutModules'])
            self.assertEqual(1,result['totals']['modulesWithoutReceipt'])

    def test_expected_failure_and_unexpected_success_are_accounted_for(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = self.fixture(root, {'test_a.py': 'import unittest\nclass Cases(unittest.TestCase):\n'
                ' @unittest.expectedFailure\n def test_expected(self): self.fail()\n'
                ' @unittest.expectedFailure\n def test_unexpected(self): pass\n'})
            output = root / 'results'
            self.assertEqual(1, runner.run('stdlib', output, root=root, manifest=manifest))
            receipt = json.loads((output / 'receipt.json').read_text())
            self.assertEqual(1, receipt['totals']['expectedFailures'])
            self.assertEqual(1, receipt['totals']['unexpectedSuccesses'])
            self.assertEqual(1, receipt['totals']['failedModules'])
            self.assertEqual('FAIL', receipt['status'])


if __name__ == '__main__':
    unittest.main()
