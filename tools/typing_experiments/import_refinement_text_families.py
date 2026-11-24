"""Quarantine public refinement text fragments and dictionary analyses."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/ci'), str(ROOT / 'tools/morphology')]
import historical_data_fixtures as data
import import_word_epoch_text_segments as segments
import import_word_epoch_text_families as families
from holdout_ledger import pack_ledger, validate_ledger
from ranker import PymorphyLexicon

PREFIX = 'public-refinement-text-'


def partition_entries(part, records, allowed_articles, parent, lexicon, bindings, dictionary_sha):
    parent_id = 'public-ranker-history-' + part
    if parent['id'] != parent_id:
        raise ValueError('REFINEMENT_TEXT_PARENT')
    source = segments.make_entry(part, records, allowed_articles, parent_id, bindings)
    if not set(source['keys']['article']) <= set(parent['keys'].get('article', [])):
        raise ValueError('REFINEMENT_TEXT_PARENT_ARTICLES')
    source['id'] = PREFIX + 'segments-' + part
    source['parentEntrySha256'] = hashlib.sha256(json.dumps(parent, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    source['notes'] = 'Segments of archived refinement text payloads; not complete source articles or linguistic sentences.'
    alias = copy.deepcopy(source)
    alias['id'] = segments.PREFIX + part
    family, counts = families.entry(part, records, allowed_articles, alias, lexicon, bindings, dictionary_sha)
    family['id'] = PREFIX + 'families-' + part
    family['parentEntries'] = [source['id']]
    return source, family, counts


def build(base, lexicon):
    base = validate_ledger(base)
    parents = {e['id']: e for e in base['entries']}
    if any(key.startswith(PREFIX) for key in parents):
        raise ValueError('REFINEMENT_TEXT_ALREADY_IMPORTED')
    paths = {Path(__file__).resolve(), Path(segments.__file__).resolve(), Path(families.__file__).resolve(),
             Path(families.families.__file__).resolve(), ROOT / 'tools/morphology/ranker.py',
             ROOT / 'tools/typing_experiments/holdout_ledger.py', ROOT / 'tools/typing_experiments/source_identities.py',
             ROOT / 'tools/ci/historical_data_fixtures.py', ROOT / 'tools/typing_experiments/frozen_sources/manifest.json',
             ROOT / 'tools/model/rune-text-0.2/source-lock.json'}
    paths.update(data.DATA / name for name in ('manifest.json', 'files.tar.gz', 'articles.jsonl', 'NOTICE.md'))
    bindings = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    payload = data.verify()
    manifest = json.loads(payload['typing-refinement/data/manifest.json'])
    dictionary = lexicon.receipt()
    dictionary_sha = hashlib.sha256(json.dumps(dictionary, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    result = copy.deepcopy(base); counts = {}
    for part in ('train', 'dev', 'test'):
        rows = [json.loads(line) for line in payload['typing-refinement/data/' + part + '-text.jsonl'].splitlines()]
        source, family, counts[part] = partition_entries(part, rows, manifest['partitions'][part]['articles'],
            parents['public-ranker-history-' + part], lexicon, bindings, dictionary_sha)
        result['entries'].extend((source, family))
        counts[part]['records'] = len(rows)
    if lexicon.receipt() != dictionary or any(hashlib.sha256((ROOT / k).read_bytes()).hexdigest() != v for k, v in bindings.items()):
        raise ValueError('REFINEMENT_TEXT_INPUT_DRIFT')
    return validate_ledger(result), {'purpose': 'HISTORICAL_REFINEMENT_TEXT_NOT_QUALIFICATION',
        'counts': counts, 'dictionary': dictionary, 'dictionaryReceiptSha256': dictionary_sha,
        'globalCoverageComplete': False, 'modelCalls': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); output = args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'):
        raise ValueError('FRESH_BUILD_OUTPUT_REQUIRED')
    base_raw = args.base.read_bytes(); base = json.loads(base_raw)
    ledger, receipt = build(copy.deepcopy(base), PymorphyLexicon(cache_size=16384))
    if args.base.read_bytes() != base_raw:
        raise ValueError('REFINEMENT_TEXT_INPUT_DRIFT')
    stored = copy.deepcopy(base); stored['entries'].extend(pack_ledger(ledger)['entries'][-6:])
    if validate_ledger(copy.deepcopy(stored)) != ledger:
        raise ValueError('REFINEMENT_TEXT_STORAGE_MISMATCH')
    output.mkdir(parents=True, mode=0o700)
    for name, value in (('ledger.json', stored), ('receipt.json', receipt)):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps(receipt['counts'], sort_keys=True))


if __name__ == '__main__':
    main()
