"""Verify the suspended-source historical registration with its bound helpers.

This isolates historical reproduction only; live preflight and incomplete
registry coverage remain independently enforced by current code.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path('tools/typing_experiments/retrieval-suspended-source-v1')
ENTRY = 'historical-retrieval-suspended-source-v1'
HELPERS = {
    'control_ledger.py': '461a8977336cd2836f746565e7bb6fdd71ce0591c237dc78f6c65c1d72cbe470',
    'holdout_ledger.py': '466d711e261e07a6d3bc570218d3dd2d3d23f2e0c853acf999fa84ce17821cdb',
    'independent_corpus_guard.py': '2d95637da79d562ea2c807f0252451e1fd56e00611b3d0e3957b45fd793aca3d',
    'conversation_split_checks.py': '373879a4483989d8adb7f1831265ee0803502fb25660a202a6898ed74c613683',
    'source_identities.py': 'f4e8c95415c180702f15a291fc32462ac4e2bd95046706bf60f98a04b40c98c4',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('SUSPENDED_HISTORY_DUPLICATE')
        result[key] = value
    return result


def overlay_helpers(snapshot):
    base = snapshot / 'tools/typing_experiments'
    fixture = snapshot / FIXTURE
    if (base.is_symlink() or fixture.is_symlink() or not base.is_dir() or not fixture.is_dir() or
            not base.resolve().is_relative_to(snapshot.resolve()) or
            not fixture.resolve().is_relative_to(base.resolve())):
        raise ValueError('SUSPENDED_HISTORY_HELPER')
    archive = snapshot / FIXTURE / 'helper-snapshots.json'
    if archive.is_symlink() or not archive.is_file():
        raise ValueError('SUSPENDED_HISTORY_HELPER')
    data = json.loads(archive.read_bytes(), object_pairs_hook=unique_pairs)
    if not isinstance(data, dict) or set(data) != set(HELPERS):
        raise ValueError('SUSPENDED_HISTORY_HELPER')
    for name, digest in HELPERS.items():
        value = data[name]
        if not isinstance(value, str) or sha(value.encode()) != digest:
            raise ValueError('SUSPENDED_HISTORY_HELPER:' + name)
    for ledger, identity in (('control-ledger.json', ENTRY), ('holdout-ledger.json', ENTRY + '-contexts')):
        path = snapshot / 'tools/typing_experiments' / ledger
        if path.is_symlink() or not path.is_file():
            raise ValueError('SUSPENDED_HISTORY_BINDING')
        ledger_data = json.loads(path.read_bytes())
        entries = ledger_data.get('entries') if isinstance(ledger_data, dict) else None
        if not isinstance(entries, list):
            raise ValueError('SUSPENDED_HISTORY_BINDING')
        matches = [entry for entry in entries if isinstance(entry, dict) and entry.get('id') == identity]
        if len(matches) != 1 or not isinstance(matches[0].get('bindings'), dict):
            raise ValueError('SUSPENDED_HISTORY_BINDING')
        for name, digest in HELPERS.items():
            if matches[0]['bindings'].get('tools/typing_experiments/' + name) != digest:
                raise ValueError('SUSPENDED_HISTORY_BINDING:' + name)
    for name, value in data.items():
        path = snapshot / 'tools/typing_experiments' / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('SUSPENDED_HISTORY_HELPER')
        path.write_bytes(value.encode())


def verify(root):
    root = Path(root).resolve()
    with tempfile.TemporaryDirectory(prefix='rune-suspended-history-') as folder:
        snapshot = Path(folder).resolve()
        shutil.copytree(root / 'tools', snapshot / 'tools', symlinks=True,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        overlay_helpers(snapshot)
        env = os.environ.copy()
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', str(snapshot / 'tools/ci'),
                        '-p', 'test_register_retrieval_suspended_source.py', '-v'],
                       cwd=snapshot, check=True, env=env)
        subprocess.run([sys.executable, str(snapshot / 'tools/ci/register_retrieval_suspended_source.py'), '--check'],
                       cwd=snapshot, check=True, env=env)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    verify(args.root)
    print('Historical suspended-source check passed; no independent qualification.')


if __name__ == '__main__':
    main()
