import json
from pathlib import Path
from types import SimpleNamespace
import subprocess
import tempfile
import unittest
from unittest import mock

import android_editing_process_death as subject


def transcript(method, code='0'):
    def event(value):
        return (f'INSTRUMENTATION_STATUS: class={subject.CLASS}\n'
                f'INSTRUMENTATION_STATUS: test={method}\nINSTRUMENTATION_STATUS_CODE: {value}\n')
    return event('1') + event(code) + '\nOK (1 test)\nINSTRUMENTATION_CODE: -1\n'


def crash():
    return (f'INSTRUMENTATION_STATUS: class={subject.CLASS}\n'
            f'INSTRUMENTATION_STATUS: test={subject.PREPARE}\n'
            'INSTRUMENTATION_STATUS_CODE: 1\nINSTRUMENTATION_FAILED: Process crashed.\n')


class EditingDeathRunnerTest(unittest.TestCase):
    def test_proof_and_crash_are_strict(self):
        self.assertEqual(('123', '456'), subject.proof_fields('123\n456\ntrue\n', True))
        for proof in ('123\n123\ntrue\n', '0\n456\ntrue\n', '123\n456\nfalse\n', '123\n456\ntrue\nextra'):
            with self.subTest(proof=proof), self.assertRaisesRegex(ValueError, 'EDITING_DEATH_PROOF'):
                subject.proof_fields(proof, True)
        self.assertTrue(subject.prepare_crashed(crash()))
        for text in ('Process crashed', transcript(subject.PREPARE), crash() + 'OK (1 test)'):
            self.assertFalse(subject.prepare_crashed(text))

    def test_fallback_requires_known_enabled_keyboard(self):
        def adb(args, execute):
            return 'com.google.android.googlequicksearchbox/.Voice\ncom.android.inputmethod.latin/.LatinIME\n'
        with mock.patch.object(subject, 'checked_adb', side_effect=adb):
            self.assertEqual('com.android.inputmethod.latin/.LatinIME', subject.fallback_ime('emulator-1'))
        with mock.patch.object(subject, 'checked_adb', return_value=subject.PACKAGE + '/.ime.Service'):
            with self.assertRaisesRegex(ValueError, 'EDITING_DEATH_NO_FALLBACK_IME'):
                subject.fallback_ime('emulator-1')

    def test_both_phases_require_matching_processes_and_real_recovery(self):
        for failed in (False, True):
            with self.subTest(failed=failed), tempfile.TemporaryDirectory() as folder:
                root = Path(folder).resolve()
                actions = []
                state = {'right': False}
                def adb(args, execute):
                    if args[-2:] == ['getprop', 'ro.build.version.sdk']:
                        return '37'
                    if 'pm' in args:
                        return 'package:/synthetic.apk'
                    if 'pidof' in args:
                        return '456' if args[-1] == subject.EDITOR else '123'
                    if 'kill' in args:
                        self.assertEqual(['run-as', subject.PACKAGE, 'kill', '-9', '123'], args[-5:])
                        actions.append('kill')
                    return ''
                class Running:
                    done = False
                    def poll(self): return 0 if self.done else None
                    def communicate(self, timeout): self.done = True; return crash(), None
                    def terminate(self): self.done = True
                def start(command, **kwargs):
                    state['right'] = command[command.index('runeRightContext') + 1] == 'true'
                    actions.append('prepare')
                    return Running()
                def execute(command, **kwargs):
                    if 'cat' in command:
                        return SimpleNamespace(returncode=0, stdout='123\n456\n' + str(state['right']).lower() + '\n', stderr='')
                    actions.append('recover')
                    return SimpleNamespace(returncode=0, stdout=transcript(subject.RECOVER, '-4' if failed else '0'))
                with mock.patch.object(subject, 'ROOT', root), \
                     mock.patch.object(subject, 'owned_emulator', return_value='emulator-5554'), \
                     mock.patch.object(subject, 'checked_adb', side_effect=adb):
                    code = subject.run(root / 'build/run', 'rune-ci-boundary', execute=execute, start=start)
                receipt = json.loads((root / 'build/run/receipt.json').read_text())
                self.assertEqual(int(failed), code)
                self.assertEqual(not failed, receipt['passed'])
                self.assertEqual(1 if failed else 2, actions.count('kill'))
                self.assertEqual(['prepare', 'kill', 'recover'] * (1 if failed else 2), actions)

    def test_permission_failure_never_kills_process(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            actions = []
            def adb(args, execute):
                if args[-2:] == ['getprop', 'ro.build.version.sdk']: return '37'
                if 'pm' in args: return 'package:/synthetic.apk'
                actions.append(args)
                return ''
            class Running:
                done = False
                def poll(self): return 0 if self.done else None
                def terminate(self): self.done = True
                def communicate(self, timeout): return '', None
            def execute(*args, **kwargs):
                return SimpleNamespace(returncode=1, stdout='', stderr='Permission denied')
            with mock.patch.object(subject, 'ROOT', root), \
                 mock.patch.object(subject, 'owned_emulator', return_value='emulator-5554'), \
                 mock.patch.object(subject, 'checked_adb', side_effect=adb):
                with self.assertRaisesRegex(ValueError, 'EDITING_DEATH_PROOF_READ'):
                    subject.run(root / 'build/run', 'rune-ci-boundary', execute=execute, start=lambda *a, **k: Running())
            self.assertFalse(any('kill' in action for action in actions))

    def test_missing_editor_or_unverified_device_fails_before_instrumentation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            output = root / 'build/run'
            def adb(args, execute):
                if args[-2:] == ['getprop', 'ro.build.version.sdk']: return '37'
                if 'pm' in args: return '' if args[-1] == subject.EDITOR else 'package:/synthetic.apk'
                raise AssertionError('Unexpected command')
            with mock.patch.object(subject, 'ROOT', root), \
                 mock.patch.object(subject, 'owned_emulator', return_value='emulator-5554'), \
                 mock.patch.object(subject, 'checked_adb', side_effect=adb), \
                 mock.patch.object(subject.subprocess, 'Popen') as start:
                with self.assertRaisesRegex(ValueError, 'EDITING_DEATH_FIXTURE_MISSING'):
                    subject.run(output, 'rune-ci-boundary', start=start)
                start.assert_not_called()
                self.assertFalse(output.exists())
            with mock.patch.object(subject, 'ROOT', root), \
                 mock.patch.object(subject, 'owned_emulator', side_effect=ValueError('UNVERIFIED_DEVICE')), \
                 mock.patch.object(subject, 'checked_adb') as adb_calls:
                with self.assertRaisesRegex(ValueError, 'UNVERIFIED_DEVICE'):
                    subject.run(output, 'rune-ci-boundary')
                adb_calls.assert_not_called()
                self.assertFalse(output.exists())

    def test_changed_device_or_pid_never_kills_process(self):
        for change in ('device', 'pid'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as folder:
                root = Path(folder).resolve()
                commands = []
                def adb(args, execute):
                    commands.append(args)
                    if args[-2:] == ['getprop', 'ro.build.version.sdk']: return '37'
                    if 'pm' in args: return 'package:/synthetic.apk'
                    if 'pidof' in args: return '999' if change == 'pid' else '123'
                    return ''
                class Running:
                    done = False
                    def poll(self): return 0 if self.done else None
                    def terminate(self): self.done = True
                    def communicate(self, timeout): return '', None
                def execute(*args, **kwargs):
                    return SimpleNamespace(returncode=0, stdout='123\n456\nfalse\n', stderr='')
                devices = ['emulator-5554', 'emulator-5554',
                           'emulator-5556' if change == 'device' else 'emulator-5554']
                with mock.patch.object(subject, 'ROOT', root), \
                     mock.patch.object(subject, 'owned_emulator', side_effect=devices), \
                     mock.patch.object(subject, 'checked_adb', side_effect=adb):
                    with self.assertRaisesRegex(ValueError, 'EDITING_DEATH_DEVICE_CHANGED' if change == 'device'
                                                else 'EDITING_DEATH_PROCESS_IDENTITY'):
                        subject.run(root / 'build/run', 'rune-ci-boundary', execute=execute, start=lambda *a, **k: Running())
                self.assertFalse(any('kill' in args for args in commands))


if __name__ == '__main__':
    unittest.main()
