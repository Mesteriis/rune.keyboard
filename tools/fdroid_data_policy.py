#!/usr/bin/env python3
"""Check exact reviewed F-Droid data exceptions; this is not a source scanner."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

REPO = Path(__file__).resolve().parents[1]
POLICY = REPO / 'fdroid/review-data-policy.json'
DATA_SUFFIXES = {'.bin', '.ctx', '.gram', '.zip'}


class DataPolicyError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise DataPolicyError(code)


def relative_file(root: Path, name: str) -> Path:
    require(isinstance(name, str) and re.fullmatch(r'[A-Za-z0-9_+./-]+', name) is not None and
            not name.startswith('/') and '..' not in PurePosixPath(name).parts and
            PurePosixPath(name).as_posix() == name, 'INVALID_POLICY_PATH')
    path = root / name
    require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root.resolve()),
            'POLICY_FILE_MISSING_OR_UNSAFE')
    return path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def parse_policy(data: bytes) -> dict:
    def unique(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, 'DUPLICATE_POLICY_KEY')
            value[key] = item
        return value
    value = json.loads(data, object_pairs_hook=unique)
    require(isinstance(value, dict) and set(value) == {'schema', 'sourceCommit', 'scannerVersion', 'entries'} and
            type(value['schema']) is int and value['schema'] == 1 and value['scannerVersion'] == '2.4.5' and
            isinstance(value['sourceCommit'], str) and re.fullmatch(r'[0-9a-f]{40}', value['sourceCommit']) is not None and
            isinstance(value['entries'], list) and bool(value['entries']), 'DATA_POLICY_SCHEMA')
    return value


def check(root: Path, value: dict) -> dict:
    discovered = set()
    for directory in ('app/src/main/assets', 'app/src/test/resources', 'tools/emoji/sources',
                      'tools/typing_experiments/baseline'):
        for path in (root / directory).rglob('*'):
            if path.is_file() and path.suffix in DATA_SUFFIXES:
                discovered.add(path.relative_to(root).as_posix())
    registered = set()
    actions = {name: [] for name in ('ignore', 'inventory', 'delete')}
    for entry in value['entries']:
        require(isinstance(entry, dict) and set(entry) == {'path', 'bytes', 'sha256', 'action', 'provenance', 'provenanceSha256'},
                'DATA_ENTRY_SCHEMA')
        name = entry['path']
        require(isinstance(name, str) and name in discovered, 'UNREVIEWED_OR_STALE_DATA_SET')
        path = relative_file(root, name)
        require(name not in registered, 'DUPLICATE_DATA_ENTRY')
        registered.add(name)
        require(type(entry['bytes']) is int and entry['bytes'] > 0 and
                all(isinstance(entry[key], str) and re.fullmatch(r'[0-9a-f]{64}', entry[key]) is not None
                    for key in ('sha256', 'provenanceSha256')), 'DATA_ENTRY_IDENTITY')
        require(path.stat().st_size == entry['bytes'] and digest(path) == entry['sha256'], 'DATA_BYTES_DRIFT')
        declared = entry['provenance']
        require(isinstance(declared, str) and declared.endswith('.json') and
                (declared.startswith(('app/src/main/assets/', 'app/src/test/resources/')) or
                 declared == 'tools/emoji/source-manifest.json'), 'INVALID_PROVENANCE_SCOPE')
        provenance = relative_file(root, declared)
        require(digest(provenance) == entry['provenanceSha256'], 'DECLARED_PROVENANCE_DRIFT')
        expected = 'delete' if name.startswith('tools/typing_experiments/baseline/') else (
            'inventory' if path.suffix in {'.ctx', '.gram'} else 'ignore')
        require(entry['action'] == expected, 'SCANNER_ACTION_MISMATCH')
        actions[expected].append(name)
        # Upstream 2.4.5 uses startswith after resolving an exact scanignore path.
        # Refuse siblings/directories which would otherwise inherit that suppression.
        if expected in {'ignore', 'delete'}:
            require(not any(sibling.name != path.name and sibling.name.startswith(path.name)
                            for sibling in path.parent.iterdir()), 'SCANNER_PREFIX_COLLISION')
    require(discovered == registered, 'UNREVIEWED_OR_STALE_DATA_SET')
    return dict(schema=1, passed=True, entries=len(registered),
                scanignore=sorted(actions['ignore']), scandelete=sorted(actions['delete']),
                inventoryOnly=sorted(actions['inventory']))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=REPO)
    parser.add_argument('--policy', type=Path, default=POLICY)
    args = parser.parse_args()
    try:
        data = args.policy.read_bytes()
        result = check(args.root, parse_policy(data))
        result['policySha256'] = hashlib.sha256(data).hexdigest()
        print(json.dumps(result, sort_keys=True, indent=2))
    except (DataPolicyError, OSError, ValueError, UnicodeError) as error:
        parser.exit(1, 'F-Droid data policy failed: ' +
                    (str(error) if isinstance(error, DataPolicyError) else type(error).__name__) + '\n')


if __name__ == '__main__':
    main()
