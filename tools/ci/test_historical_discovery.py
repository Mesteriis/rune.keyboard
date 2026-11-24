from pathlib import Path
import subprocess
import unittest
from unittest import mock

import historical_discovery as subject


class HistoricalDiscoveryTest(unittest.TestCase):
    class Original(unittest.TestCase):
        def test_alpha(self):
            pass

        def test_beta(self):
            pass

    def proxy(self, names=('test_alpha', 'test_beta')):
        original = unittest.TestSuite(self.Original(name) for name in names)
        with mock.patch.object(subject.history, 'HELPERS', {'missing-helper': 'x'}), \
             mock.patch.object(Path, 'read_bytes', return_value=b'live'):
            return subject.isolated_suite('test_historical', original)

    def test_real_historical_snapshot_keeps_original_suite(self):
        suite = unittest.TestSuite()
        with mock.patch.object(subject.history, 'HELPERS', {}):
            self.assertIs(suite, subject.isolated_suite('test_historical', suite))

    def test_child_failure_empty_run_and_skip_are_rejected(self):
        suite = self.proxy()
        case = next(iter(suite))
        case.snapshot = Path('/temporary-snapshot')
        for code, output in ((1, 'Ran 1 test\nFAILED'), (0, 'Ran 0 tests\nOK'),
                             (0, 'Ran 1 test in 0s\nOK (skipped=1)')):
            with self.subTest(output=output), mock.patch.object(subject.subprocess, 'run',
                    return_value=subprocess.CompletedProcess([], code, stdout=output)):
                with self.assertRaises(AssertionError):
                    case.run_historical('test_example')
        with mock.patch.object(subject.subprocess, 'run',
                return_value=subprocess.CompletedProcess([], 0, stdout='Ran 1 test in 0s\nOK')):
            case.run_historical('test_example')

    def test_filtered_and_empty_suites_remain_filtered(self):
        selected = list(self.proxy(('test_beta',)))
        self.assertEqual(['test_beta'], [case._testMethodName for case in selected])
        self.assertEqual(0, self.proxy(()).countTestCases())

    def test_duplicate_methods_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'HISTORICAL_DISCOVERY_DUPLICATE_METHOD'):
            self.proxy(('test_alpha', 'test_alpha'))


if __name__ == '__main__':
    unittest.main()
