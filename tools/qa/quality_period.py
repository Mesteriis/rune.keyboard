#!/usr/bin/env python3
"""Capture and compare RUNE_QUALITY_3 counters without changing device state."""

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile

SOURCES = (
    'COMMON_CONFUSION', 'GENERAL_LOCAL', 'COMPACT_PUBLIC', 'NEIGHBOR_RECOVERY',
    'JOINT_SHORT', 'JOINT_LONG', 'JOINT_RESCUE', 'WORD_CONTEXT', 'CONTEXTUAL_RANKER',
    'INFINITIVE_REVISION', 'NOUN_CASE_REVISION', 'MODEL', 'CONTEXTUAL', 'CANONICAL_CASE',
)
MAX_COUNT = 1_000_000_000_000
SOURCE_OFFSET = 8 + 6 + 6
COUNTS = SOURCE_OFFSET + len(SOURCES) * 4 + 5
PACKAGE = 'io.github.mesteriis.rune.keyboard'
PREFERENCE = r'^[[:space:]]*<boolean name="quality_metrics" value="true"[[:space:]]*/>[[:space:]]*$'
PREFERENCES = 'shared_prefs/keyboard_preferences.xml'
COUNTER_FILE = 'no_backup/typing-quality-v1.txt'
BUILD = Path(__file__).resolve().parents[2] / 'build'


def parse_counters(raw):
    lines = raw.split(b'\n')
    if len(raw) > 2048 or len(lines) != COUNTS + 2 or lines[0] != b'RUNE_QUALITY_3' or lines[-1] != b'':
        raise ValueError('invalid snapshot schema')
    values = []
    for item in lines[1:-1]:
        if not item or len(item) > 13 or any(c < 48 or c > 57 for c in item):
            raise ValueError('invalid counter')
        value = int(item)
        if value > MAX_COUNT:
            raise ValueError('counter out of range')
        values.append(value)
    return values


def read_snapshot(path, metadata_path):
    raw = Path(path).read_bytes()
    metadata = json.loads(Path(metadata_path).read_text(encoding='utf-8'))
    if hashlib.sha256(raw).hexdigest() != metadata['snapshot_sha256']:
        raise ValueError('snapshot hash mismatch')
    values = parse_counters(raw)
    timestamp = dt.datetime.fromisoformat(metadata['captured_utc'].replace('Z', '+00:00'))
    if timestamp.utcoffset() is None:
        raise ValueError('capture timestamp must include timezone')
    return timestamp, values


def capture_snapshot(serial, build=BUILD, *, execute=subprocess.run):
    if not serial or serial.startswith('-') or any(character.isspace() for character in serial):
        raise ValueError('an explicit ADB serial is required')

    def adb(*args):
        try:
            result = execute(['adb', '-s', serial, *args], capture_output=True, timeout=15)
        except (OSError, subprocess.TimeoutExpired):
            raise ValueError('ADB read failed') from None
        if result.returncode != 0:
            raise ValueError('ADB read failed')
        return result.stdout

    def app_read(*args):
        command = shlex.join(['run-as', PACKAGE, '--user', '0', *args])
        return adb('exec-out', command)

    def require_opt_in():
        # Emit only a literal marker for each matching line.
        if app_read('sed', '-n', f's|{PREFERENCE}|1|p', PREFERENCES).strip() != b'1':
            raise ValueError('quality metrics preference is not confirmed')

    if adb('get-state').strip() != b'device' or adb('shell', 'am', 'get-current-user').strip() != b'0':
        raise ValueError('ADB must target an online device using Android user 0')
    require_opt_in()
    raw = app_read('head', '-c', '2049', COUNTER_FILE)
    captured = dt.datetime.now(dt.timezone.utc).isoformat()
    parse_counters(raw)
    require_opt_in()

    metadata = {
        'captured_utc': captured,
        'snapshot_sha256': hashlib.sha256(raw).hexdigest(),
        'quality_metrics_enabled_before_and_after': True,
    }
    build.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='fold-owner-q4-observation-', dir=build))
    try:
        for name, value in (('quality.txt', raw), ('metadata.json', (json.dumps(metadata) + '\n').encode())):
            fd = os.open(directory / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(value)
    except BaseException:
        shutil.rmtree(directory)
        raise
    return directory


def compare(start, end):
    start_time, old = start
    end_time, new = end
    elapsed = (end_time - start_time).total_seconds()
    if elapsed <= 0:
        raise ValueError('final snapshot must be later than baseline')
    if len(old) != COUNTS or len(new) != COUNTS:
        raise ValueError('invalid counter count')
    if any(a > b for a, b in zip(old, new)):
        raise ValueError('counter decreased; reset or incompatible snapshots')
    if any(v == MAX_COUNT for v in old + new):
        raise ValueError('saturated counter prevents reliable comparison')
    sources = {}
    for index, name in enumerate(SOURCES):
        offset = SOURCE_OFFSET + index * 4
        applied, undo, kept, expired = (new[i] - old[i] for i in range(offset, offset + 4))
        # Undo can cross the baseline boundary; it is not necessarily an undo of a period application.
        sources[name] = {
            'applied': applied, 'explicit_undo': undo, 'kept_original': kept,
            'window_expired': expired,
            'undo_per_application': undo / applied if applied >= 100 else None,
            'cross_boundary_undo_possible': True,
        }
    return {
        'elapsed_seconds': elapsed,
        'at_least_14_days': elapsed >= 14 * 86400,
        'continuity_and_ordinary_owner_use_verified': False,
        'reset_excluded': False,
        'correctness_measured': False,
        'sources': sources,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', metavar='ADB_SERIAL')
    parser.add_argument('files', nargs='*', metavar='FILE',
                        help='baseline snapshot, baseline metadata, final snapshot, final metadata')
    args = parser.parse_args()
    if args.capture is not None:
        if args.files:
            parser.error('--capture does not take snapshot paths')
        try:
            directory = capture_snapshot(args.capture)
        except OSError:
            parser.exit(2, 'Cannot save private snapshot\n')
        except ValueError as error:
            parser.exit(2, f'Cannot capture snapshot: {error}\n')
        print(directory.relative_to(BUILD.parent))
        return
    if len(args.files) != 4:
        parser.error('provide four snapshot paths or use --capture ADB_SERIAL')
    baseline, baseline_meta, final, final_meta = args.files
    try:
        result = compare(read_snapshot(baseline, baseline_meta), read_snapshot(final, final_meta))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f'Cannot compare snapshots: {error}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
