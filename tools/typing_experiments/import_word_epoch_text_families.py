"""Quarantine dictionary analyses of retained, disclosed public text fragments."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/ci'), str(ROOT / 'tools/morphology')]
import historical_data_fixtures as data
import historical_model_fixtures as model
import import_word_epoch_text_segments as segments
import import_q7_regression_families as families
from holdout_ledger import pack_ledger, validate_ledger
from ranker import PymorphyLexicon

PREFIX = 'public-word-epoch-text-families-'
WORD = re.compile('[а-яё]+')


def entry(name, records, allowed_articles, parent, lexicon, bindings, dictionary_sha):
    check = segments.make_entry(name, records, allowed_articles, 'unused', bindings)
    if parent['id'] != segments.PREFIX + name or parent['keys'] != check['keys']:
        raise ValueError('TEXT_FAMILY_PARENT_MISMATCH')
    surfaces = sorted({word for row in records for word in WORD.findall(
        unicodedata.normalize('NFC', row['text']).casefold())})
    if any(len(word) > 32 for word in surfaces):
        raise ValueError('TEXT_FAMILY_SURFACE_TOO_LONG')
    lemmas, unknown, stats = families.analyze(surfaces, lexicon)
    if not lemmas:
        raise ValueError('TEXT_FAMILY_EMPTY')
    result = {'id': PREFIX + name, 'usage': 'historical-family-exclusion',
              'rowCount': len(records), 'keys': {'family': lemmas}, 'missingAxes': [],
              'bindings': bindings, 'dictionaryReceiptSha256': dictionary_sha,
              'parentEntries': [parent['id']],
              'notes': 'All dictionary analyses of exact Russian tokens in archived text fragments; '
                       'unknowns are exact surfaces only, not inferred families or complete articles.'}
    if unknown:
        result['unsupportedSurfaceKeys'] = unknown
    return result, stats | {'familyKeys': len(lemmas), 'unsupportedSurfaceKeys': len(unknown)}


def build(base, lexicon):
    base = validate_ledger(base)
    parents = {e['id']: e for e in base['entries']}
    if any(key.startswith(PREFIX) for key in parents):
        raise ValueError('TEXT_FAMILIES_ALREADY_IMPORTED')
    raw = data.verify(); _, word = model.verify()
    specs = [('extra-test', raw, 'typing-extra-epochs/data/', 'test'),
             *[('wordrank-' + part, word, 'build/typing-word-ranking/data/', part)
               for part in ('train', 'dev', 'test')]]
    paths = {Path(__file__).resolve(), Path(segments.__file__).resolve(), Path(families.__file__).resolve(),
             ROOT / 'tools/morphology/ranker.py', ROOT / 'tools/typing_experiments/holdout_ledger.py',
             ROOT / 'tools/typing_experiments/source_identities.py'}
    for name, _, _, _ in specs:
        parent = parents[segments.PREFIX + name]
        paths.update(ROOT / p for p in parent['bindings'])
    bindings = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    dictionary = lexicon.receipt()
    dictionary_sha = hashlib.sha256(json.dumps(dictionary, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    result = copy.deepcopy(base); counts = {}
    for name, archive, directory, part in specs:
        manifest = json.loads(archive[directory + 'manifest.json'])
        rows = [json.loads(line) for line in archive[directory + part + '-text.jsonl'].splitlines()]
        result_entry, counts[name] = entry(name, rows, manifest['partitions'][part]['articles'],
                                          parents[segments.PREFIX + name], lexicon, bindings, dictionary_sha)
        result['entries'].append(result_entry)
    if lexicon.receipt() != dictionary or any(hashlib.sha256((ROOT / k).read_bytes()).hexdigest() != v for k, v in bindings.items()):
        raise ValueError('TEXT_FAMILY_INPUT_DRIFT')
    return validate_ledger(result), {'purpose': 'HISTORICAL_TEXT_FAMILIES_NOT_QUALIFICATION',
        'counts': counts, 'dictionary': dictionary, 'dictionaryReceiptSha256': dictionary_sha,
        'globalCoverageComplete': False, 'modelCalls': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'):
        raise ValueError('FRESH_BUILD_OUTPUT_REQUIRED')
    base_raw = args.base.read_bytes()
    base = json.loads(base_raw)
    ledger, receipt = build(copy.deepcopy(base), PymorphyLexicon(cache_size=16384))
    if args.base.read_bytes() != base_raw:
        raise ValueError('TEXT_FAMILY_INPUT_DRIFT')
    # Keep the existing storage representation intact; pack only new entries.
    stored = copy.deepcopy(base)
    stored['entries'].extend(pack_ledger(ledger)['entries'][-4:])
    if validate_ledger(copy.deepcopy(stored)) != ledger:
        raise ValueError('TEXT_FAMILY_STORAGE_MISMATCH')
    output.mkdir(parents=True, mode=0o700)
    for name, value in (('ledger.json', stored), ('receipt.json', receipt)):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps(receipt['counts'], sort_keys=True))


if __name__ == '__main__':
    main()
