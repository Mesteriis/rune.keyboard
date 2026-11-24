#!/usr/bin/env python3
"""Exercise voice-IME discovery with a silent fixture on one disposable emulator."""
import argparse
import json
from pathlib import Path
import re
import subprocess

from android_synthetic_restart_suites import checked_adb, owned_emulator, verified_instrumentation

ROOT = Path(__file__).resolve().parents[2]
RUNE = 'io.github.mesteriis.rune.keyboard'
FIXTURE = 'io.github.mesteriis.rune.qa.compose'
RUNE_IME = RUNE + '/.ime.RuneInputMethodService'
VOICE = FIXTURE + '/.VoiceInputMethodService'
CLASS = RUNE + '.qa.VoiceInputInstrumentedTest'
SCOPES = (('unavailable', 'unavailableVoiceSubtypeIsNotOffered'),
          ('enabled', 'enabledVoiceSubtypeIsOfferedAndActuallySelected'),
          ('gesture', 'voicePopupGestureSwitchesTheIme'),
          ('stale', 'voiceDisabledAfterKeyboardShownFallsBackToPicker'))
NEXT = {'26': ('next_picker', 'nextKeyboardPopupOpensSystemPickerOnApi26'),
        '37': ('next_switch', 'nextKeyboardPopupSwitchesOrShowsPicker')}
COMPONENT = re.compile(r'[A-Za-z0-9_.]+/[A-Za-z0-9_.$]+\Z')


def ime_list(serial, all_methods, execute):
    args = ['-s', serial, 'shell', 'ime', 'list', '-s'] + (['-a'] if all_methods else [])
    lines = checked_adb(args, execute).splitlines()
    if any(not COMPONENT.fullmatch(line.strip()) for line in lines):
        raise ValueError('VOICE_IME_LIST')
    return {line.strip() for line in lines}


def run(output, avd_name, execute=subprocess.run):
    output = Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'):
        raise ValueError('VOICE_FIXTURE_OUTPUT')
    serial = owned_emulator(avd_name, execute)
    api = checked_adb(['-s', serial, 'shell', 'getprop', 'ro.build.version.sdk'], execute)
    if api not in NEXT:
        raise ValueError('VOICE_FIXTURE_API')
    scopes = SCOPES + (NEXT[api],)
    for package in (RUNE, RUNE + '.test', FIXTURE):
        if not checked_adb(['-s', serial, 'shell', 'pm', 'path', package], execute).startswith('package:'):
            raise ValueError('VOICE_FIXTURE_MISSING')
    if VOICE not in ime_list(serial, True, execute):
        raise ValueError('VOICE_FIXTURE_NOT_REGISTERED')
    initially_enabled = ime_list(serial, False, execute)
    initial_ime = checked_adb(['-s', serial, 'shell', 'settings', 'get', 'secure', 'default_input_method'], execute)
    if not COMPONENT.fullmatch(initial_ime) or initial_ime not in initially_enabled or RUNE_IME not in initially_enabled:
        raise ValueError('VOICE_INITIAL_IME')
    voices = {item for item in initially_enabled if item.endswith('VoiceInputMethodService')}
    output.mkdir(parents=True, mode=0o700)
    results = []
    try:
        for component in sorted(voices):
            if owned_emulator(avd_name, execute) != serial:
                raise ValueError('VOICE_DEVICE_CHANGED')
            checked_adb(['-s', serial, 'shell', 'ime', 'disable', component], execute)
        if voices & ime_list(serial, False, execute):
            raise ValueError('VOICE_DISABLE_FAILED')
        for mode, method in scopes:
            if owned_emulator(avd_name, execute) != serial:
                raise ValueError('VOICE_DEVICE_CHANGED')
            if mode == 'enabled':
                checked_adb(['-s', serial, 'shell', 'ime', 'enable', VOICE], execute)
                if VOICE not in ime_list(serial, False, execute):
                    raise ValueError('VOICE_ENABLE_FAILED')
            checked_adb(['-s', serial, 'shell', 'ime', 'set', RUNE_IME], execute)
            command = ['adb', '-s', serial, 'shell', 'am', 'instrument', '-w', '-r',
                       '-e', 'voice_test_mode', mode, '-e', 'voice_ime', VOICE,
                       '-e', 'runeCiFailureCapture', 'true', '-e', 'class', CLASS + '#' + method,
                       RUNE + '.test/androidx.test.runner.AndroidJUnitRunner']
            result = execute(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            (output / (mode + '.log')).write_text(result.stdout)
            if owned_emulator(avd_name, execute) != serial:
                raise ValueError('VOICE_DEVICE_CHANGED')
            passed = result.returncode == 0 and verified_instrumentation(result.stdout, CLASS, method)
            results.append({'scope': mode, 'passed': passed})
            print('VOICE_FIXTURE_SCOPE', mode, 'passed', passed, flush=True)
            if not passed:
                break
    finally:
        if owned_emulator(avd_name, execute) != serial:
            raise ValueError('VOICE_DEVICE_CHANGED')
        current = ime_list(serial, False, execute)
        if VOICE in current and VOICE not in initially_enabled:
            checked_adb(['-s', serial, 'shell', 'ime', 'disable', VOICE], execute)
        for component in sorted(voices):
            checked_adb(['-s', serial, 'shell', 'ime', 'enable', component], execute)
        checked_adb(['-s', serial, 'shell', 'ime', 'set', initial_ime], execute)
    passed = len(results) == len(scopes) and all(item['passed'] for item in results)
    (output / 'receipt.json').write_text(json.dumps({'schema': 1, 'scopes': results, 'passed': passed},
                                                    indent=2, sort_keys=True) + '\n')
    return 0 if passed else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--avd-name', required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.output, args.avd_name))
