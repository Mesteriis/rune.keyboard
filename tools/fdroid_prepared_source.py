"""Validate the exact committed F-Droid source transformations, without repairing Git."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

from release_source_check import SourceCheckError, git, status_count

POLICY = 'fdroid/prepared-source-policy.json'
PREPARER = 'fdroidserver-2.4.5'


def refuse(code: str) -> None:
    raise SourceCheckError('RELEASE_PREPARED_' + code)


def relative(value: object) -> str:
    if not isinstance(value, str) or not value or '\\' in value or any(ord(c) < 32 for c in value):
        refuse('POLICY')
    path = PurePosixPath(value)
    if not path.parts or path.is_absolute() or str(path) != value or any(p in ('.', '..', '.git') for p in path.parts):
        refuse('POLICY')
    return value


def ordinary_path(root: Path, name: str, *, missing: bool = False) -> Path:
    path = root
    for index, part in enumerate(PurePosixPath(name).parts):
        path /= part
        if path.is_symlink():
            refuse('SYMLINK')
        if index < len(PurePosixPath(name).parts) - 1 and not path.is_dir():
            refuse('PATH')
    if not missing and not path.is_file():
        refuse('PATH')
    return path


def parse_policy(raw: bytes) -> list[dict]:
    def unique(items):
        result = {}
        for key, value in items:
            if key in result:
                refuse('POLICY')
            result[key] = value
        return result
    try:
        policy = json.loads(raw, object_pairs_hook=unique)
    except (ValueError, UnicodeError) as error:
        raise SourceCheckError('RELEASE_PREPARED_POLICY') from error
    if not isinstance(policy, dict) or set(policy) != {'schema', 'preparer', 'changes'} or \
            type(policy['schema']) is not int or policy['schema'] != 1 or policy['preparer'] != PREPARER:
        refuse('POLICY')
    changes = policy['changes']
    if not isinstance(changes, list) or not changes or len(changes) > 32:
        refuse('POLICY')
    seen = set()
    for row in changes:
        if not isinstance(row, dict):
            refuse('POLICY')
        fields = {'path', 'action', 'beforeSha256'}
        if row.get('action') == 'replace':
            fields.add('afterSha256')
        elif row.get('action') != 'delete':
            refuse('POLICY')
        if set(row) != fields:
            refuse('POLICY')
        name = relative(row['path'])
        if name == POLICY or name in seen:
            refuse('POLICY')
        seen.add(name)
        for key in fields - {'path', 'action'}:
            if not isinstance(row[key], str) or re.fullmatch('[0-9a-f]{64}', row[key]) is None:
                refuse('POLICY')
        if row['action'] == 'replace' and row['beforeSha256'] == row['afterSha256']:
            refuse('POLICY')
    return changes


def tree(root: Path) -> dict[bytes, tuple[bytes, bytes, bytes]]:
    result = {}
    for row in git(root, 'ls-tree', '-r', '-z', 'HEAD').split(b'\x00'):
        if not row:
            continue
        header, separator, name = row.partition(b'\t')
        parts = header.split(b' ')
        if not separator or len(parts) != 3 or not name or name in result:
            refuse('GIT_PROTOCOL')
        result[name] = tuple(parts)
    return result


def check_prepared(root: Path) -> dict:
    try:
        return _check_prepared(root)
    except OSError as error:
        raise SourceCheckError('RELEASE_PREPARED_IO') from error


def _check_prepared(root: Path) -> dict:
    root = root.resolve()
    top = Path(os.fsdecode(git(root, 'rev-parse', '--show-toplevel').rstrip(b'\n')))
    if top.resolve() != root:
        refuse('ROOT_MISMATCH')
    commit = git(root, 'rev-parse', '--verify', 'HEAD^{commit}').strip()
    if re.fullmatch(rb'[0-9a-f]{40}|[0-9a-f]{64}', commit) is None:
        refuse('GIT_PROTOCOL')
    committed = git(root, 'show', 'HEAD:' + POLICY)
    working = ordinary_path(root, POLICY).read_bytes()
    if working != committed:
        refuse('POLICY_DIRTY')
    changes = parse_policy(committed)
    # Every module must still have its exact recorded commit. Walking the tree
    # avoids whitespace/quoting ambiguities in human `git submodule status` output.
    checkouts = {}
    def visit(checkout: Path, prefix: str, expected: bytes | None = None):
        if prefix in checkouts or len(checkouts) >= 64:
            refuse('SUBMODULE_PROTOCOL')
        actual_top = Path(os.fsdecode(git(checkout, 'rev-parse', '--show-toplevel').rstrip(b'\n')))
        actual = git(checkout, 'rev-parse', '--verify', 'HEAD^{commit}').strip()
        if actual_top.resolve() != checkout.resolve() or (expected is not None and actual != expected):
            refuse('SUBMODULE_NOT_READY')
        entries = tree(checkout)
        # Git assume-unchanged/skip-worktree can hide source changes from status.
        for entry in git(checkout, 'ls-files', '-v', '-z').split(b'\x00'):
            if entry and entry[:1] != b'H':
                refuse('INDEX_FLAGS')
        checkouts[prefix] = (checkout, entries, set())
        for name, (mode, kind, object_id) in entries.items():
            if mode == b'160000' and kind == b'commit':
                path = relative(os.fsdecode(name))
                module = ordinary_path(checkout, path, missing=True)
                if not module.is_dir():
                    refuse('SUBMODULE_NOT_READY')
                visit(module, prefix + path + '/', object_id)
    visit(root, '')
    for row in changes:
        name = row['path']
        prefix = max((p for p in checkouts if name.startswith(p)), key=len)
        checkout, entries, expected = checkouts[prefix]
        local = name[len(prefix):]
        entry = entries.get(os.fsencode(local))
        if entry is None or entry[0] not in (b'100644', b'100755') or entry[1] != b'blob':
            refuse('BASE_FILE')
        before = git(checkout, 'cat-file', 'blob', entry[2].decode('ascii'))
        if hashlib.sha256(before).hexdigest() != row['beforeSha256']:
            refuse('BASE_HASH')
        path = ordinary_path(checkout, local, missing=row['action'] == 'delete')
        if row['action'] == 'delete':
            if path.exists():
                refuse('EXPECTED_DELETE')
            expected.add(b' D ' + os.fsencode(local))
        else:
            if hashlib.sha256(path.read_bytes()).hexdigest() != row['afterSha256']:
                refuse('REPLACEMENT_HASH')
            if bool(path.stat().st_mode & stat.S_IXUSR) != (entry[0] == b'100755'):
                refuse('FILE_MODE')
            expected.add(b' M ' + os.fsencode(local))
    # A module's allowed child delta also appears as an unstaged module change
    # in every enclosing checkout. No staged entries or unrelated changes pass.
    for prefix in sorted(checkouts, key=len, reverse=True):
        checkout, entries, expected = checkouts[prefix]
        if prefix and expected:
            parent = max((p for p in checkouts if p != prefix and prefix.startswith(p)), key=len)
            checkouts[parent][2].add(b' M ' + os.fsencode(prefix[len(parent):].rstrip('/')))
        raw = git(checkout, 'status', '--porcelain=v1', '-z', '--untracked-files=all', '--ignore-submodules=none')
        status_count(raw)  # Validate the full NUL protocol, including rename records.
        actual = raw.split(b'\x00')[:-1] if raw else []
        if len(actual) != len(expected) or set(actual) != expected:
            refuse('SOURCE_DELTA')
    return dict(schema=1, passed=True, commit=commit.decode('ascii'), preparedSource=PREPARER,
                policySha256=hashlib.sha256(committed).hexdigest(), approvedChanges=len(changes),
                submodules=len(checkouts) - 1)
