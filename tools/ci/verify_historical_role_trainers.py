"""Verify retained pre-role training scripts without executing them."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = (
    '94d490825dcef94f7bb930a6608f2e33624f16f77fd79b636643b7e0f125ca52',
    '2031f0465c629a8f34a123d67ff9cc059fba9744967c8992b8d2dd3aef6b8643',
    '39ad6970c6af2464f7d16327064409570a060a6e9ea5cd146c2ad8dfb354853b',
)


def verify(root):
    for digest in SOURCES:
        path = Path(root) / 'tools/typing_experiments/frozen_sources' / ('role_train_' + digest[:16] + '.py')
        if path.is_symlink() or not path.is_file():
            raise ValueError('HISTORICAL_ROLE_TRAINER_MISSING')
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError('HISTORICAL_ROLE_TRAINER_DRIFT')
        compile(raw, str(path), 'exec')
    return len(SOURCES)


if __name__ == '__main__':
    print(json.dumps({'historicalTrainers': verify(ROOT), 'qualification': False}))
