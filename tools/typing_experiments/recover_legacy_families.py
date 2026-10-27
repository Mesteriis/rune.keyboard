"""Append dictionary-supported family exclusions; never guess missing lemmas."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

from holdout_ledger import keys_for, load_ledger, validate_ledger

ROOT = Path(__file__).resolve().parents[2]
ENTRY = 'public-legacy-dictionary-families-v7-v12'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def recover_rows(rows, lexicon):
    keys = set(); unresolved = []; resolved = 0
    ids = set()
    for row in rows:
        if not isinstance(row.get('id'), str) or row['id'] in ids:
            raise ValueError('FAMILY_ROW_IDENTITY')
        ids.add(row['id'])
        target = row.get('expectedSpelling')
        if target is None and row.get('cohort') == 'correct':
            target = row.get('typed')
        if not isinstance(target, str) or not target:
            raise ValueError('FAMILY_TARGET_MISSING')
        lemmas = sorted({analysis.lemma for analysis in lexicon.analyses(target)})
        if not lemmas:
            unresolved.append(row['id'])
            continue
        keys.update(keys_for([{'families': lemmas}], 'family'))
        resolved += 1
    return sorted(keys), dict(rows=len(rows), resolvedRows=resolved, unresolvedRows=sorted(unresolved))


def build(root, base, lexicon):
    root = Path(root); result = copy.deepcopy(validate_ledger(base))
    if any(e['id'] == ENTRY for e in result['entries']):
        raise ValueError('FAMILY_ALREADY_IMPORTED')
    keys = set(); counts = {}; bindings = {}
    for version in range(7, 13):
        parent = next(e for e in result['entries'] if e['id'] == f'public-spelling-v{version}')
        rows_path = next(p for p in parent['bindings'] if p.endswith('/rows.jsonl'))
        manifest_path = next(p for p in parent['bindings'] if p.endswith('/manifest.json'))
        for path in (rows_path, manifest_path):
            if sha(root / path) != parent['bindings'][path]:
                raise ValueError('FAMILY_CORPUS_IDENTITY')
            bindings[path] = parent['bindings'][path]
        rows = [json.loads(line) for line in (root / rows_path).read_text().splitlines()]
        if len(rows) != parent['rowCount']:
            raise ValueError('FAMILY_CORPUS_COUNT')
        recovered, counts[str(version)] = recover_rows(rows, lexicon)
        keys.update(recovered)
    receipt = dict(purpose='PUBLIC_DICTIONARY_FAMILY_EXCLUSIONS_NOT_QUALIFICATION',
        dictionary=lexicon.receipt(), counts=counts, modelCalls=0,
        sourceBindings={p: sha(root / p) for p in (
            'tools/morphology/ranker.py', 'tools/typing_experiments/recover_legacy_families.py')})
    # A separate family-only addendum leaves each parent's missing family axis
    # intact. Recognized subsets must never masquerade as full recovery.
    bindings.update(receipt['sourceBindings'])
    receipt_digest = hashlib.sha256(json.dumps(receipt, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    result['entries'].append(dict(id=ENTRY, usage='historical-family-exclusion',
        keys={'family': sorted(keys)}, missingAxes=[], bindings=bindings,
        recoveryReceiptSha256=receipt_digest, parentEntries=[f'public-spelling-v{v}' for v in range(7,13)],
        notes='Dictionary-only union of all analyses. Parent missing family axes remain unresolved.'))
    return validate_ledger(result), receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output directory already exists')
    sys.path.insert(0, str(ROOT / 'tools/morphology'))
    from ranker import PymorphyLexicon
    ledger, receipt = build(ROOT, load_ledger(args.base), PymorphyLexicon(cache_size=16384))
    args.output.mkdir(parents=True, exist_ok=False)
    for name, value in (('ledger.json', ledger), ('receipt.json', receipt)):
        (args.output / name).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps(dict(families=len(ledger['entries'][-1]['keys']['family']),
        unresolvedRows=sum(len(v['unresolvedRows']) for v in receipt['counts'].values()), coverageComplete=False)))


if __name__ == '__main__':
    main()
