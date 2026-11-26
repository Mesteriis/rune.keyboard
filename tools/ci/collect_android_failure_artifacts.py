#!/usr/bin/env python3
"""Preserve synthetic Android failure captures from one verified CI AVD."""
import argparse
import json
from pathlib import Path
import subprocess

from android_synthetic_restart_suites import checked_adb, owned_emulator

ROOT = Path(__file__).resolve().parents[2]
REMOTE = '/data/local/tmp/rune-ci-failure-captures'


def collect(output, avd_name, execute=subprocess.run):
    output = Path(output).resolve()
    if output.exists() or not output.is_relative_to((ROOT / 'app/build/ci-device').resolve()):
        raise ValueError('FAILURE_CAPTURE_OUTPUT')
    serial = owned_emulator(avd_name, execute)
    command = 'if [ -d "' + REMOTE + '" ]; then echo PRESENT; elif [ -e "' + REMOTE + '" ]; then echo INVALID; else echo ABSENT; fi'
    state = checked_adb(['-s', serial, 'shell', command], execute)
    if state not in ('PRESENT', 'ABSENT'):
        raise ValueError('FAILURE_CAPTURE_REMOTE_STATE')
    output.mkdir(parents=True, mode=0o700)
    pngs, xmls = set(), set()
    if state == 'PRESENT':
        checked_adb(['-s', serial, 'pull', REMOTE, str(output / 'captures')], execute)
        if not (output / 'captures').is_dir():
            raise ValueError('FAILURE_CAPTURE_PULL_MISSING')
        for path in (output / 'captures').rglob('*'):
            if path.is_symlink():
                raise ValueError('FAILURE_CAPTURE_SYMLINK')
            if path.is_file() and path.stat().st_size:
                if path.suffix == '.png':
                    pngs.add(path.relative_to(output / 'captures').with_suffix('').as_posix())
                elif path.suffix == '.xml':
                    xmls.add(path.relative_to(output / 'captures').with_suffix('').as_posix())
        if not pngs and not xmls:
            raise ValueError('FAILURE_CAPTURE_EMPTY')
    if owned_emulator(avd_name, execute) != serial:
        raise ValueError('FAILURE_CAPTURE_DEVICE_CHANGED')
    receipt = {'schemaVersion': 1, 'state': state, 'screenshots': len(pngs), 'hierarchies': len(xmls),
               'missingScreenshots': len(xmls - pngs), 'missingHierarchies': len(pngs - xmls)}
    (output / 'receipt.json').write_text(json.dumps(receipt, sort_keys=True) + '\n')
    print('ANDROID_FAILURE_CAPTURES', state, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--avd-name', required=True)
    args = parser.parse_args()
    collect(args.output, args.avd_name)
