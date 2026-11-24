"""Fill control-ledger gaps for byte-exact recovered historical corpora."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

import control_ledger
from historical_control_projection import project_corpus_entries


ROOT = Path(__file__).resolve().parents[2]
EXPERIMENTS = Path('tools/typing_experiments')
SOURCE_PROOFS = EXPERIMENTS / 'historical_provenance_sources/v6-inputs'
JOINT_PROOF = SOURCE_PROOFS / 'joint-diagnostic-recovery.json'
PREFIX = 'recovered-historical-corpus-'
CORPORA = {
    'supervised-v2': (
        'tatoeba-cc0-verified/supervised-v2',
        SOURCE_PROOFS / 'tatoeba-supervised-v2-recovery.json',
        ('files',), ('train', 'calibration', 'holdout'), 'build/conversation-supervised-20261026/corpus-v2', 'tatoeba',
    ),
    'context-feature': (
        'tatoeba-cc0-verified/conversation-corpus',
        SOURCE_PROOFS / 'tatoeba-cc0-context-feature-recovery.json',
        ('files',), ('calibration', 'holdout'), 'build/context-feature-ranker-20261026/conversation-corpus', 'tatoeba',
    ),
    'available-clean-v6': (
        'final-available-v6', Path('docs/acceptance/2026-11-24-q6-final-v6-recovery.json'),
        ('originalFiles',), ('calibration', 'holdout'), 'build/right-context-available-clean-v6-20261027/corpus', None,
    ),
    'joint-original': (
        'joint-diagnostic-replay/corpus', JOINT_PROOF, ('corpora', 'corpus', 'files'),
        ('train', 'calibration', 'holdout'), 'build/joint-correction-20261025/corpus', None,
    ),
    'joint-followup': (
        'joint-diagnostic-replay/followup-corpus', JOINT_PROOF, ('corpora', 'followup-corpus', 'files'),
        ('calibration', 'holdout'), 'build/joint-correction-20261025/followup-corpus', None,
    ),
    'joint-followup-v3': (
        'joint-diagnostic-replay/followup-corpus-v3', JOINT_PROOF, ('corpora', 'followup-corpus-v3', 'files'),
        ('calibration', 'holdout'), 'build/joint-correction-20261025/followup-corpus-v3', None,
    ),
    'diagnostic-rare-ranking': (
        'joint-diagnostic-replay/diagnostic-rare-ranking', JOINT_PROOF,
        ('corpora', 'diagnostic-rare-ranking', 'files'),
        ('calibration', 'holdout'), 'build/diagnostic-rare-ranking/fresh-corpus', None,
    ),
}


def verified_rows(directory, expected):
    for name, digest in expected.items():
        raw = (directory / name).read_bytes()
        if sha256(raw).hexdigest() != digest:
            raise ValueError('RECOVERED_CONTROL_INPUT:' + name)
        yield from map(json.loads, raw.splitlines())


def missing_entries(projected, ledger):
    existing = ledger['entries']
    ids = {entry['id'] for entry in existing}
    covered_surfaces = {key for entry in existing for key in entry.get('surfaceKeys', [])}
    covered_articles = {key for entry in existing for key in entry.get('articleKeys', [])}
    additions = []
    for entry in projected:
        kind = entry['kind']
        covered_contexts = {key for current in existing if current['kind'] == kind for key in current['keys']}
        contexts = sorted(set(entry['keys']) - covered_contexts)
        surfaces = sorted(set(entry.get('surfaceKeys', [])) - covered_surfaces)
        articles = sorted(set(entry.get('articleKeys', [])) - covered_articles)
        if not (contexts or surfaces or articles):
            continue
        if entry['id'] in ids:
            raise ValueError('RECOVERED_CONTROL_REGISTRY_DRIFT:' + entry['id'])
        delta = {key: value for key, value in entry.items() if key not in ('surfaceKeys', 'articleKeys')}
        # A control entry needs contexts. Reuse verified ones if only surfaces are missing.
        delta['keys'] = contexts or entry['keys']
        if surfaces:
            delta['surfaceKeys'] = surfaces
        if articles:
            delta['articleKeys'] = articles
            delta['rowCount'] = len(articles)
        additions.append(delta)
    return additions


def reconcile(input_root, ledger, write):
    report = {}
    for name, (folder, proof, fields, splits, original, source_repository) in CORPORA.items():
        evidence = (ROOT / proof).read_bytes()
        files = json.loads(evidence)
        for field in fields:
            files = files[field]
        expected = {key: value['sha256'] if isinstance(value, dict) else value
                    for key, value in files.items() if key.endswith('.jsonl')}
        if set(expected) != {split + '.jsonl' for split in splits}:
            raise ValueError('RECOVERED_CONTROL_SPLITS:' + name)
        bindings = {proof.as_posix(): sha256(evidence).hexdigest()}
        bindings.update({f'{original}/{key}': value for key, value in expected.items()})
        rows = verified_rows(input_root / folder, expected)
        entries = project_corpus_entries(rows, bindings, PREFIX + name + '-', 'ru', source_repository)
        additions = missing_entries(entries, ledger)
        if additions and not write:
            raise ValueError('RECOVERED_CONTROL_COVERAGE:' + name)
        ledger['entries'].extend(additions)
        report[name] = {
            'rows': sum(entry['rowCount'] for entry in entries if entry['kind'] != 'source'),
            'entriesAdded': len(additions),
            'contextKeysAdded': sum(len(entry['keys']) for entry in additions),
            'surfaceKeysAdded': sum(len(entry.get('surfaceKeys', [])) for entry in additions),
            'articleKeysAdded': sum(len(entry.get('articleKeys', [])) for entry in additions),
        }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-root', type=Path, required=True)
    parser.add_argument('--ledger', type=Path, default=ROOT / EXPERIMENTS / 'control-ledger.json')
    parser.add_argument('--output', type=Path, help='Fresh path for the updated ledger')
    args = parser.parse_args()
    ledger = control_ledger.load(args.ledger)
    report = reconcile(args.input_root, ledger, args.output is not None)
    if args.output:
        control_ledger.validate(ledger)
        with args.output.open('x', encoding='utf-8') as output:
            output.write(json.dumps(ledger, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
