"""Check the tracked direct source projection for two historical corpora."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = 'tools/typing_experiments/frozen_sources/recovered-feature-source-closure.json'
SNAPSHOT_SHA = '255d7c327ee810a0520661d9d4add5f254c74758db1825049451e4eeb5375910'


def verify(root):
    root = Path(root).resolve()
    raw = (root / SNAPSHOT).read_bytes()
    if hashlib.sha256(raw).hexdigest() != SNAPSHOT_SHA:
        raise ValueError('FEATURE_CLOSURE_SNAPSHOT')
    snapshot = json.loads(raw)
    entries = snapshot['corpora']
    if snapshot['schemaVersion'] != 1 or [x['corpus'] for x in entries] != ['role-v4', 'left-sequence-v1']:
        raise ValueError('FEATURE_CLOSURE_SCHEMA')
    for corpus, count in zip(entries, (4, 7)):
        receipt = json.loads((root / 'docs/acceptance' / corpus['receipt']).read_bytes())['receipt']
        if receipt['bindings'].get(corpus['manifestReceiptPath']) != corpus['manifestSha256']:
            raise ValueError('FEATURE_CLOSURE_PARENT')
        if len(corpus['sources']) != count or len({s['originalName'] for s in corpus['sources']}) != count:
            raise ValueError('FEATURE_CLOSURE_SCOPE')
        for source in corpus['sources']:
            path = root / source['trackedPath']
            if (not path.resolve().is_relative_to(root) or path.is_symlink() or not path.is_file() or
                    hashlib.sha256(path.read_bytes()).hexdigest() != source['sha256']):
                raise ValueError('FEATURE_CLOSURE_SOURCE')
    return sum(len(x['sources']) for x in entries)


if __name__ == '__main__':
    print(json.dumps({'directSourceBindings': verify(ROOT), 'transitiveClosureEstablished': False}))
