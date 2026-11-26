"""Conservatively quarantine dictionary analyses of disclosed RU replay surfaces."""
import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/ci'), str(ROOT / 'tools/morphology')]
import register_historical_replay as historical
import register_product_replay_v1 as product
from holdout_ledger import keys_for, load_ledger, validate_ledger
from source_identities import unsupported_surface_key
from ranker import PymorphyLexicon

PREFIX = 'public-q7-regression-dictionary-families-'
WORD = re.compile('[а-яё]{1,32}\\Z')


def lexical_surfaces(values):
    result = set()
    for value in values:
        if not isinstance(value, str): raise ValueError('Q7_SURFACE_TYPE')
        normalized = unicodedata.normalize('NFC', value).casefold()
        if WORD.fullmatch(normalized): result.add(normalized)
    return sorted(result)


def analyze(surfaces, lexicon):
    families, unknown = set(), set(); counts = Counter()
    for word in surfaces:
        analyses = lexicon.analyses(word)
        if analyses:
            families.update(keys_for([{'families': sorted({a.lemma for a in analyses})}], 'family'))
            counts['dictionaryResolved'] += 1
        else:
            key = unsupported_surface_key(word)
            if key is None: raise ValueError('Q7_UNSUPPORTED_SURFACE')
            unknown.add(key); counts['dictionaryUnresolved'] += 1
    counts['surfaces'] = len(surfaces)
    return sorted(families), sorted(unknown), dict(sorted(counts.items()))


def build(base, inputs, lexicon, bindings, dictionary_sha):
    result = copy.deepcopy(validate_ledger(base)); existing = {e['id']: e for e in result['entries']}
    if any(k.startswith(PREFIX) for k in existing): raise ValueError('Q7_FAMILIES_ALREADY_IMPORTED')
    counts = {}
    for name, (values, parent) in inputs.items():
        if parent['id'] not in existing or existing[parent['id']] != parent: raise ValueError('Q7_FAMILY_PARENT_DRIFT')
        families, unknown, stats = analyze(lexical_surfaces(values), lexicon)
        if not families: raise ValueError('Q7_FAMILY_EMPTY')
        entry = {'id': PREFIX + name, 'usage': 'historical-family-exclusion',
                 'keys': {'family': families}, 'missingAxes': [], 'bindings': bindings,
                 'dictionaryReceiptSha256': dictionary_sha,
                 'parentEntries': [parent['id']],
                 'notes': 'All dictionary-only analyses of disclosed Russian replay surfaces; unknowns are exact surfaces only.'}
        if unknown: entry['unsupportedSurfaceKeys'] = unknown
        result['entries'].append(entry)
        counts[name] = stats | {'familyKeys': len(families), 'unsupportedSurfaceKeys': len(unknown)}
    return validate_ledger(result), counts


def source_inputs():
    _, product_parent = product.expected_entries(); _, historical_parent = historical.expected_entries()
    rows = [json.loads(s) for s in (product.DATA / 'inputs.jsonl').read_text().splitlines()]
    origins = [json.loads(s) for s in (product.DATA / 'origins.jsonl').read_text().splitlines()]
    values = [r['typed'] for r in rows if r['language'] == 'ru']
    values += [w['word'] for o in origins if o['language'] == 'ru' for w in [o['target'], *o['context']]]
    original = []
    for name in historical.FILES:
        for r in map(json.loads, (historical.CORPUS / name).read_text().splitlines()):
            if r['language'] != 'ru': continue
            original += [r['typed'], *r['prefix'].split(), *(v.strip() for v in r.get('candidates', []))]
    return {'product-v1': (values, product_parent), 'original-v2': (original, historical_parent)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    args = p.parse_args(); output = args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'): raise ValueError('FRESH_BUILD_OUTPUT_REQUIRED')
    base_bytes = args.base.read_bytes(); inputs = source_inputs(); dictionary = PymorphyLexicon(cache_size=16384)
    paths = [Path(__file__).resolve(), Path(product.__file__), Path(historical.__file__),
             ROOT / 'tools/ci/generate_product_replay_v1.py', ROOT / 'tools/morphology/ranker.py',
             ROOT / 'tools/typing_experiments/holdout_ledger.py', ROOT / 'tools/typing_experiments/source_identities.py']
    paths += [ROOT / key for _, parent in inputs.values() for key in parent['bindings']]
    bindings = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in set(paths)}
    dictionary_receipt = dictionary.receipt()
    dictionary_sha = hashlib.sha256(json.dumps(dictionary_receipt, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    ledger, counts = build(load_ledger(args.base), inputs, dictionary, bindings, dictionary_sha)
    receipt = {'purpose': 'DISCLOSED_Q7_DICTIONARY_FAMILY_QUARANTINE_NOT_QUALIFICATION',
               'counts': counts, 'dictionary': dictionary_receipt, 'dictionaryReceiptSha256': dictionary_sha, 'modelCalls': 0,
               'globalCoverageComplete': False}
    if (args.base.read_bytes() != base_bytes or dictionary.receipt() != dictionary_receipt or
            any(hashlib.sha256((ROOT/k).read_bytes()).hexdigest() != v for k,v in bindings.items())):
        raise ValueError('Q7_FAMILY_INPUT_DRIFT')
    output.mkdir(parents=True, mode=0o700)
    for name, value in (('ledger.json', ledger), ('receipt.json', receipt)):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps(counts, sort_keys=True))


if __name__ == '__main__': main()
