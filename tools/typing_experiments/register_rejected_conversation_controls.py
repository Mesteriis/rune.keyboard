"""Register control exclusions from the hash-verified rejected conversation corpus."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

import control_ledger
from historical_control_projection import project_corpus_entries


ROOT = Path(__file__).resolve().parents[2]
EXPERIMENTS = Path('tools/typing_experiments')
PROOF = Path('docs/acceptance/2026-10-27-unmanifested-conversation-audit-evidence.json')
BUILDER = EXPERIMENTS / 'historical_provenance_sources/conversation_supervised_v1_preparer.py'
BUILDER_SHA = '1a7548ffee3a16956cb2cf199e413cd1384b74955254a9f0cfda88c450168083'
ORIGINAL = Path('build/conversation-supervised-20261026/corpus')
PARTS = ('train', 'calibration', 'holdout')
ENTRY_PREFIX = 'rejected-supervised-conversation-v1-'


def verified_rows(corpus, expected):
    if (corpus / 'manifest.json').exists():
        raise ValueError('REJECTED_CONVERSATION_MANIFEST')
    for part in PARTS:
        name = part + '.jsonl'
        raw = (corpus / name).read_bytes()
        if sha256(raw).hexdigest() != expected[(ORIGINAL / name).as_posix()]:
            raise ValueError('REJECTED_CONVERSATION_ROWS:' + part)
        yield from map(json.loads, raw.splitlines())


def project(rows, bindings):
    return project_corpus_entries(rows, bindings, ENTRY_PREFIX, 'ru', 'tatoeba')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--ledger', type=Path, default=ROOT / EXPERIMENTS / 'control-ledger.json')
    parser.add_argument('--output', type=Path, help='Fresh output path for the updated ledger')
    args = parser.parse_args()
    proof = (ROOT / PROOF).read_bytes()
    expected = json.loads(proof)['after']['bindings']
    if sha256((ROOT / BUILDER).read_bytes()).hexdigest() != BUILDER_SHA:
        raise ValueError('REJECTED_CONVERSATION_BUILDER')
    bindings = {PROOF.as_posix(): sha256(proof).hexdigest(), BUILDER.as_posix(): BUILDER_SHA}
    bindings.update({key: value for key, value in expected.items() if key.startswith(ORIGINAL.as_posix() + '/')})
    entries = project(verified_rows(args.corpus, expected), bindings)
    ledger = control_ledger.load(args.ledger)
    registered = [entry for entry in ledger['entries'] if entry['id'].startswith(ENTRY_PREFIX)]
    if args.output:
        if registered:
            raise ValueError('REJECTED_CONVERSATION_ALREADY_REGISTERED')
        ledger['entries'].extend(entries)
        control_ledger.validate(ledger)
        with args.output.open('x', encoding='utf-8') as output:
            output.write(json.dumps(ledger, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    elif registered != entries:
        raise ValueError('REJECTED_CONVERSATION_REGISTRY_DRIFT')
    print(json.dumps({entry['kind']: {
        'rows': entry['rowCount'], 'contexts': len(entry['keys']),
        'surfaces': len(entry.get('surfaceKeys', [])), 'articles': len(entry.get('articleKeys', [])),
    } for entry in entries}, sort_keys=True))


if __name__ == '__main__':
    main()
