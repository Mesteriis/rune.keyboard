"""Audit authored typo targets against existing Q7 family exclusions."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import import_q7_regression_families as q7
from holdout_ledger import keys_for, load_ledger

ROOT = Path(__file__).resolve().parents[2]
ENTRY = q7.PREFIX + 'original-v2'


def audit(rows, lexicon, existing):
    counts = Counter(); unknown_surfaces = set(); with_known_target = set(); missing = set(); identities = set()
    for row in rows:
        identity = row.get('id')
        if not isinstance(identity, str) or not identity or identity in identities: raise ValueError('Q7_TYPO_ROW_ID')
        identities.add(identity)
        if row.get('language') != 'ru' or row.get('cohort') not in ('typo', 'correct'):
            raise ValueError('Q7_TYPO_ROW_SCOPE')
        if row['cohort'] != 'typo': continue
        if not isinstance(row.get('typed'), str) or not isinstance(row.get('expectedSpelling'), str):
            raise ValueError('Q7_TYPO_TARGET')
        typed = q7.lexical_surfaces([row['typed']]); target = q7.lexical_surfaces([row['expectedSpelling']])
        if len(typed) != 1 or len(target) != 1: raise ValueError('Q7_TYPO_NONLEXICAL')
        if lexicon.analyses(typed[0]): continue
        counts['unknownTypoRows'] += 1; unknown_surfaces.add(typed[0])
        analyses = lexicon.analyses(target[0])
        if not analyses:
            counts['unknownTargetRows'] += 1
            continue
        counts['knownTargetRows'] += 1; with_known_target.add(typed[0])
        missing.update(keys_for([{'families': sorted({a.lemma for a in analyses})}], 'family') - existing)
    return dict(sorted(counts.items())) | {'distinctUnknownTypoSurfaces': len(unknown_surfaces),
        'distinctUnknownWithKnownTarget': len(with_known_target), 'missingTargetFamilyKeys': len(missing)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True); args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'): raise ValueError('FRESH_BUILD_OUTPUT_REQUIRED')
    _, parent = q7.historical.expected_entries()
    base = ROOT / 'tools/typing_experiments/holdout-ledger.json'; before = hashlib.sha256(base.read_bytes()).hexdigest()
    ledger = load_ledger(base); entries = {e['id']: e for e in ledger['entries']}
    if entries.get(parent['id']) != parent or ENTRY not in entries: raise ValueError('Q7_TYPO_PARENT')
    dictionary = q7.PymorphyLexicon(cache_size=16384); dictionary_receipt = dictionary.receipt()
    digest = hashlib.sha256(json.dumps(dictionary_receipt, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if entries[ENTRY].get('dictionaryReceiptSha256') != digest: raise ValueError('Q7_TYPO_DICTIONARY_DRIFT')
    source = q7.historical.CORPUS / 'spelling-ru.jsonl'
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    rows = [json.loads(s) for s in source.read_text().splitlines()]
    result = audit(rows, dictionary, set(entries[ENTRY]['keys']['family']))
    if result['missingTargetFamilyKeys']: raise ValueError('Q7_TYPO_TARGET_FAMILY_MISSING')
    if hashlib.sha256(base.read_bytes()).hexdigest() != before or hashlib.sha256(source.read_bytes()).hexdigest() != source_sha or dictionary.receipt() != dictionary_receipt:
        raise ValueError('Q7_TYPO_INPUT_DRIFT')
    output.mkdir(parents=True, mode=0o700)
    receipt = {'purpose': 'DISCLOSED_AUTHORED_TYPO_FAMILY_AUDIT_NOT_QUALIFICATION', 'counts': result,
               'ledgerSha256': before, 'sourceSha256': source_sha, 'dictionaryReceiptSha256': digest,
               'scriptSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'modelCalls': 0}
    (output / 'receipt.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__': main()
