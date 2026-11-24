"""Run historical text-boundary verifiers with their archived helper versions.

This verifies historical disclosures only; it cannot certify new holdouts.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = Path('tools/typing_experiments/retrieval-history-v1/sources')
HELPERS = {
    'tools/typing_experiments/control_ledger.py':
        '2647503526a78fad3c31c27ec3739b9f3468a428072716f43c7b73c489872674',
    'tools/typing_experiments/independent_corpus_guard.py':
        'f8bf944977321d8f2864308a8b822a39c11e47f23b87793e28bf298f42de4ce6',
}


EWT_SOURCE = 'historical-english-ewt-control-source-v1'


def project_control_ledger(path):
    """Hide only the checked later source-only entry from the old schema."""
    ledger = json.loads(path.read_bytes())
    entries = ledger.get('entries')
    if not isinstance(entries, list):
        raise ValueError('HISTORICAL_CONTROL_SCHEMA')
    selected = [e for e in entries if isinstance(e, dict) and e.get('id') == EWT_SOURCE]
    if not selected:
        return False
    if len(selected) != 1:
        raise ValueError('HISTORICAL_CONTROL_SOURCE')
    item = selected[0]
    keys = item.get('articleKeys')
    if (item.get('kind') != 'source' or item.get('language') != 'en' or
            item.get('rowCount') != 16622 or item.get('keys') != [] or
            not isinstance(keys, list) or len(keys) != 1174 or keys != sorted(set(keys))):
        raise ValueError('HISTORICAL_CONTROL_SOURCE')
    ledger['entries'] = [e for e in entries if e is not item]
    path.write_text(json.dumps(ledger, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    return True


@contextmanager
def historical_snapshot(root):
    root = Path(root).resolve()
    with tempfile.TemporaryDirectory(prefix='rune-text-history-') as folder:
        snapshot = Path(folder).resolve()
        shutil.copytree(root / 'tools', snapshot / 'tools', symlinks=True,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        shutil.copytree(root / 'app/src/main', snapshot / 'app/src/main', symlinks=True)
        for name, digest in HELPERS.items():
            raw = (snapshot / ARCHIVE / (digest + '.txt')).read_bytes()
            if hashlib.sha256(raw).hexdigest() != digest:
                raise ValueError('HISTORICAL_HELPER_MISMATCH:' + name)
            (snapshot / name).write_bytes(raw)
        if project_control_ledger(snapshot / 'tools/typing_experiments/control-ledger.json'):
            # Verify the complete live source-only entry before excluding it from
            # the archived schema's temporary view. Never modify the live ledger.
            subprocess.run([sys.executable, str(root / 'tools/ci/register_ewt_control_source.py'), '--check'],
                           cwd=root, check=True)
        yield snapshot


def verify(root):
    with historical_snapshot(root) as snapshot:
        for suffix in ('shared', 'all'):
            test = 'test_register_' + suffix + '_text_boundaries.py'
            subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s',
                            str(snapshot / 'tools/ci'), '-p', test, '-v'],
                           cwd=snapshot, check=True)
            subprocess.run([sys.executable, str(snapshot / 'tools/ci' /
                           ('register_' + suffix + '_text_boundaries.py')), '--check'],
                           cwd=snapshot, check=True)

        subprocess.run([sys.executable, str(snapshot / 'tools/typing_experiments' /
                       'register_named_regressions.py'), '--check'],
                       cwd=snapshot, check=True)
        # This historical ledger entry binds the same archived guard bytes.
        # Keep its verifier independent of future live admission changes.
        subprocess.run([sys.executable, str(snapshot / 'tools/typing_experiments' /
                       'import_neighbor_article_segments.py'), '--check'],
                       cwd=snapshot, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT,
                        help='source tree containing tools/; defaults to this checkout')
    args = parser.parse_args()
    verify(args.root)
    print('Historical text boundary checks passed; no independent qualification.')


if __name__ == '__main__':
    main()
