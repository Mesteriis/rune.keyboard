import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import backend_test_gate as gate


class Ready(unittest.TestCase):
    def run_case(self):
        pass


class Skipped(unittest.TestCase):
    @unittest.skip('expected skip refusal')
    def run_case(self):
        pass


class Broken(unittest.TestCase):
    def run_case(self):
        self.fail('expected test failure')


class ExpectedFailure(unittest.TestCase):
    @unittest.expectedFailure
    def run_case(self):
        self.fail('expected-failure refusal')


class BackendGateTest(unittest.TestCase):
    def test_success_requires_every_declared_case_to_execute(self):
        test = Ready('run_case')
        passed, result = gate.execute(unittest.TestSuite([test]), {test.id()})
        self.assertTrue(passed);self.assertEqual(1, result['tests'])

    def test_skips_and_actual_failures_are_not_success(self):
        for test in (Skipped('run_case'), Broken('run_case'), ExpectedFailure('run_case')):
            passed, result = gate.execute(unittest.TestSuite([test]), {test.id()})
            self.assertFalse(passed)
            self.assertTrue(result['skipped'] or result['failures'] or result['expectedFailures'])

    def test_missing_or_empty_required_test_suite_is_rejected(self):
        for suite in (unittest.TestSuite(), unittest.TestSuite([Ready('run_case')])):
            with self.assertRaisesRegex(ValueError, 'REQUIRED_BACKEND_TEST_MISSING'):
                gate.execute(suite, {'mandatory.backend.test'})

    def test_wrong_dependency_versions_and_unsupported_platform_are_rejected(self):
        with mock.patch.object(gate.metadata, 'version', return_value='wrong'), \
             self.assertRaisesRegex(ValueError, 'BACKEND_VERSION_MISMATCH'):
            gate.preflight('pymorphy')
        with mock.patch.object(gate.metadata, 'version', side_effect=lambda name: gate.VERSIONS['mlx'][name]), \
             mock.patch.object(gate.sys, 'platform', 'linux'), \
             self.assertRaisesRegex(ValueError, 'MLX_MACOS_ARM64_REQUIRED'):
            gate.preflight('mlx')

    def test_changed_inputs_cannot_pass_after_successful_test_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'result'
            test = Ready('run_case')
            with mock.patch.object(gate, 'preflight', return_value=gate.VERSIONS['mlx']), \
                 mock.patch.object(gate, 'load_suite', return_value=unittest.TestSuite([test])), \
                 mock.patch.dict(gate.REQUIRED, {'mlx': {test.id()}}), \
                 mock.patch.object(gate, 'input_bindings', side_effect=[{'input': 'before'}, {'input': 'after'}]):
                self.assertEqual(1, gate.run('mlx', output))
            receipt = json.loads((output / 'receipt.json').read_text())
            self.assertEqual('FAIL', receipt['status'])
            self.assertEqual(1, receipt['unittest']['tests'])
            self.assertIn('BACKEND_INPUT_CHANGED', (output / 'tests.log').read_text())

    def test_missing_backend_writes_failure_receipt_without_claiming_tests(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'result'
            with mock.patch.object(gate, 'preflight', side_effect=ImportError('expected missing backend')):
                self.assertEqual(1, gate.run('mlx', output))
            result = json.loads((output / 'receipt.json').read_text())
            self.assertEqual('FAIL', result['status']);self.assertIsNone(result['unittest'])
            self.assertEqual('ImportError', result['errorType'])
            with self.assertRaises(FileExistsError):
                gate.run('mlx', output)


if __name__ == '__main__':
    unittest.main()
