import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

import collect_android_failure_artifacts as capture


class AndroidFailureCaptureTest(unittest.TestCase):
    def fake_adb(self, state, fail_pull=False):
        def run(command, **kwargs):
            if command[1:] == ['devices']:
                return SimpleNamespace(returncode=0, stdout='List of devices attached\nemulator-5554\tdevice\n')
            if command[-3:] == ['shell', 'getprop', 'ro.kernel.qemu']:
                return SimpleNamespace(returncode=0, stdout='1\n')
            if command[-3:] == ['shell', 'getprop', 'ro.hardware']:
                return SimpleNamespace(returncode=0, stdout='ranchu\n')
            if command[-3:] == ['emu', 'avd', 'name']:
                return SimpleNamespace(returncode=0, stdout='rune-ci-boundary\nOK\n')
            if 'shell' in command and command[-1].startswith('if [ -d'):
                return SimpleNamespace(returncode=0, stdout=state + '\n')
            if 'pull' in command:
                if fail_pull:
                    return SimpleNamespace(returncode=1, stdout='')
                destination = Path(command[-1]); destination.mkdir()
                (destination / 'synthetic.xml').write_text('<synthetic/>')
                return SimpleNamespace(returncode=0, stdout='')
            raise AssertionError('unexpected ADB command')
        return run

    def test_absent_and_present_captures(self):
        for state in ('ABSENT', 'PRESENT'):
            with self.subTest(state=state), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                with mock.patch.object(capture, 'ROOT', root):
                    output = root / 'app/build/ci-device/failure-artifacts'
                    capture.collect(output, 'rune-ci-boundary', self.fake_adb(state))
                    receipt = json.loads((output / 'receipt.json').read_text())
                    self.assertEqual(state, receipt['state'])
                    self.assertEqual(1 if state == 'PRESENT' else 0, receipt['hierarchies'])
                    self.assertEqual(1 if state == 'PRESENT' else 0, receipt['missingScreenshots'])
                    self.assertEqual(state == 'PRESENT', (output / 'captures/synthetic.xml').exists())
                    with self.assertRaisesRegex(ValueError, 'FAILURE_CAPTURE_OUTPUT'):
                        capture.collect(output, 'rune-ci-boundary', self.fake_adb(state))

    def test_pull_failure_never_writes_success_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with mock.patch.object(capture, 'ROOT', root):
                output = root / 'app/build/ci-device/failure-artifacts'
                with self.assertRaisesRegex(ValueError, 'RESTART_ADB_FAILURE'):
                    capture.collect(output, 'rune-ci-boundary', self.fake_adb('PRESENT', fail_pull=True))
                self.assertFalse((output / 'receipt.json').exists())


if __name__ == '__main__':
    unittest.main()
