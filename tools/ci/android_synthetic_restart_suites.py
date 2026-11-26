#!/usr/bin/env python3
"""Run synthetic profile restart checks only on one verified ADB emulator."""
import argparse
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = 'io.github.mesteriis.rune.keyboard'
QA = PACKAGE + '.qa.'
PAIRS = (
    ('case-rejection', QA + 'CaseRejectionPersistenceInstrumentedTest',
     'writeCaseRejectionWithoutChangingLegacyEntries', 'caseRejectionSurvivesProcessRestart'),
    ('confirmed-words', QA + 'ConfirmedWordsInstrumentedTest',
     'originalConfirmationIsVisibleAndRemovalIsDurable', 'removalSurvivesAProcessRestart'),
)


def checked_adb(args, execute=subprocess.run):
    result = execute(['adb', *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise ValueError('RESTART_ADB_FAILURE')
    return result.stdout.strip()


def owned_emulator(avd_name, execute=subprocess.run):
    if not re.fullmatch(r'rune-ci-[a-z0-9-]+', avd_name):
        raise ValueError('RESTART_AVD_NAME')
    lines = checked_adb(['devices'], execute).splitlines()
    if not lines or lines[0].strip() != 'List of devices attached':
        raise ValueError('RESTART_ADB_LIST')
    devices = [line.split() for line in lines[1:] if line.strip()]
    if len(devices) != 1 or len(devices[0]) != 2 or devices[0][1] != 'device':
        raise ValueError('RESTART_REQUIRES_ONE_DEVICE')
    serial = devices[0][0]
    if not re.fullmatch(r'emulator-[0-9]+', serial):
        raise ValueError('RESTART_REQUIRES_EMULATOR_SERIAL')
    if (checked_adb(['-s', serial, 'shell', 'getprop', 'ro.kernel.qemu'], execute) != '1' or
            checked_adb(['-s', serial, 'shell', 'getprop', 'ro.hardware'], execute) not in ('ranchu', 'goldfish')):
        raise ValueError('RESTART_REQUIRES_EMULATOR_HARDWARE')
    identity = checked_adb(['-s', serial, 'emu', 'avd', 'name'], execute).splitlines()
    if identity != [avd_name, 'OK']:
        raise ValueError('RESTART_WRONG_AVD')
    return serial


def verified_instrumentation(text, cls, method):
    """Require exact start and success events, not only Android's final -1 code."""
    events = []
    status = {}
    for line in text.splitlines():
        if line.startswith('INSTRUMENTATION_STATUS: '):
            key, sep, value = line[len('INSTRUMENTATION_STATUS: '):].partition('=')
            if sep:
                status[key] = value
        elif line.startswith('INSTRUMENTATION_STATUS_CODE: '):
            events.append((status.get('class'), status.get('test'), line.rsplit(' ', 1)[-1]))
            status = {}
    return (events == [(cls, method, '1'), (cls, method, '0')] and
            re.search(r'^OK \(1 test\)$', text, re.MULTILINE) is not None and
            re.search(r'^INSTRUMENTATION_CODE: -1$', text, re.MULTILINE) is not None and
            'INSTRUMENTATION_FAILED' not in text and 'FAILURES!!!' not in text)


def run(output, avd_name, execute=subprocess.run):
    output = Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'):
        raise ValueError('RESTART_OUTPUT')
    serial = owned_emulator(avd_name, execute)
    apks = [ROOT / 'app/build/outputs/apk/debug/app-debug.apk',
            ROOT / 'app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk']
    if any(not path.is_file() or path.is_symlink() for path in apks):
        raise ValueError('RESTART_APK_MISSING')
    output.mkdir(parents=True, mode=0o700)
    for apk in apks:
        if owned_emulator(avd_name, execute) != serial:
            raise ValueError('RESTART_DEVICE_CHANGED')
        checked_adb(['-s', serial, 'install', '-r', str(apk)], execute)
    checked_adb(['-s', serial, 'shell', 'ime', 'enable', PACKAGE + '/.ime.RuneInputMethodService'], execute)
    checked_adb(['-s', serial, 'shell', 'ime', 'set', PACKAGE + '/.ime.RuneInputMethodService'], execute)
    results = []
    for name, cls, first, second in PAIRS:
        for phase, method in (('write', first), ('reload', second)):
            scope = name + '-' + phase
            if phase == 'reload' and not results[-1]['passed']:
                results.append({'scope': scope, 'passed': False, 'reason': 'PREVIOUS_PHASE_FAILED'})
                continue
            if owned_emulator(avd_name, execute) != serial:
                raise ValueError('RESTART_DEVICE_CHANGED')
            if phase == 'reload':
                checked_adb(['-s', serial, 'shell', 'am', 'force-stop', PACKAGE], execute)
            command = ['adb', '-s', serial, 'shell', 'am', 'instrument', '-w', '-r',
                       '-e', 'runeSyntheticProfileFixture', 'true', '-e', 'runeCiFailureCapture', 'true',
                       '-e', 'class', cls + '#' + method,
                       PACKAGE + '.test/androidx.test.runner.AndroidJUnitRunner']
            result = execute(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            (output / (scope + '.log')).write_text(result.stdout)
            if owned_emulator(avd_name, execute) != serial:
                raise ValueError('RESTART_DEVICE_CHANGED')
            passed = result.returncode == 0 and verified_instrumentation(result.stdout, cls, method)
            results.append({'scope': scope, 'exitCode': result.returncode, 'passed': passed})
            print('SYNTHETIC_RESTART_SCOPE', scope, 'passed', passed, flush=True)
    receipt = {'schema': 1, 'scopes': results, 'passed': len(results) == 4 and all(r['passed'] for r in results)}
    (output / 'receipt.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    return 0 if receipt['passed'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--avd-name', required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.output, args.avd_name))
