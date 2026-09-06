#!/usr/bin/env python3
"""Offline host build from verified archives. No installation or global package changes."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile

from pipeline_config import PACKAGE, assert_build_tree, build_root, safe_path

ROOT = build_root()
HUNSPELL = 'e184e22c51fe213f4490e9b36998f0ad3e5e606b'
SCOWL = '5ef55f9c42730ebe4394a78b77855468a6f15dd2'


def tool_record(path: str, version_arg: str = '--version') -> dict:
    resolved = Path(path).resolve()
    version = subprocess.run([str(resolved), version_arg], capture_output=True, text=True, check=True)
    return {'executable': resolved.name, 'sha256': hashlib.sha256(resolved.read_bytes()).hexdigest(),
            'version': next(line for line in version.stdout.splitlines() if line.strip())}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scowl-work', default='scowl-reproduce')
    args = parser.parse_args()
    if not args.scowl_work.replace('-', '').isalnum():
        raise SystemExit('Use a simple work directory name')
    subprocess.run([sys.executable, str(PACKAGE/'scripts/fetch_sources.py')], check=True)
    work = ROOT/'work'/args.scowl_work
    if work.exists():
        raise SystemExit('Use a fresh --scowl-work directory for archive reproducibility')
    host_bin = safe_path(ROOT, 'bin/host-tools')
    host_bin.mkdir(parents=True, exist_ok=True)
    provenance = {'system': platform.system(), 'architecture': platform.machine(),
                  'python': platform.python_version(), 'unicode': __import__('unicodedata').unidata_version,
                  'tools': {}, 'scowl_work': str(work.relative_to(ROOT)), 'commands': []}
    for name in ['find', 'grep']:
        executable = shutil.which('g'+name) or shutil.which(name)
        if executable is None:
            raise SystemExit(f'Missing {name}')
        record = tool_record(executable)
        if 'GNU' not in record['version']:
            raise SystemExit(f'GNU {name} is required; no packages will be installed')
        link = host_bin/name
        if link.is_symlink():
            link.unlink()
        link.symlink_to(Path(executable).resolve())
        provenance['tools'][name] = record
    for name in ['c++', 'make', 'perl']:
        executable = shutil.which(name)
        if executable is None:
            raise SystemExit(f'Missing host tool {name}')
        provenance['tools'][name] = tool_record(executable, '-v' if name == 'perl' else '--version')
    # Upstream make uses these existing host utilities; record their executable bytes too.
    for name in ['bash', 'sh', 'tar', 'unzip', 'gzip', 'sort', 'uniq', 'comm', 'tr', 'sed', 'awk', 'cut', 'cat']:
        executable = shutil.which(name)
        if executable is None:
            raise SystemExit(f'Missing host utility {name}')
        resolved = Path(executable).resolve()
        provenance['tools'][name] = {'executable': resolved.name,
                                     'sha256': hashlib.sha256(resolved.read_bytes()).hexdigest()}
    with tarfile.open(ROOT/f'downloads/hunspell-{HUNSPELL}.tar.gz') as archive:
        archive.extractall(ROOT/'sources', filter='data')
    with tarfile.open(ROOT/f'downloads/scowl-{SCOWL}.tar.gz') as archive:
        archive.extractall(work, filter='data')
    assert_build_tree(ROOT)
    native = ROOT/f'sources/hunspell-{HUNSPELL}/src/hunspell'
    files = ['affentry', 'affixmgr', 'csutil', 'filemgr', 'hashmgr', 'hunspell',
             'hunspelltrace', 'hunzip', 'phonet', 'replist', 'suggestmgr']
    common = ['c++', '-std=c++17', '-O2', '-DHUNSPELL_STATIC', '-I'+str(native)]
    commands = [common + [str(PACKAGE/'scripts/spell_oracle.cxx')] + [str(native/(f+'.cxx')) for f in files]
                + ['-o', str(safe_path(ROOT, 'bin/spell_oracle'))],
                ['c++', '-std=c++17', '-O2', str(native.parent/'tools/unmunch.cxx'),
                 '-o', str(safe_path(ROOT, 'bin/unmunch'))]]
    with safe_path(ROOT, 'reports/host-build-reproduce.log').open('w') as log:
        for command in commands:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
            provenance['commands'].append([arg.replace(str(PACKAGE), '<TOOL>').replace(str(ROOT), '<BUILD>') for arg in command])
    assert_build_tree(ROOT)
    environment = dict(os.environ, LC_ALL='C', LANG='C', PATH=str(host_bin)+os.pathsep+os.environ['PATH'])
    scowl = work/f'wordlist-{SCOWL}'
    with safe_path(ROOT, 'reports/scowl-build-reproduce.log').open('w') as log:
        subprocess.run(['make', '-j1'], cwd=scowl, env=environment, stdout=log,
                       stderr=subprocess.STDOUT, check=True)
    assert_build_tree(ROOT)
    for arguments, name in [(['--accents', 'keep'], 'en-scowl60-latin1.txt'), (['-f'], 'en-scowl60-selected-files.txt')]:
        with safe_path(ROOT, 'reports/'+name).open('wb') as output:
            subprocess.run(['perl', 'mk-list', *arguments, 'en_US', '60'], cwd=scowl/'scowl',
                           env=environment, stdout=output, check=True)
    provenance['commands'].extend([['make', '-j1'], ['perl', 'mk-list', '--accents', 'keep', 'en_US', '60']])
    for name in ['spell_oracle', 'unmunch']:
        provenance['tools'][name] = {'sha256': hashlib.sha256((ROOT/'bin'/name).read_bytes()).hexdigest()}
    safe_path(ROOT, 'reports/toolchain.json').write_text(json.dumps(provenance, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
