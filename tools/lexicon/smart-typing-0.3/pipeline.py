#!/usr/bin/env python3
"""Run the immutable lexicon pipeline with all mutable files in explicit build/."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
PACKAGE = Path(__file__).resolve().parent
sys.path.insert(0, str(PACKAGE/'scripts'))
from pipeline_config import BUILD_VARIABLE, assert_build_tree, build_root, prepare, safe_path, verify_inputs  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-dir', required=True, help='dedicated project build/ child; never tools/')
    parser.add_argument('--source-cache', type=Path, help='explicit cache containing locked paths, e.g. sources/ and downloads/')
    parser.add_argument('--fetch', action='store_true', help='authorize downloads of missing locked inputs only')
    parser.add_argument('--scowl-work', default='scowl-first', help='fresh work directory name for host stage')
    parser.add_argument('stage', choices=['acquire', 'host', 'diagnose', 'expand', 'finalize', 'verify', 'reproduce', 'test'])
    args = parser.parse_args()
    if (args.fetch or args.source_cache) and args.stage not in {'acquire', 'reproduce'}:
        parser.error('--fetch/--source-cache apply only to acquire or reproduce')
    root = build_root(args.build_dir)
    prepare(root)
    environment = dict(os.environ, **{BUILD_VARIABLE: str(root), 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONIOENCODING': 'utf-8'})

    def run(script: str, arguments: list[str] | None = None, log: str | None = None) -> None:
        assert_build_tree(root)
        if script != 'fetch_sources.py':
            verify_inputs(root)
        command = [sys.executable, str(PACKAGE/'scripts'/script), *(arguments or [])]
        if log is None:
            subprocess.run(command, env=environment, check=True)
        else:
            with safe_path(root, 'reports/'+log).open('w', encoding='utf-8') as output:
                subprocess.run(command, env=environment, stdout=output, check=True)

    def acquire() -> None:
        flags = ['--fetch'] if args.fetch else []
        if args.source_cache:
            flags += ['--source-cache', str(args.source_cache.resolve())]
        run('fetch_sources.py', flags)

    def expand() -> None:
        run('source_witnesses.py')
        run('expand_affixes.py', log='finite-expansion.log')
        run('expand_affixes.py', log='finite-expansion-repeat.log')

    if args.stage == 'acquire':
        acquire()
    elif args.stage == 'host':
        run('build_host_tools.py', ['--scowl-work', args.scowl_work])
    elif args.stage == 'diagnose':
        run('check_unmunch.py')
    elif args.stage == 'expand':
        expand()
    elif args.stage == 'finalize':
        run('finalize_inputs.py')
        run('verify_outputs.py')
    elif args.stage == 'verify':
        run('verify_outputs.py')
    elif args.stage == 'test':
        subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', str(PACKAGE/'scripts'),
                        '-p', 'test_*.py', '-v'], env=environment, check=True)
    else:
        acquire()
        selections = []
        for suffix in ('first', 'second'):
            run('build_host_tools.py', ['--scowl-work', 'scowl-'+suffix])
            data = (root/'reports/en-scowl60-latin1.txt').read_bytes()
            selections.append({'rows': data.count(b'\n'), 'sha256': hashlib.sha256(data).hexdigest()})
        if selections[0] != selections[1] or selections[0] != {'rows': 123679, 'sha256': '2d85306ee69f0b01925d703299efc67d4830aef72e990d816a0ab040d2fb55b2'}:
            raise ValueError('Two clean SCOWL builds must match the frozen source selection')
        safe_path(root, 'reports/scowl-reproducibility.json').write_text(json.dumps({
            'identical': True, 'first_rows': selections[0]['rows'], 'second_rows': selections[1]['rows'],
            'first_sha256': selections[0]['sha256'], 'second_sha256': selections[1]['sha256']}, indent=2)+'\n')
        run('check_unmunch.py')
        expand()
        run('finalize_inputs.py')
        run('verify_outputs.py')


if __name__ == '__main__':
    main()
