"""Audit source relationships in the disclosed, label-free Q7 v1 corpus."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import import_q7_regression_families as q7
import generate_product_replay_v1 as generator
from holdout_ledger import keys_for, load_ledger
from source_identities import unsupported_surface_key

ROOT = Path(__file__).resolve().parents[2]
ENTRY = q7.PREFIX + 'product-v1'


def audit(rows, origins, lexicon, family_keys, surface_keys):
    if len(rows) != 4 * len(origins): raise ValueError('Q7_VARIANT_ROW_COUNT')
    counts = Counter(); unknown_surfaces = set(); unknown_targets = set(); missing_families = set(); missing_surfaces = set()
    for index, origin in enumerate(origins):
        target = origin['target']['word']; group = rows[index * 4:index * 4 + 4]
        if (any(row['language'] != origin['language'] for row in group) or
                [row['typed'] for row in group] != list(generator.variants(target))):
            raise ValueError('Q7_VARIANT_RELATION')
        if origin['language'] != 'ru': continue
        analyses = lexicon.analyses(target)
        for row in group:
            typed = row['typed'].casefold()
            if lexicon.analyses(typed): continue
            counts['unknownVariantRows'] += 1; unknown_surfaces.add(typed)
            if analyses:
                counts['knownSourceRows'] += 1
                missing_families.update(keys_for([{'families': sorted({a.lemma for a in analyses})}], 'family') - family_keys)
            else:
                counts['unknownSourceRows'] += 1; unknown_targets.add(target)
                surface = unsupported_surface_key(target)
                if surface is None: raise ValueError('Q7_VARIANT_SOURCE_SURFACE')
                if surface not in surface_keys: missing_surfaces.add(surface)
    return dict(sorted(counts.items())) | {'distinctUnknownVariants': len(unknown_surfaces),
        'distinctUnknownSources': len(unknown_targets), 'missingSourceFamilyKeys': len(missing_families),
        'missingSourceSurfaces': len(missing_surfaces)}


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', type=Path, required=True)
    args = p.parse_args(); output = args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'): raise ValueError('FRESH_BUILD_OUTPUT_REQUIRED')
    _, parent = q7.product.expected_entries()
    base = ROOT / 'tools/typing_experiments/holdout-ledger.json'; ledger_sha = hashlib.sha256(base.read_bytes()).hexdigest()
    entries = {e['id']: e for e in load_ledger(base)['entries']}
    if entries.get(parent['id']) != parent or ENTRY not in entries: raise ValueError('Q7_VARIANT_PARENT')
    dictionary = q7.PymorphyLexicon(cache_size=16384); dictionary_receipt = dictionary.receipt()
    dictionary_sha = hashlib.sha256(json.dumps(dictionary_receipt, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if entries[ENTRY].get('dictionaryReceiptSha256') != dictionary_sha: raise ValueError('Q7_VARIANT_DICTIONARY_DRIFT')
    rows_file, origins_file = q7.product.DATA / 'inputs.jsonl', q7.product.DATA / 'origins.jsonl'
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (rows_file, origins_file)}
    rows = [json.loads(s) for s in rows_file.read_text().splitlines()]
    origins = [json.loads(s) for s in origins_file.read_text().splitlines()]
    result = audit(rows, origins, dictionary, set(entries[ENTRY]['keys']['family']),
                   set(entries[ENTRY].get('unsupportedSurfaceKeys', [])))
    if result['missingSourceFamilyKeys'] or result['missingSourceSurfaces']: raise ValueError('Q7_VARIANT_COVERAGE')
    if (hashlib.sha256(base.read_bytes()).hexdigest() != ledger_sha or dictionary.receipt() != dictionary_receipt or
            any(hashlib.sha256(p.read_bytes()).hexdigest() != hashes[p.name] for p in (rows_file, origins_file))):
        raise ValueError('Q7_VARIANT_INPUT_DRIFT')
    output.mkdir(parents=True, mode=0o700)
    receipt = {'purpose': 'DISCLOSED_Q7_SOURCE_RELATION_NOT_QUALIFICATION', 'counts': result,
               'ledgerSha256': ledger_sha, 'sourceSha256': hashes, 'dictionaryReceiptSha256': dictionary_sha,
               'scriptSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'modelCalls': 0}
    (output / 'receipt.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__': main()
