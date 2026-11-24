"""Verify restored historical feature source bytes against their receipts."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPECS = (
    ('right_context_role_features_2442a38501946f6f.py',
     'right_context_role_features.py',
     '2442a38501946f6fcaad293a99b11d0ad785123efb1fe207b03beb5332a841d0',
     '2026-10-27-late-authored-history-evidence.json'),
    ('right_context_left_sequence_features_82aeb37a82f7ac32.py',
     'right_context_left_sequence_features.py',
     '82aeb37a82f7ac32aafd2f5f08eab36469ad2605b169943359db9a069726788e',
     '2026-10-27-auxiliary-authored-history-evidence.json'),
)


def verify(root):
    root = Path(root)
    for archived, original, expected, receipt in SPECS:
        path = root / 'tools/typing_experiments/frozen_sources' / archived
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('RECOVERED_FEATURE_SOURCE_IDENTITY')
        facts = json.loads((root / 'docs/acceptance' / receipt).read_bytes())['receipt']['unavailableHistoricalSources']
        original_path = 'tools/typing_experiments/' + original
        if not any(item.get('path') == original_path and item.get('sha256') == expected for item in facts):
            raise ValueError('RECOVERED_FEATURE_RECEIPT_IDENTITY')
        compile(path.read_bytes(), str(path), 'exec')
    return len(SPECS)


if __name__ == '__main__':
    print(json.dumps({'recoveredSources': verify(ROOT), 'modelExecutionEstablished': False}))
