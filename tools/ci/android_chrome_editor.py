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


def run(output, avd_name):
    output = Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'):
        raise ValueError('CHROME_OUTPUT')
    serial = owned_emulator(avd_name)

    def adb(*args):
        return checked_adb(['-s', serial, *args])

    if (adb('shell', 'getprop', 'ro.build.version.sdk') != '37'
            or adb('shell', 'getprop', 'ro.build.type') != 'userdebug'):
        raise ValueError('CHROME_REQUIRES_API37_USERDEBUG')
    for package in (CHROME, RUNE, RUNE + '.test'):
        if not adb('shell', 'pm', 'path', package).startswith('package:'):
            raise ValueError('CHROME_REQUIRED_PACKAGE:' + package)
    if (adb('shell', 'settings', 'get', 'global', 'debug_app') != 'null'
            or adb('shell', f'if [ -e {FLAGS} ]; then echo present; fi')):
        raise ValueError('CHROME_EXISTING_DEBUG_CONFIGURATION')
    output.mkdir(parents=True, mode=0o700)
    numeric = output / 'dom.jsonl'
    native_log = output / 'native.log'
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
                   '-e', 'class', CLASS, '-e', 'runeOwnedEmulator', 'q8-chrome',
                   '-e', 'runeLoopbackPort', str(port), '-e', 'runeFailureArtifacts', 'false',
                   RUNE + '.test/androidx.test.runner.AndroidJUnitRunner']
        with native_log.open('x') as log:
            try:
                subprocess.run(command, text=True, stdout=log, stderr=subprocess.STDOUT,
                               check=True, timeout=180)
            except subprocess.TimeoutExpired:
                adb('shell', 'am', 'force-stop', RUNE + '.test')
                raise

    if native_log.stat().st_size > 1024 * 1024 or numeric.stat().st_size > 256 * 1024:
        raise ValueError('CHROME_REPORT_SIZE')
    native = native_log.read_text()
    verify_native_identities(native)
    records = [json.loads(line) for line in numeric.read_text().splitlines()]
    result = fixture_module('verify').verify(records, native)
    (output / 'receipt.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--avd-name', required=True)
    args = parser.parse_args()
    run(args.output, args.avd_name)


if __name__ == '__main__':
    main()
