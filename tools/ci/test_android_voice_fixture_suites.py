import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

import android_voice_fixture_suites as subject


def transcript(method, code='0'):
    def event(value):
        return (f'INSTRUMENTATION_STATUS: class={subject.CLASS}\n'
                f'INSTRUMENTATION_STATUS: test={method}\nINSTRUMENTATION_STATUS_CODE: {value}\n')
    return event('1') + event(code) + '\nOK (1 test)\nINSTRUMENTATION_CODE: -1\n'


class VoiceFixtureRunnerTest(unittest.TestCase):
    def test_ime_list_rejects_unexpected_output(self):
        with mock.patch.object(subject, 'checked_adb', return_value='bad output'):
            with self.assertRaisesRegex(ValueError, 'VOICE_IME_LIST'):
                subject.ime_list('emulator-5554', False, None)

    def test_scopes_and_cleanup_with_real_result_rules(self):
        system_voice = 'org.example/.VoiceInputMethodService'
        for failure in (False, True):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as folder:
                root = Path(folder).resolve()
                enabled = {subject.RUNE_IME, system_voice}
                selected = [subject.RUNE_IME]
                actions = []
                def adb(args, execute):
                    if 'getprop' in args: return '37'
                    if 'pm' in args: return 'package:/synthetic.apk'
                    if args[-3:] == ['get', 'secure', 'default_input_method']: return selected[0]
                    if 'list' in args:
                        return '\n'.join(sorted(enabled | ({subject.VOICE} if '-a' in args else set())))
                    if 'disable' in args:
                        enabled.discard(args[-1]); actions.append(('disable', args[-1])); return ''
                    if 'enable' in args:
                        enabled.add(args[-1]); actions.append(('enable', args[-1])); return ''
                    if 'set' in args:
                        selected[0] = args[-1]; actions.append(('set', args[-1])); return ''
                    raise AssertionError(args)
                def execute(command, **kwargs):
                    method = command[command.index('class') + 1].split('#')[1]
                    actions.append(('test', method))
                    return SimpleNamespace(returncode=0, stdout=transcript(method, '-4' if failure else '0'))
                with mock.patch.object(subject, 'ROOT', root), \
                     mock.patch.object(subject, 'owned_emulator', return_value='emulator-5554'), \
                     mock.patch.object(subject, 'checked_adb', side_effect=adb):
                    code = subject.run(root / 'build/run', 'rune-ci-boundary', execute)
                receipt = json.loads((root / 'build/run/receipt.json').read_text())
                self.assertEqual(int(failure), code)
                self.assertEqual(not failure, receipt['passed'])
                self.assertEqual({subject.RUNE_IME, system_voice}, enabled)
                self.assertEqual(subject.RUNE_IME, selected[0])
                self.assertEqual(1 if failure else 5, sum(action == 'test' for action, _ in actions))
                self.assertIn(('disable', system_voice), actions)
                self.assertIn(('enable', system_voice), actions)

    def test_unsupported_api_is_rejected_before_any_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            with mock.patch.object(subject, 'ROOT', root), \
                 mock.patch.object(subject, 'owned_emulator', return_value='emulator-5554'), \
                 mock.patch.object(subject, 'checked_adb', return_value='28') as calls:
                with self.assertRaisesRegex(ValueError, 'VOICE_FIXTURE_API'):
                    subject.run(root / 'build/run', 'rune-ci-boundary')
                self.assertEqual(1, calls.call_count)
                self.assertFalse((root / 'build/run').exists())

    def test_missing_fixture_or_unverified_device_never_mutates_ime(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve(); output = root / 'build/run'
            def adb(args, execute):
                if 'getprop' in args: return '26'
                if 'pm' in args: return '' if args[-1] == subject.FIXTURE else 'package:/synthetic.apk'
                raise AssertionError('Unexpected command')
            with mock.patch.object(subject, 'ROOT', root), \
                 mock.patch.object(subject, 'owned_emulator', return_value='emulator-5554'), \
                 mock.patch.object(subject, 'checked_adb', side_effect=adb):
                with self.assertRaisesRegex(ValueError, 'VOICE_FIXTURE_MISSING'):
                    subject.run(output, 'rune-ci-boundary')
                self.assertFalse(output.exists())
            with mock.patch.object(subject, 'ROOT', root), \
                 mock.patch.object(subject, 'owned_emulator', side_effect=ValueError('UNVERIFIED_DEVICE')), \
                 mock.patch.object(subject, 'checked_adb') as calls:
                with self.assertRaisesRegex(ValueError, 'UNVERIFIED_DEVICE'):
                    subject.run(output, 'rune-ci-boundary')
                calls.assert_not_called()
                self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
