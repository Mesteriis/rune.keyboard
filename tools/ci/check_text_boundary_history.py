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
CONTROLLER = ('app/src/main/java/io/github/mesteriis/rune/keyboard/'
              'smarttyping/session/SessionTextContext.kt')
HELPERS = {
    CONTROLLER: '8e6f6c82c113a0acfa4286a9de46518de732d408854da33c415740d504241643',
    'tools/ci/historical_model_fixtures.py':
        '450d752d42cbc4a1776909e4529e769a4dcc19a41462b848e68128f22edaa594',
    'tools/ci/historical_model_sources.py':
        '8e47cb5ee459ca4d4d415c32f69cb29cf9aa0cc6606d4fd4d068f0d7dff52a2a',
    'tools/typing_experiments/control_ledger.py':
        '2647503526a78fad3c31c27ec3739b9f3468a428072716f43c7b73c489872674',
    'tools/typing_experiments/independent_corpus_guard.py':
        'f8bf944977321d8f2864308a8b822a39c11e47f23b87793e28bf298f42de4ce6',
}


EWT_SOURCE = 'historical-english-ewt-control-source-v1'
VERIFIERS = ('shared_text_boundaries', 'all_text_boundaries',
             'refinement_text_boundaries', 'epoch_text_boundaries', 'truncated_text_sources')


def archived_path(name, digest):
    if name == CONTROLLER:
        return Path('tools/ci/historical-model-sources-v1/sources') / (digest + '.kt')
    return ARCHIVE / (digest + '.txt')


def project_control_ledger(path):
    """Project source-only entries out of the archived control schema."""
    ledger = json.loads(path.read_bytes())
    entries = ledger.get('entries')
    if not isinstance(entries, list):
        raise ValueError('HISTORICAL_CONTROL_SCHEMA')
    ewt = [e for e in entries if isinstance(e, dict) and e.get('id') == EWT_SOURCE]
    if ewt and (len(ewt) != 1 or ewt[0].get('kind') != 'source'):
        raise ValueError('HISTORICAL_CONTROL_SOURCE')
    sources = [e for e in entries if isinstance(e, dict) and e.get('kind') == 'source']
    if sources:
        ledger['entries'] = [e for e in entries if not isinstance(e, dict) or e.get('kind') != 'source']
        path.write_text(json.dumps(ledger, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    return {e.get('id') for e in sources}


@contextmanager
def historical_snapshot(root):
    root = Path(root).resolve()
    with tempfile.TemporaryDirectory(prefix='rune-text-history-') as folder:
        snapshot = Path(folder).resolve()
        shutil.copytree(root / 'tools', snapshot / 'tools', symlinks=True,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        shutil.copytree(root / 'app/src/main', snapshot / 'app/src/main', symlinks=True)
        for name, digest in HELPERS.items():
            raw = (snapshot / archived_path(name, digest)).read_bytes()
            if hashlib.sha256(raw).hexdigest() != digest:
                raise ValueError('HISTORICAL_HELPER_MISMATCH:' + name)
            (snapshot / name).write_bytes(raw)
        omitted = project_control_ledger(snapshot / 'tools/typing_experiments/control-ledger.json')
        if omitted:
            # The old schema predates article-only rows. Validate the full live
            # ledger before using the projection for historical checks only.
            subprocess.run([sys.executable, str(root / 'tools/typing_experiments/control_ledger.py'),
                            '--validate-only'], cwd=root, check=True)
        if EWT_SOURCE in omitted:
            subprocess.run([sys.executable, str(root / 'tools/ci/register_ewt_control_source.py'), '--check'],
                           cwd=root, check=True)
        yield snapshot


def verify(root):
    with historical_snapshot(root) as snapshot:
        for verifier in VERIFIERS:
            test = 'test_register_' + verifier + '.py'
            subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s',
                            str(snapshot / 'tools/ci'), '-p', test, '-v'],
                           cwd=snapshot, check=True)
            subprocess.run([sys.executable, str(snapshot / 'tools/ci' /
                           ('register_' + verifier + '.py')), '--check'],
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
