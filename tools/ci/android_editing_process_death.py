#!/usr/bin/env python3
"""Exercise Rune process death with an independent synthetic Compose editor."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import time

from android_synthetic_restart_suites import checked_adb, owned_emulator, verified_instrumentation

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = 'io.github.mesteriis.rune.keyboard'
EDITOR = 'io.github.mesteriis.rune.qa.compose'
CLASS = PACKAGE + '.qa.EditingProcessDeathInstrumentedTest'
PREPARE = 'prepareForeignTextForHostKill'
RECOVER = 'recreatedProcessKeepsForeignSuffixIsolated'
PROOF = 'cache/editing-process-death-proof'


def proof_fields(text, right):
    match = re.fullmatch(r'([1-9][0-9]*)\n([1-9][0-9]*)\n(true|false)\s*', text)
    if not match or (match.group(3) == 'true') != right or match.group(1) == match.group(2):
        raise ValueError('EDITING_DEATH_PROOF')
    return match.group(1), match.group(2)


def prepare_crashed(text):
    return (f'INSTRUMENTATION_STATUS: class={CLASS}' in text and
            f'INSTRUMENTATION_STATUS: test={PREPARE}' in text and
            'INSTRUMENTATION_STATUS_CODE: 1' in text and
            'Process crashed' in text and 'OK (1 test)' not in text)


def fallback_ime(serial, execute=subprocess.run):
    entries = checked_adb(['-s', serial, 'shell', 'ime', 'list', '-s'], execute).splitlines()
    candidates = sorted(x.strip() for x in entries if x.strip().startswith(
        ('com.android.inputmethod.latin/', 'com.google.android.inputmethod.latin/'))
        and re.fullmatch(r'[A-Za-z0-9_.]+/[A-Za-z0-9_.$]+', x.strip()))
    if not candidates:
        raise ValueError('EDITING_DEATH_NO_FALLBACK_IME')
    return candidates[0]


def run(output, avd_name, execute=subprocess.run, start=subprocess.Popen,
        monotonic=time.monotonic, sleep=time.sleep):
    output = Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'):
        raise ValueError('EDITING_DEATH_OUTPUT')
    serial = owned_emulator(avd_name, execute)
    api = checked_adb(['-s', serial, 'shell', 'getprop', 'ro.build.version.sdk'], execute)
    if api not in ('26', '37'):
        raise ValueError('EDITING_DEATH_API')
    for package in (PACKAGE, PACKAGE + '.test', EDITOR):
        if not checked_adb(['-s', serial, 'shell', 'pm', 'path', package], execute).startswith('package:'):
            raise ValueError('EDITING_DEATH_FIXTURE_MISSING')
    fallback = fallback_ime(serial, execute) if api == '26' else None
    output.mkdir(parents=True, mode=0o700)
    results = []
    for right in (False, True):
        scope = 'right' if right else 'left'
        if owned_emulator(avd_name, execute) != serial:
            raise ValueError('EDITING_DEATH_DEVICE_CHANGED')
        checked_adb(['-s', serial, 'shell', 'run-as', PACKAGE, 'rm', '-f', PROOF], execute)
        args = ['-e', 'runeEditingDeathFixture', 'true', '-e', 'runeRightContext', str(right).lower(),
                '-e', 'runeCiFailureCapture', 'true']
        if fallback:
            args += ['-e', 'runeRecoveryFallbackIme', fallback]
        command = ['adb', '-s', serial, 'shell', 'am', 'instrument', '-w', '-r', *args,
                   '-e', 'class', CLASS + '#' + PREPARE, PACKAGE + '.test/androidx.test.runner.AndroidJUnitRunner']
        process = start(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            deadline = monotonic() + 180
            while True:
                probe = execute(['adb', '-s', serial, 'shell', 'run-as', PACKAGE, 'cat', PROOF],
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if probe.returncode == 0:
                    old_pid, editor_pid = proof_fields(probe.stdout, right)
                    break
                if 'No such file or directory' not in probe.stderr and 'No such file or directory' not in probe.stdout:
                    raise ValueError('EDITING_DEATH_PROOF_READ')
                if process.poll() is not None or monotonic() >= deadline:
                    raise ValueError('EDITING_DEATH_PREPARE_TIMEOUT')
                sleep(0.25)
            if owned_emulator(avd_name, execute) != serial:
                raise ValueError('EDITING_DEATH_DEVICE_CHANGED')
            if (checked_adb(['-s', serial, 'shell', 'pidof', PACKAGE], execute) != old_pid or
                    checked_adb(['-s', serial, 'shell', 'pidof', EDITOR], execute) != editor_pid):
                raise ValueError('EDITING_DEATH_PROCESS_IDENTITY')
            # Kill only the verified Rune PID. force-stop also changes Android's
            # package stopped state and does not model an ordinary process death.
            checked_adb(['-s', serial, 'shell', 'run-as', PACKAGE, 'kill', '-9', old_pid], execute)
            transcript, _ = process.communicate(timeout=30)
        finally:
            if process.poll() is None:
                process.terminate()
                process.communicate(timeout=30)
        (output / (scope + '-prepare.log')).write_text(transcript)
        if not prepare_crashed(transcript):
            raise ValueError('EDITING_DEATH_CRASH_NOT_PROVEN')
        if owned_emulator(avd_name, execute) != serial or checked_adb(
                ['-s', serial, 'shell', 'pidof', EDITOR], execute) != editor_pid:
            raise ValueError('EDITING_DEATH_EDITOR_LOST')
        command = ['adb', '-s', serial, 'shell', 'am', 'instrument', '-w', '-r', *args,
                   '-e', 'class', CLASS + '#' + RECOVER, PACKAGE + '.test/androidx.test.runner.AndroidJUnitRunner']
        result = execute(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (output / (scope + '-recover.log')).write_text(result.stdout)
        if owned_emulator(avd_name, execute) != serial:
            raise ValueError('EDITING_DEATH_DEVICE_CHANGED')
        passed = result.returncode == 0 and verified_instrumentation(result.stdout, CLASS, RECOVER)
        results.append({'scope': scope, 'prepareCrashVerified': True, 'recoveryPassed': passed})
        print('EDITING_PROCESS_DEATH', scope, 'passed', passed, flush=True)
        if not passed:
            break
    passed = len(results) == 2 and all(item['recoveryPassed'] for item in results)
    (output / 'receipt.json').write_text(json.dumps({'schema': 1, 'api': api, 'scopes': results,
                                                    'passed': passed}, indent=2, sort_keys=True) + '\n')
    return 0 if passed else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--avd-name', required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.output, args.avd_name))
