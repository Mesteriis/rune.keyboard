"""Verify tracked source bytes projected from historical role model records."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INVENTORY = 'tools/typing_experiments/historical_provenance_sources/role-model-source-inventory-v1.json'
INVENTORY_SHA = '7be033cd3fe3ebecc7405f83ecfaf5c915da0b35ab197c7e4f58310d315b5121'


def verify(root):
    root = Path(root).resolve()
    data = (root / INVENTORY).read_bytes()
    if hashlib.sha256(data).hexdigest() != INVENTORY_SHA:
        raise ValueError('ROLE_MODEL_INVENTORY_DRIFT')
    inventory = json.loads(data)
    records = inventory['records']
    if inventory['schemaVersion'] != 1 or len(records) != 14 or len({r['model'] for r in records}) != 14:
        raise ValueError('ROLE_MODEL_INVENTORY_SCOPE')
    bindings = [source for record in records for source in record['sourceBindings']]
    if len(bindings) != 322 or len({b['sha256'] for b in bindings}) != 53:
        raise ValueError('ROLE_MODEL_BINDING_SCOPE')
    checked = {}
    for source in bindings:
        path = root / source['trackedPath']
        if not path.resolve().is_relative_to(root) or path.is_symlink() or not path.is_file():
            raise ValueError('ROLE_MODEL_SOURCE_MISSING')
        if path not in checked:
            checked[path] = hashlib.sha256(path.read_bytes()).hexdigest()
        if checked[path] != source['sha256']:
            raise ValueError('ROLE_MODEL_SOURCE_DRIFT')
    return len(records), len(bindings), len(checked)


if __name__ == '__main__':
    records, bindings, sources = verify(ROOT)
    print(json.dumps({'modelRecords': records, 'sourceBindings': bindings, 'trackedFiles': sources,
                      'historicalExecutionEstablished': False, 'qualification': False}))
