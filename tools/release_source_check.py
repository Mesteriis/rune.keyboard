#!/usr/bin/env python3
"""Require a clean, committed Git checkout with initialized matching submodules."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess

REPO = Path(__file__).resolve().parents[1]


class SourceCheckError(ValueError):
    pass


def git(root: Path, *args: str) -> bytes:
    try:
        result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise SourceCheckError('RELEASE_GIT_QUERY_FAILED') from error
    if result.returncode:
        raise SourceCheckError('RELEASE_GIT_QUERY_FAILED')
    return result.stdout


def status_count(output: bytes) -> int:
    if not output:
        return 0
    if not output.endswith(b'\x00'):
        raise SourceCheckError('RELEASE_STATUS_PROTOCOL')
    records = output.split(b'\x00')[:-1]
    count = index = 0
    while index < len(records):
        record = records[index]
        if len(record) < 4 or record[2:3] != b' ':
            raise SourceCheckError('RELEASE_STATUS_PROTOCOL')
        count += 1
        index += 1
        if b'R' in record[:2] or b'C' in record[:2]:
            if index >= len(records) or not records[index]:
                raise SourceCheckError('RELEASE_STATUS_PROTOCOL')
            index += 1
    return count


def check(root: Path) -> dict:
    top = Path(os.fsdecode(git(root, 'rev-parse', '--show-toplevel').rstrip(b'\n')))
    if top.resolve() != root.resolve():
        raise SourceCheckError('RELEASE_ROOT_MISMATCH')
    commit = git(root, 'rev-parse', '--verify', 'HEAD^{commit}').strip()
    if re.fullmatch(rb'[0-9a-f]{40}|[0-9a-f]{64}', commit) is None:
        raise SourceCheckError('RELEASE_COMMIT_PROTOCOL')
    count = status_count(git(root, 'status', '--porcelain=v1', '-z', '--untracked-files=all', '--ignore-submodules=none'))
    result = dict(schema=1, passed=False, commit=commit.decode('ascii'), statusEntries=count, submodules=None)
    if count:
        return dict(result, reason='RELEASE_SOURCE_DIRTY')
    rows = git(root, 'submodule', 'status', '--recursive').splitlines()
    result['submodules'] = len(rows)
    for row in rows:
        if re.match(rb'^[ +U-](?:[0-9a-f]{40}|[0-9a-f]{64}) ', row) is None:
            raise SourceCheckError('RELEASE_SUBMODULE_PROTOCOL')
        if row[:1] != b' ':
            return dict(result, reason='RELEASE_SUBMODULE_NOT_READY')
    return dict(result, passed=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=REPO)
    args = parser.parse_args()
    try:
        report = check(args.root)
        print(json.dumps(report, sort_keys=True))
        if not report['passed']:
            raise SourceCheckError(report['reason'])
    except SourceCheckError as error:
        parser.exit(1, 'Release source check failed: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
