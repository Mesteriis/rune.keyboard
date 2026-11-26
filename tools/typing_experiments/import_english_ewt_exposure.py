"""Register the complete disclosed EWT source by document and normalized sentence."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import unicodedata

from holdout_ledger import keys_for, validate_ledger

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / 'tools/typing_experiments/public_sources/ud-ewt-2.18/source-lock.json'
ENTRY = 'public-ud-english-ewt-2.18-exposure'


def rows_from_sources(data_by_name, hashes):
    if set(data_by_name) != set(hashes) or len(hashes) != 3: raise ValueError('EWT_SOURCE_SET')
    rows, identities, documents = [], set(), set()
    for name in sorted(hashes):
        data = data_by_name[name]
        if hashlib.sha256(data).hexdigest() != hashes[name]: raise ValueError('EWT_SOURCE_HASH')
        document = None; identity = None; sentence = None
        for line in data.decode('utf-8').splitlines() + ['']:
            if line.startswith('# newdoc id = '):
                document = line.removeprefix('# newdoc id = ')
                if not document: raise ValueError('EWT_DOCUMENT')
                documents.add(document)
            elif line.startswith('# sent_id = '):
                if identity is not None: raise ValueError('EWT_SENTENCE_INCOMPLETE')
                identity = line.removeprefix('# sent_id = ')
                if not identity or identity in identities: raise ValueError('EWT_SENTENCE_ID')
                identities.add(identity)
            elif line.startswith('# text = '):
                if identity is None or sentence is not None: raise ValueError('EWT_SENTENCE_TEXT')
                sentence = line.removeprefix('# text = ')
            elif line == '' and identity is not None:
                if document is None or not sentence or not sentence.strip(): raise ValueError('EWT_SENTENCE_INCOMPLETE')
                normalized = ' '.join(unicodedata.normalize('NFC', sentence).casefold().split())
                rows.append(dict(sourceRepository='ud-english-ewt', language='en', article='ewt:' + document,
                                 sentenceHash=hashlib.sha256(normalized.encode('utf-8')).hexdigest()))
                identity = None; sentence = None
    if not rows or not documents: raise ValueError('EWT_EMPTY')
    return rows


def build(ledger, rows, bindings):
    result = copy.deepcopy(validate_ledger(ledger))
    if any(item['id'] == ENTRY for item in result['entries']): raise ValueError('EWT_ALREADY_IMPORTED')
    keys = {kind: sorted(keys_for(rows, kind)) for kind in ('article', 'sentence')}
    prior = {key for entry in result['entries'] for key in entry['keys'].get('sentence', [])}
    overlaps = len(set(keys['sentence']) & prior)
    result['entries'].append(dict(id=ENTRY, usage='historical-source-exclusion', keys=keys,
        missingAxes=[], bindings=bindings, rowCount=len(rows), sourceRepository='ud-english-ewt',
        notes='All pinned EWT partitions quarantined after training-source screen; no fresh holdout claim.'))
    return validate_ledger(result), overlaps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    lock = json.loads(LOCK.read_text())
    hashes = lock['files']
    data = {name: (args.source_directory / name).read_bytes() for name in hashes}
    rows = rows_from_sources(data, hashes)
    ledger = json.loads((ROOT / 'tools/typing_experiments/holdout-ledger.json').read_text())
    bindings = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                (LOCK, Path(__file__), ROOT / 'tools/typing_experiments/source_identities.py',
                 ROOT / 'tools/typing_experiments/holdout_ledger.py')}
    result, overlaps = build(ledger, rows, bindings)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, sort_keys=True, indent=2); stream.write('\n')
    print(json.dumps({'rows': len(rows), 'priorSentenceOverlap': overlaps,
                      'documents': len(keys_for(rows, 'article'))}, sort_keys=True))


if __name__ == '__main__': main()
