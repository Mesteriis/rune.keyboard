"""Count affected historical v6 rows without emitting corpus text or row identifiers."""

import argparse
from collections import Counter
import json
from pathlib import Path

from audit_available_v6_family_exposure import LEDGER, MANIFEST, PARTS, digest
from holdout_ledger import keys_for, validate_ledger
from import_recovered_v6_history import PARENT_ENTRY


TARGET = 'public-right-context-available-v6-'
NEIGHBOR = 'historical-neighbor-recovery-public-v1'


def count_rows(rows, blocked):
    rows = [(row, article) for row, article in rows if article in blocked]
    return {'articles': len({article for _, article in rows}),
            'contexts': len({row['contextHash'] for row, _ in rows}),
            'rows': len(rows),
            'groups': dict(Counter(row['group'] for row, _ in rows))}


def partition_report(part, raw, expected, target_keys, scopes):
    if digest(raw) != expected:
        raise ValueError('V6_ARTICLE_ROWS_INPUT:' + part)
    rows = []
    for row in map(json.loads, raw.splitlines()):
        if row['part'] != part or row['split'] != part:
            raise ValueError('V6_ARTICLE_ROWS_PARTITION:' + part)
        article, = keys_for([row], 'article')
        rows.append((row, article))
    if {article for _, article in rows} != target_keys:
        raise ValueError('V6_ARTICLE_ROWS_LEDGER_BINDING:' + part)
    return {name: count_rows(rows, scope) for name, scope in scopes.items()}


def audit(corpus, ledger_path=LEDGER):
    manifest_raw = MANIFEST.read_bytes()
    manifest = json.loads(manifest_raw)
    ledger_raw = Path(ledger_path).read_bytes()
    ledger = validate_ledger(json.loads(ledger_raw))
    entries = {entry['id']: set(entry['keys'].get('article', [])) for entry in ledger['entries']}
    spelling = set().union(*(entries[name] for name in ledger['historicalArticleOverlap']['scopeEntries']))
    neighbor = entries[NEIGHBOR]
    other = set().union(*(values for name, values in entries.items()
                         if name != PARENT_ENTRY and not name.startswith(TARGET)))
    scopes = {'spelling': spelling, 'neighbor': neighbor, 'spellingOrNeighbor': spelling | neighbor,
              'otherRegistered': other}
    result = {'schema': 1, 'auditSourceSha256': digest(Path(__file__).read_bytes()),
              'manifestSha256': digest(manifest_raw), 'ledgerSha256': digest(ledger_raw),
              'ledgerEntries': len(entries), 'ledgerCoverageComplete': ledger['coverage']['complete'],
              'rowsSha256': {}, 'partitions': {}, 'modelCalls': 0, 'independentQualification': False}
    for part in PARTS:
        name = part + '.jsonl'
        expected = manifest['files'][name]
        report = partition_report(part, (corpus / name).read_bytes(), expected, entries[TARGET + part], scopes)
        result['rowsSha256'][part] = expected
        result['partitions'][part] = report
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', required=True, type=Path, help='Directory with both restored JSONL partitions')
    args = parser.parse_args()
    print(json.dumps(audit(args.corpus), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
