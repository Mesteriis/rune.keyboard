#!/usr/bin/env python3
"""Run the real Chrome editor and independent DOM oracle on an owned API 37 AVD."""

import argparse
from contextlib import ExitStack, contextmanager
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import threading

from android_synthetic_restart_suites import checked_adb, owned_emulator

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / 'tools/qa/chrome-editor'
RUNE = 'io.github.mesteriis.rune.keyboard'
CHROME = 'com.android.chrome'
CLASS = RUNE + '.qa.ChromeEditorCompatibilityInstrumentedTest'
METHODS = {'correctionRemainsAvailableAfterFiveWordsAndExactUndo',
           'noSuggestionsPreservesFiveLiteralWordsAndBackspace'}
FLAGS = '/data/local/tmp/chrome-command-line'


def fixture_module(name):
    spec = importlib.util.spec_from_file_location('rune_chrome_' + name, FIXTURE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def numeric_server(path):
    fixture = fixture_module('serve')
    with path.open('x') as receipt, fixture.http.server.HTTPServer(('127.0.0.1', 0),
                                                                   fixture.FixtureHandler) as server:
        server.records = 0
        server.receipt = receipt
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            yield server.server_port
        finally:
            server.shutdown()
            worker.join()


def verify_native_identities(native):
    events = {}
    status = {}
    for line in native.splitlines():
        if line.startswith('INSTRUMENTATION_STATUS: '):
            key, separator, value = line.removeprefix('INSTRUMENTATION_STATUS: ').partition('=')
            if separator:
                status[key] = value
        elif line.startswith('INSTRUMENTATION_STATUS_CODE: '):
            code = line.rsplit(' ', 1)[-1]
            if code == '2' and 'class' not in status and 'test' not in status:
                status = {}
                continue
            if status.get('class') != CLASS or status.get('test') not in METHODS:
                raise ValueError('CHROME_NATIVE_CASE')
            events.setdefault(status['test'], []).append(code)
            status = {}
    if (events != {method: ['1', '0'] for method in METHODS}
            or not re.search(r'^INSTRUMENTATION_CODE: -1$', native, re.MULTILINE)):
        raise ValueError('CHROME_NATIVE_STATUS')


def watch_fold_requests(path, adb, stop, observed):
    stages = iter((('closed', 'fold'), ('opened', 'unfold')))
    prefix = 'INSTRUMENTATION_STATUS: fold_request='
    with path.open() as stream:
        while not stop.is_set():
            offset = stream.tell()
            line = stream.readline()
            if not line.endswith('\n'):
                stream.seek(offset)
                stop.wait(0.1)
            elif line.startswith(prefix):
                posture = line.removeprefix(prefix).strip()
                expected, command = next(stages, (None, None))
                if posture != expected or adb('emu', command) != 'OK':
                    return
                observed.append(posture)


def verify_fold_transition(native, dispatched):
    stages = re.findall(r'^INSTRUMENTATION_STATUS: fold_observed=(.*)$', native, re.M)
    widths = [int(width) for width in re.findall(r'^INSTRUMENTATION_STATUS: fold_width=(\d+)$', native, re.M)]
    before = [int(width) for width in re.findall(r'^INSTRUMENTATION_STATUS: fold_width_before=(\d+)$', native, re.M)]
    if (stages != ['closed', 'opened'] or stages != dispatched or len(widths) != 2 or len(before) != 2
            or not 0 < widths[0] == before[1] < before[0] == widths[1]):
        raise ValueError('CHROME_FOLD_TRANSITIONS')
    return [{'posture': posture, 'widthBefore': start, 'widthAfter': end}
            for posture, start, end in zip(stages, before, widths, strict=True)]


def run(output, avd_name, *, navigation=False, password=False, fold_transitions=False):
    if sum((navigation, password, fold_transitions)) > 1:
        raise ValueError('CHROME_SCENARIO')
    output = Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'):
        raise ValueError('CHROME_OUTPUT')
    serial = owned_emulator(avd_name)

    def adb(*args):
        return checked_adb(['-s', serial, *args])

    if (adb('shell', 'getprop', 'ro.build.version.sdk') != '37'
            or adb('shell', 'getprop', 'ro.build.type') != 'userdebug'):
        raise ValueError('CHROME_REQUIRES_API37_USERDEBUG')
    if fold_transitions:
        device_states = adb('shell', 'cmd', 'device_state', 'print-states')
        if "name='CLOSED'" not in device_states or "name='OPENED'" not in device_states:
            raise ValueError('CHROME_REQUIRES_FOLDABLE_AVD')
    for package in (CHROME, RUNE, RUNE + '.test'):
        if not adb('shell', 'pm', 'path', package).startswith('package:'):
            raise ValueError('CHROME_REQUIRED_PACKAGE:' + package)
    if (adb('shell', 'settings', 'get', 'global', 'debug_app') != 'null'
            or adb('shell', f'if [ -e {FLAGS} ]; then echo present; fi')):
        raise ValueError('CHROME_EXISTING_DEBUG_CONFIGURATION')
    output.mkdir(parents=True, mode=0o700)
    numeric = output / 'dom.jsonl'
    native_log = output / 'native.log'
    verifier = fixture_module('verify')
    if navigation:
        selector, opt_in = f'{verifier.OMNIBOX_CLASS}#{verifier.OMNIBOX_METHOD}', 'q8-omnibox'
    elif password:
        selector, opt_in = f'{verifier.PASSWORD_CLASS}#{verifier.PASSWORD_METHOD}', 'q8-chrome-password'
    else:
        selector, opt_in = CLASS, 'q8-chrome'
    dispatched = []
    with numeric_server(numeric) as port, ExitStack() as cleanup:
        if owned_emulator(avd_name) != serial:
            raise ValueError('CHROME_DEVICE_CHANGED')
        adb('shell', 'am', 'set-debug-app', '--persistent', CHROME)
        cleanup.callback(adb, 'shell', 'am', 'clear-debug-app')
        adb('shell', f"set -C; printf '%s\\n' '_ --disable-fre --no-first-run --no-default-browser-check' > {FLAGS}")
        cleanup.callback(adb, 'shell', 'rm', '--', FLAGS)
        cleanup.callback(adb, 'shell', 'am', 'force-stop', CHROME)
        adb('shell', 'am', 'force-stop', CHROME)
        endpoint = f'tcp:{port}'
        adb('reverse', '--no-rebind', endpoint, endpoint)
        cleanup.callback(adb, 'reverse', '--remove', endpoint)
        command = ['adb', '-s', serial, 'shell', 'am', 'instrument', '--user', '0', '-w', '-r',
                   '-e', 'class', selector, '-e', 'runeOwnedEmulator', opt_in,
                   '-e', 'runeLoopbackPort', str(port), '-e', 'runeFailureArtifacts', 'false']
        if fold_transitions:
            command.extend(['-e', 'runeFoldTransitions', 'true'])
        command.append(RUNE + '.test/androidx.test.runner.AndroidJUnitRunner')
        with native_log.open('x') as log:
            stop = threading.Event()
            watcher = None
            if fold_transitions:
                watcher = threading.Thread(target=watch_fold_requests, args=(native_log, adb, stop, dispatched))
                watcher.start()
            try:
                subprocess.run(command, text=True, stdout=log, stderr=subprocess.STDOUT,
                               check=True, timeout=180)
            except subprocess.TimeoutExpired:
                adb('shell', 'am', 'force-stop', RUNE + '.test')
                raise
            finally:
                if watcher is not None:
                    stop.set()
                    watcher.join()
                    adb('emu', 'unfold')

    if native_log.stat().st_size > 1024 * 1024 or numeric.stat().st_size > 256 * 1024:
        raise ValueError('CHROME_REPORT_SIZE')
    native = native_log.read_text()
    records = [json.loads(line) for line in numeric.read_text().splitlines()]
    if navigation:
        result = verifier.verify_navigation(records, native)
    elif password:
        result = verifier.verify_password(records, native)
    else:
        verify_native_identities(native)
        result = verifier.verify(records, native)
        if fold_transitions:
            result['foldTransitions'] = verify_fold_transition(native, dispatched)
    (output / 'receipt.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--avd-name', required=True)
    scenario = parser.add_mutually_exclusive_group()
    scenario.add_argument('--navigation', action='store_true', help='Run the owned landscape omnibox scenario.')
    scenario.add_argument('--password', action='store_true', help='Run the owned Chrome password scenario.')
    scenario.add_argument('--fold-transitions', action='store_true', help='Run the textarea scenario across two emulator display changes.')
    args = parser.parse_args()
    run(args.output, args.avd_name, navigation=args.navigation, password=args.password,
        fold_transitions=args.fold_transitions)


if __name__ == '__main__':
    main()
