"""Run historically bound tests in a source snapshot during normal discovery."""
import hashlib
import os
import subprocess
import sys
import unittest

import check_text_boundary_history as history


def isolated_suite(module, original_suite):
    # The dedicated historical runner already supplies the exact helper bytes.
    if all(hashlib.sha256((history.ROOT / path).read_bytes()).hexdigest() == digest
           for path, digest in history.HELPERS.items()):
        return original_suite

    class HistoricalTests(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.snapshot_context = history.historical_snapshot(history.ROOT)
            cls.snapshot = cls.snapshot_context.__enter__()
            cls.addClassCleanup(cls.snapshot_context.__exit__, None, None, None)

        def run_historical(self, method):
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
            env.pop('PYTHONPATH', None)
            result = subprocess.run(
                [sys.executable, '-B', '-m', 'unittest', 'discover', '-s',
                 str(self.snapshot / 'tools/ci'), '-p', module + '.py', '-k', method, '-v'],
                cwd=self.snapshot, env=env, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True)
            self.assertEqual(0, result.returncode, result.stdout)
            self.assertIn('Ran 1 test ', result.stdout)
            self.assertNotIn('skipped=', result.stdout)

    def methods(suite):
        for item in suite:
            if isinstance(item, unittest.TestSuite):
                yield from methods(item)
            else:
                yield item._testMethodName

    names = list(methods(original_suite))
    if len(names) != len(set(names)):
        raise ValueError('HISTORICAL_DISCOVERY_DUPLICATE_METHOD')
    for name in names:
        def run(self, method=name):
            self.run_historical(method)
        setattr(HistoricalTests, name, run)
    return unittest.defaultTestLoader.loadTestsFromTestCase(HistoricalTests)
