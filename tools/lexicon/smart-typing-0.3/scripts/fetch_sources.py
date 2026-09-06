#!/usr/bin/env python3
"""Verify pinned inputs; acquire missing bytes only from an explicit cache or --fetch."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile
from pipeline_config import PACKAGE, assert_build_tree, assert_record, build_root, load_lock, safe_path


def acquire(root: Path, source_cache: Path | None = None, allow_fetch: bool = False) -> int:
    assert_build_tree(root)
    records = load_lock(PACKAGE)  # Before trusting any URL, revision or path.
    for record in records:
        target = safe_path(root, record['path'])
        if target.exists():
            assert_record(target, record)
            continue  # --fetch never replaces an existing mismatched file.
        cache = safe_path(source_cache, record['path']) if source_cache is not None else None
        if cache is not None and cache.is_file():
            assert_record(cache, record)
        elif not allow_fetch:
            raise ValueError(f'Missing pinned input: {record["path"]}; supply --source-cache or explicit --fetch')
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=target.name+'.', suffix='.partial', delete=False) as handle:
            partial = Path(handle.name)
        try:
            if cache is not None and cache.is_file():
                shutil.copyfile(cache, partial)
            else:
                subprocess.run(['curl', '-fsSL', '--proto', '=https', '--proto-redir', '=https',
                                '--connect-timeout', '20', '--max-time', '120', record['url'],
                                '-o', str(partial)], check=True)
            assert_record(partial, record)
            partial.replace(target)
        finally:
            partial.unlink(missing_ok=True)
    print(f'PASS: {len(records)} immutable source files; no lock was written or updated')
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--source-cache', type=Path)
    args = parser.parse_args()
    acquire(build_root(), args.source_cache.resolve() if args.source_cache else None, args.fetch)


if __name__ == '__main__':
    main()
