from contextlib import contextmanager
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import android_chrome_editor as chrome
from android_chrome_editor import CLASS, METHODS, verify_native_identities


def native_output():
    return ''.join(
        f'INSTRUMENTATION_STATUS: class={CLASS}\n'
        f'INSTRUMENTATION_STATUS: test={method}\n'
        f'INSTRUMENTATION_STATUS_CODE: {status}\n'
        for method in sorted(METHODS) for status in (1, 0)
    ) + 'INSTRUMENTATION_CODE: -1\n'


class ChromeRouteTest(unittest.TestCase):
    def test_fold_watch_only_dispatches_the_expected_next_console_command(self):
        for requested, expected in ((('closed', 'opened'), ['fold', 'unfold']),
                                    (('opened',), [])):
            with self.subTest(requested=requested), tempfile.TemporaryDirectory() as directory:
                log = Path(directory) / 'native.log'
                log.write_text(''.join(f'INSTRUMENTATION_STATUS: fold_request={stage}\n' for stage in requested))
                sent, recorded = [], []
                stop = threading.Event()

                def adb(*args):
                    self.assertEqual('emu', args[0])
                    sent.append(args[1])
                    if args[1] == 'unfold':
                        stop.set()
                    return 'OK'

                chrome.watch_fold_requests(log, adb, stop, recorded)
                self.assertEqual(expected, sent)
                self.assertEqual(list(requested) if expected else [], recorded)

    def test_fold_requires_both_observed_width_changes_in_order(self):
        closed = ('INSTRUMENTATION_STATUS: fold_observed=closed\n'
                  'INSTRUMENTATION_STATUS: fold_width_before=2208\n'
                  'INSTRUMENTATION_STATUS: fold_width=1080\n')
        opened = ('INSTRUMENTATION_STATUS: fold_observed=opened\n'
                  'INSTRUMENTATION_STATUS: fold_width_before=1080\n'
                  'INSTRUMENTATION_STATUS: fold_width=2208\n')
        dispatched = ['closed', 'opened']
        self.assertEqual([1080, 2208], [row['widthAfter'] for row in
                                         chrome.verify_fold_transition(closed + opened, dispatched)])
        for native, commands in ((opened + closed, dispatched), (closed, dispatched),
                                 (closed + opened, ['closed']),
                                 ((closed + opened).replace('fold_width=1080', 'fold_width=2208'), dispatched)):
            with self.subTest(native=native, commands=commands), self.assertRaisesRegex(ValueError, 'CHROME_FOLD_TRANSITIONS'):
                chrome.verify_fold_transition(native, commands)

    def test_navigation_route_uses_the_owned_case_and_requires_dom_evidence(self):
        verifier = chrome.fixture_module('verify')
        native = ''.join(f'INSTRUMENTATION_STATUS: class={verifier.OMNIBOX_CLASS}\n'
                         f'INSTRUMENTATION_STATUS: test={verifier.OMNIBOX_METHOD}\n'
                         f'INSTRUMENTATION_STATUS_CODE: {status}\n' for status in (1, 0))
        native += 'OK (1 test)\nINSTRUMENTATION_CODE: -1\n'
        for destination in (True, False):
            with self.subTest(destination=destination), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                output = root / 'build/omnibox'
                calls = []

                def adb(args):
                    calls.append(tuple(args))
                    if args[-1] == 'ro.build.version.sdk':
                        return '37'
                    if args[-1] == 'ro.build.type':
                        return 'userdebug'
                    if args[-1] == 'debug_app':
                        return 'null'
                    return 'package:/fixture.apk' if args[3:5] == ['pm', 'path'] else ''

                @contextmanager
                def numeric_server(path):
                    profiles = ('ordinary', 'no-suggestions') if destination else ('ordinary',)
                    path.write_text(''.join(json.dumps({'profile': profile, **dict.fromkeys(
                        verifier.FIELDS - {'profile'}, 0)}) + '\n' for profile in profiles))
                    yield 43123

                def instrument(command, **arguments):
                    self.assertIn('q8-omnibox', command)
                    self.assertIn(verifier.OMNIBOX_CLASS + '#' + verifier.OMNIBOX_METHOD, command)
                    arguments['stdout'].write(native)

                with patch.multiple(chrome, ROOT=root, owned_emulator=lambda _: 'emulator-5588',
                                    checked_adb=adb, numeric_server=numeric_server), \
                        patch.object(chrome.subprocess, 'run', side_effect=instrument):
                    if destination:
                        chrome.run(output, 'rune-ci-boundary', navigation=True)
                        self.assertTrue(json.loads((output / 'receipt.json').read_text())['passed'])
                    else:
                        with self.assertRaisesRegex(ValueError, 'DOM_NAVIGATION_NOT_OBSERVED'):
                            chrome.run(output, 'rune-ci-boundary', navigation=True)
                        self.assertFalse((output / 'receipt.json').exists())
                self.assertIn(('-s', 'emulator-5588', 'reverse', '--remove', 'tcp:43123'), calls)
                self.assertIn(('-s', 'emulator-5588', 'shell', 'am', 'clear-debug-app'), calls)

    def test_allows_numeric_progress_between_case_events(self):
        native = native_output().replace(
            'INSTRUMENTATION_STATUS_CODE: 1\n',
            'INSTRUMENTATION_STATUS_CODE: 1\n'
            'INSTRUMENTATION_STATUS: word=1\nINSTRUMENTATION_STATUS_CODE: 2\n',
        )
        verify_native_identities(native)

    def test_requires_both_exact_cases_to_start_and_pass(self):
        verify_native_identities(native_output())
        for text in (
            native_output().replace('INSTRUMENTATION_CODE: -1\n', ''),
            native_output().replace(CLASS, 'some.other.Test'),
            native_output().replace(sorted(METHODS)[0], sorted(METHODS)[1]),
            native_output().replace('INSTRUMENTATION_STATUS_CODE: 0', 'INSTRUMENTATION_STATUS_CODE: -3'),
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                verify_native_identities(text)
