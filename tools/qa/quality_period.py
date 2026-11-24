#!/usr/bin/env python3
"""Compare two RUNE_QUALITY_3 numeric snapshots; this does not certify owner use."""

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path

SOURCES = (
    'COMMON_CONFUSION', 'GENERAL_LOCAL', 'COMPACT_PUBLIC', 'NEIGHBOR_RECOVERY',
    'JOINT_SHORT', 'JOINT_LONG', 'JOINT_RESCUE', 'WORD_CONTEXT', 'CONTEXTUAL_RANKER',
    'INFINITIVE_REVISION', 'NOUN_CASE_REVISION', 'MODEL', 'CONTEXTUAL', 'CANONICAL_CASE',
)
MAX_COUNT = 1_000_000_000_000
SOURCE_OFFSET = 8 + 6 + 6
COUNTS = SOURCE_OFFSET + len(SOURCES) * 4 + 5


def read_snapshot(path, metadata_path):
    raw = Path(path).read_bytes()
    metadata = json.loads(Path(metadata_path).read_text(encoding='utf-8'))
    if hashlib.sha256(raw).hexdigest() != metadata['snapshot_sha256']:
        raise ValueError('snapshot hash mismatch')
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
    timestamp = dt.datetime.fromisoformat(metadata['captured_utc'].replace('Z', '+00:00'))
    if timestamp.utcoffset() is None:
        raise ValueError('capture timestamp must include timezone')
    return timestamp, values


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
    parser.add_argument('baseline_snapshot')
    parser.add_argument('baseline_metadata')
    parser.add_argument('final_snapshot')
    parser.add_argument('final_metadata')
    args = parser.parse_args()
    try:
        result = compare(read_snapshot(args.baseline_snapshot, args.baseline_metadata),
                         read_snapshot(args.final_snapshot, args.final_metadata))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f'Cannot compare snapshots: {error}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
