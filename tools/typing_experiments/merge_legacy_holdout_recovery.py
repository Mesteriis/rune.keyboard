"""Add verified historical source identities without removing prior exclusions."""
import argparse
import copy
import json
from pathlib import Path

from holdout_ledger import keys_for, load_ledger, validate_ledger
from recover_legacy_holdout import ORIGINAL, ROOT, sha


def enrich_entry(entry, receipt, records, selections, bindings):
    if any(path in entry['bindings'] and entry['bindings'][path] != digest for path, digest in bindings.items()):
        raise ValueError('LEDGER_RECOVERY_BINDING_CHANGE')
    if (receipt.get('allRowsRecovered') is not True or receipt.get('modelCalls') != 0
            or receipt.get('missingRows') != [] or receipt.get('source') != entry['publicSource']
            or receipt.get('sourceGeneratorSha256') != entry['generatorBindings'][ORIGINAL]
            or receipt.get('corpusRows') != entry['rowCount']
            or receipt.get('recoveredRows') != len(selections)
            or receipt.get('matchedOccurrences') != len(records)
            or len(selections) != entry['rowCount']):
        raise ValueError('LEDGER_RECOVERY_RECEIPT')
    if not records or {r['id'] for r in records} != set(selections):
        raise ValueError('LEDGER_RECOVERY_COVERAGE')
    if any(r['selectionHash'] != selections[r['id']] for r in records):
        raise ValueError('LEDGER_RECOVERY_SELECTION')
    result = copy.deepcopy(entry)
    for axis in ('article', 'sentence'):
        recovered = keys_for(records, axis)
        result['keys'][axis] = sorted(set(result['keys'].get(axis, [])) | recovered)
    result['missingAxes'] = [axis for axis in result['missingAxes'] if axis not in ('article', 'sentence')]
    result['bindings'].update(bindings)
    result['notes'] = ('All matching source articles/occurrences are retained. Sentence keys use the '
        'current right-context window projection. Canonical family recovery remains pending.')
    result['recoveryCounts'] = dict(sourceRows=len(selections), occurrences=len(records),
                                   articles=len({r['article'] for r in records}))
    return result


def build_enriched_ledger(root, recovery_root, base):
    root = Path(root).resolve(); recovery_root = Path(recovery_root).resolve()
    result = copy.deepcopy(validate_ledger(base))
    for entry in result['entries']:
        if not entry['id'].startswith('public-spelling-v'):
            continue
        version = int(entry['id'].removeprefix('public-spelling-v'))
        directory = recovery_root / f'v{version}'
        receipt_path = directory / 'receipt.json'; identities_path = directory / 'identities.jsonl'
        receipt = json.loads(receipt_path.read_text())
        if (receipt['version'] != version or sha(identities_path) != receipt['identitiesSha256']
                or sha(root / 'tools/typing_experiments/recover_legacy_holdout.py') != receipt['recoverySourceSha256']):
            raise ValueError('LEDGER_RECOVERY_IDENTITY')
        corpus_path = next(p for p in entry['bindings'] if p.endswith('/rows.jsonl'))
        manifest_path = next(p for p in entry['bindings'] if p.endswith('/manifest.json'))
        if (sha(root / corpus_path) != entry['bindings'][corpus_path] or sha(root / corpus_path) != receipt['corpusSha256']
                or sha(root / manifest_path) != entry['bindings'][manifest_path]
                or sha(root / manifest_path) != receipt['corpusManifestSha256']):
            raise ValueError('LEDGER_RECOVERY_CORPUS')
        rows = [json.loads(line) for line in (root / corpus_path).read_text().splitlines()]
        selections = {r['id']: r['template'].removeprefix('holdout-wikipedia-') for r in rows}
        if len(selections) != len(rows):
            raise ValueError('LEDGER_RECOVERY_ROW_IDS')
        records = [json.loads(line) for line in identities_path.read_text().splitlines()]
        enriched = enrich_entry(entry, receipt, records, selections,
            {str(p.relative_to(root)): sha(p) for p in (receipt_path, identities_path)})
        entry.clear(); entry.update(enriched)
    # Only this completed migration item is removed. Overall coverage stays false.
    result['coverage']['pending'] = [task for task in result['coverage']['pending']
        if task != 'Recover historical article and source-sentence identities for spelling v7-v12.']
    result['coverage']['complete'] = False
    historical_articles = {key for entry in result['entries']
        if entry['id'].startswith('public-spelling-v') for key in entry['keys']['article']}
    result['historicalArticleOverlap'] = {
        'status': 'NOT_INDEPENDENT_OF_HISTORICAL_SPELLING',
        'historicalArticles': len(historical_articles),
        'entries': {entry['id']: len(historical_articles & set(entry['keys'].get('article', [])))
            for entry in result['entries'] if entry['id'].startswith('public-right-context-available-')},
        'note': 'Existing corpora and scores are unchanged; these corpora cannot certify article-disjoint freshness.',
    }
    return validate_ledger(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--recovery-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    enriched = build_enriched_ledger(args.root, args.recovery_root.resolve(), load_ledger(args.base))
    with args.output.open('x') as stream:
        stream.write(json.dumps(enriched, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps(dict(entries=len(enriched['entries']), coverageComplete=False, sha256=sha(args.output))))


if __name__ == '__main__':
    main()
