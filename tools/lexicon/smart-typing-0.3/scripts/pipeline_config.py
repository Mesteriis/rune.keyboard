"""Immutable package metadata and an explicitly selected, isolated build root."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath

PACKAGE = Path(__file__).resolve().parents[1]
PROJECT = PACKAGE.parents[2]
FROZEN_MANIFEST_SHA256 = 'ec26c80edd28f2b42008a844c8b0ce83c11759386ccc9de591cb038a7a4f3c48'
LOCK_SHA256 = '28750e183ef99ea33da58b20036e2f0dcb3f7e1f76e8528c21074ac7d6615b70'
BUILD_VARIABLE = 'RUNE_LEXICON_BUILD_DIR'


def build_root(value: str | None = None) -> Path:
    selected = value if value is not None else os.environ.get(BUILD_VARIABLE)
    if not selected:
        raise ValueError('An explicit --build-dir is required; use pipeline.py')
    path = Path(selected)
    path = (PROJECT / path).resolve() if not path.is_absolute() else path.resolve()
    allowed = (PROJECT / 'build').resolve()
    if allowed != PROJECT.resolve() / 'build':
        raise ValueError('Project build/ must not redirect through a symlink')
    if path == allowed or allowed not in path.parents:
        raise ValueError('Build directory must be a dedicated child of the project build/ directory')
    assert_build_tree(path)
    return path


def safe_path(root: Path, relative: str) -> Path:
    part = PurePosixPath(relative)
    if part.is_absolute() or '..' in part.parts or not part.parts:
        raise ValueError(f'Unsafe package-relative path: {relative}')
    result = (root / relative).resolve()
    if root.resolve() not in result.parents:
        raise ValueError(f'Path escapes selected directory: {relative}')
    return result


def assert_build_tree(root: Path) -> None:
    """Reject pre-existing escaping links before any stage writes.

    The build directory has a single writer. This snapshot is not a sandbox for
    concurrent filesystem mutation. Do not follow directory links while walking:
    their physical targets are checked separately within the same build tree.
    """
    root = root.resolve()
    if not root.exists():
        return
    pending = [root]
    readonly_tools = {'bin/host-tools/find', 'bin/host-tools/grep'}
    while pending:
        with os.scandir(pending.pop()) as entries:
            for entry in entries:
                path = Path(entry.path)
                if entry.is_symlink():
                    relative = path.relative_to(root).as_posix()
                    try:
                        target = path.resolve()
                    except (OSError, RuntimeError) as error:
                        raise ValueError(f'Invalid build symlink: {relative}') from error
                    if relative in readonly_tools:
                        # Only these executable leaves are read/execute-only.
                        # Host setup unlinks the leaf before recreating it; it
                        # never writes through it. Directory redirects fail.
                        if not target.is_file() or not os.access(target, os.X_OK):
                            raise ValueError(f'Invalid read-only host tool link: {relative}')
                    elif target != root and root not in target.parents:
                        raise ValueError(f'Build symlink escapes selected directory: {relative}')
                elif entry.is_dir(follow_symlinks=False):
                    pending.append(path)


def load_frozen_manifest(package: Path | None = None) -> dict:
    path = (PACKAGE if package is None else package) / 'frozen-output-manifest.json'
    if not path.is_file():
        raise ValueError('Missing immutable frozen-output-manifest.json')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != FROZEN_MANIFEST_SHA256:
        raise ValueError('Frozen output-manifest SHA-256 mismatch')
    return json.loads(raw)


def load_lock(package: Path = PACKAGE) -> list[dict]:
    path = package / 'source-lock.json'
    if not path.is_file():
        raise ValueError('Missing immutable source-lock.json; unpinned bootstrap is forbidden')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != LOCK_SHA256:
        raise ValueError('Frozen source-lock SHA-256 mismatch')
    records = json.loads(raw)
    paths = set()
    for record in records:
        if record['path'] in paths or len(record['sha256']) != 64 or not record['url'].startswith('https://'):
            raise ValueError('Malformed immutable source record')
        safe_path(package, record['path'])
        paths.add(record['path'])
    return records


def assert_record(path: Path, record: dict) -> None:
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != record['sha256']:
        raise ValueError(f'SHA-256 mismatch: {record["path"]}')
    if len(data) != record['bytes']:
        raise ValueError(f'Byte count mismatch: {record["path"]}')
    if 'rows' in record and data.count(b'\n') != record['rows']:
        raise ValueError(f'Row count mismatch: {record["path"]}')


def prepare(root: Path) -> None:
    load_lock()
    manifest = load_frozen_manifest()
    assert_build_tree(root)
    for record in manifest['notices']:
        assert_record(safe_path(PACKAGE, record['path']), record)
    # Every mutable path is under the caller's dedicated ignored build root.
    root.mkdir(parents=True, exist_ok=True)
    ignore = safe_path(root, '.gitignore')
    if ignore.exists() and ignore.read_text(encoding='utf-8') != '*\n':
        raise ValueError('Existing build .gitignore differs; choose a dedicated directory')
    ignore.write_text('*\n', encoding='utf-8')
    for directory in ('downloads', 'sources', 'reports', 'outputs', 'outputs/frequency', 'notices', 'bin', 'work'):
        safe_path(root, directory).mkdir(parents=True, exist_ok=True)
    for relative in ['source-lock.json'] + [record['path'] for record in manifest['notices']]:
        source = safe_path(PACKAGE, relative)
        target = safe_path(root, relative)
        if target.exists() and target.read_bytes() != source.read_bytes():
            raise ValueError(f'Existing immutable build metadata differs: {relative}')
        if not target.exists():
            target.write_bytes(source.read_bytes())


def verify_inputs(root: Path) -> None:
    for record in load_lock():
        assert_record(safe_path(root, record['path']), record)
