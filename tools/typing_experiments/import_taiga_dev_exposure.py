"""Quarantine normalized sentences from the inspected public Taiga dev file."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import unicodedata

from holdout_ledger import _digest, validate_ledger

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / 'tools/typing_experiments/public_sources/ud-taiga-2.18-dev/source-lock.json'
ENTRY = 'public-ud-russian-taiga-2.18-dev-exposure'


def sentence_keys(data, expected_hash):
    if hashlib.sha256(data).hexdigest() != expected_hash: raise ValueError('TAIGA_SOURCE_HASH')
    keys, ids = set(), set()
    identity = sentence = None
    for line in data.decode('utf-8').splitlines() + ['']:
        if line.startswith('# sent_id = '):
            if identity is not None: raise ValueError('TAIGA_SENTENCE_INCOMPLETE')
            identity = line.removeprefix('# sent_id = ')
            if not identity or identity in ids: raise ValueError('TAIGA_SENTENCE_ID')
            ids.add(identity)
        elif line.startswith('# text = '):
            if identity is None or sentence is not None: raise ValueError('TAIGA_SENTENCE_TEXT')
            sentence = line.removeprefix('# text = ')
        elif not line and identity is not None:
            if not sentence or not sentence.strip(): raise ValueError('TAIGA_SENTENCE_INCOMPLETE')
            normalized = ' '.join(unicodedata.normalize('NFC', sentence).casefold().split())
            digest = hashlib.sha256(normalized.encode()).hexdigest()
            keys.add(_digest('sentence', ['tatoeba-full-sentence-normalized-v1', digest]))
            identity = sentence = None
    if not ids: raise ValueError('TAIGA_EMPTY')
    return sorted(keys), len(ids)


def build(ledger, keys, count, bindings):
    result = copy.deepcopy(validate_ledger(ledger))
    if any(e['id'] == ENTRY for e in result['entries']): raise ValueError('TAIGA_ALREADY_IMPORTED')
    prior = {k for entry in result['entries'] for k in entry['keys'].get('sentence', [])}
    result['entries'].append({'id': ENTRY, 'usage': 'historical-exclusion', 'keys': {'sentence': keys},
        'missingAxes': ['article', 'family', 'context'], 'bindings': bindings, 'rowCount': count,
        'sourceRepository': 'ud-russian-taiga',
        'notes': 'Inspected dev partition; sentence-only exclusion, document identity not established.'})
    return validate_ledger(result), len(prior.intersection(keys))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    lock = json.loads(LOCK.read_text())
    keys, count = sentence_keys(args.source.read_bytes(), lock['sha256'])
    ledger = json.loads((ROOT / 'tools/typing_experiments/holdout-ledger.json').read_text())
    bindings = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (LOCK, Path(__file__), ROOT / 'tools/typing_experiments/holdout_ledger.py')}
    result, overlaps = build(ledger, keys, count, bindings)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, sort_keys=True, indent=2); stream.write('\n')
    print(json.dumps({'rows': count, 'uniqueSentenceKeys': len(keys), 'priorSentenceOverlap': overlaps}))


if __name__ == '__main__': main()
