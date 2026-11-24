import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

import android_synthetic_restart_suites as subject


class RestartSuitesTest(unittest.TestCase):
    def fake_adb(self, devices='emulator-5554\tdevice', hardware='ranchu', avd='rune-ci-boundary'):
        def execute(command, **kwargs):
            self.assertEqual('adb', command[0])
            if command[1:] == ['devices']:
                out = 'List of devices attached\n' + devices + '\n'
            elif command[-1] == 'ro.kernel.qemu':
                out = '1\n'
            elif command[-1] == 'ro.hardware':
                out = hardware + '\n'
            elif command[-3:] == ['emu', 'avd', 'name']:
                out = avd + '\nOK\n'
            else:
                raise AssertionError(command)
            return SimpleNamespace(returncode=0, stdout=out)
        return execute

    def test_only_named_single_owned_emulator_is_accepted(self):
        self.assertEqual('emulator-5554', subject.owned_emulator('rune-ci-boundary', self.fake_adb()))
        for execute in (self.fake_adb(devices='serial\tdevice'),
                        self.fake_adb(devices='emulator-5554\tdevice\nserial\tdevice'),
                        self.fake_adb(devices='emulator-5554\toffline'),
                        self.fake_adb(hardware='physical'), self.fake_adb(avd='other')):
            with self.subTest(execute=execute), self.assertRaises(ValueError):
                subject.owned_emulator('rune-ci-boundary', execute)
        with self.assertRaisesRegex(ValueError, 'RESTART_AVD_NAME'):
            subject.owned_emulator('personal', self.fake_adb())

    @staticmethod
    def transcript(cls, method, code='0'):
        def event(value):
            return (f'INSTRUMENTATION_STATUS: class={cls}\nINSTRUMENTATION_STATUS: test={method}\n'
                    f'INSTRUMENTATION_STATUS_CODE: {value}\n')
        return event('1') + event(code) + '\nOK (1 test)\nINSTRUMENTATION_CODE: -1\n'

    def test_transcript_requires_exact_pass_not_only_final_code(self):
        text = self.transcript('C', 'm')
        self.assertTrue(subject.verified_instrumentation(text, 'C', 'm'))
        self.assertFalse(subject.verified_instrumentation(text, 'C', 'other'))
        self.assertFalse(subject.verified_instrumentation(self.transcript('C', 'm', '-4'), 'C', 'm'))
        self.assertFalse(subject.verified_instrumentation('INSTRUMENTATION_CODE: -1\n', 'C', 'm'))
        self.assertFalse(subject.verified_instrumentation(text + 'FAILURES!!!\n', 'C', 'm'))

    def test_ordered_runs_restart_only_after_success_and_reject_skip(self):
        for fail_first in (False, True):
            with self.subTest(fail_first=fail_first), tempfile.TemporaryDirectory() as folder:
                root = Path(folder).resolve()
                for name in ('app/build/outputs/apk/debug/app-debug.apk',
                             'app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk'):
                    path = root / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b'synthetic apk')
                real_adb = self.fake_adb()
                calls = []
                def execute(command, **kwargs):
                    if 'force-stop' in command:
                        calls.append(('stop', command[-1]))
                        return SimpleNamespace(returncode=0, stdout='')
                    if 'install' in command or 'ime' in command:
                        return SimpleNamespace(returncode=0, stdout='Success')
                    if 'instrument' not in command:
                        return real_adb(command, **kwargs)
                    self.assertEqual('true', command[command.index('runeCiFailureCapture') + 1])
                    selector = command[command.index('class') + 1]
                    cls, method = selector.split('#')
                    calls.append(('test', method))
                    skip = fail_first and method == subject.PAIRS[0][2]
                    return SimpleNamespace(returncode=0, stdout=self.transcript(cls, method, '-4' if skip else '0'))
                with mock.patch.object(subject, 'ROOT', root):
                    code = subject.run(root / 'build/run', 'rune-ci-boundary', execute)
                receipt = json.loads((root / 'build/run/receipt.json').read_text())
                self.assertEqual(int(fail_first), code)
                self.assertEqual(not fail_first, receipt['passed'])
                self.assertEqual(1 if fail_first else 2, sum(x[0] == 'stop' for x in calls))
                if fail_first:
                    self.assertEqual('PREVIOUS_PHASE_FAILED', receipt['scopes'][1]['reason'])
                    self.assertNotIn(('test', subject.PAIRS[0][3]), calls)


if __name__ == '__main__':
    unittest.main()
