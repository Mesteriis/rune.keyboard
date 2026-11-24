"""Quarantine segments of retained historical text payloads, not full articles."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/ci'))
import historical_data_fixtures as data
import historical_model_fixtures as model
from holdout_ledger import _digest, keys_for, load_ledger, validate_ledger
from recover_ranker_sources import BOUNDARY
import import_word_epoch_windows as windows

PREFIX = 'public-word-epoch-text-segments-'


def segment_keys(text):
    if not isinstance(text, str) or not text.strip(): raise ValueError('TEXT_SEGMENT_EMPTY')
    text = unicodedata.normalize('NFC', text)
    segments = [' '.join(s.casefold().split()) for s in BOUNDARY.split(text)]
    return {_digest('sentence', ['tatoeba-full-sentence-normalized-v1',
        hashlib.sha256(s.encode()).hexdigest()]) for s in segments if s}


def make_entry(name, records, allowed_articles, parent, bindings):
    ids = [str(row.get('articleId', '')) for row in records]
    if (not records or len(ids) != len(set(ids)) or any(not x.isascii() or not x.isdecimal() for x in ids)
            or not set(ids) <= {str(a) for a in allowed_articles}): raise ValueError('TEXT_ARTICLE_SCOPE')
    segments = set()
    for row in records:
        if set(row) != {'articleId', 'text'}: raise ValueError('TEXT_ROW_SCHEMA')
        segments.update(segment_keys(row['text']))
    return {'id': PREFIX + name, 'usage': 'historical-source-exclusion', 'rowCount': len(records),
        'keys': {'article': sorted(keys_for([{'article': i} for i in ids], 'article')),
                 'sentence': sorted(segments)}, 'missingAxes': [], 'bindings': bindings,
        'parentEntries': [parent],
        'notes': 'Segments of archived historical text payloads; not all manifest articles or complete linguistic sentences.'}


def build(base):
    original = validate_ledger(base)
    if any(e['id'].startswith(PREFIX) for e in original['entries']): raise ValueError('TEXT_ALREADY_IMPORTED')
    paths = [Path(__file__).resolve(), Path(windows.__file__).resolve(),
        ROOT / 'tools/typing_experiments/recover_ranker_sources.py', ROOT / 'tools/typing_experiments/holdout_ledger.py',
        ROOT / 'tools/ci/historical_data_fixtures.py', ROOT / 'tools/ci/historical_model_fixtures.py',
        ROOT / 'tools/ci/historical_model_sources.py', ROOT / 'tools/model/rune-text-0.2/source-lock.json',
        ROOT / 'tools/typing_experiments/frozen_sources/manifest.json']
    for folder in (data.DATA, model.DATA): paths += [folder / n for n in ('manifest.json', 'files.tar.gz', 'articles.jsonl', 'NOTICE.md')]
    paths.append(model.sources.DATA / 'word-data-manifest.json')
    before = {str(p.relative_to(ROOT)): windows.sha(p) for p in paths}
    payload = data.verify(); _, model_payload = model.verify()
    windows.verify_parents(original, payload)
    result = copy.deepcopy(original); counts = {}
    specs = [('extra-test', payload, 'typing-extra-epochs/data/', 'test', data.ENTRY),
             *[('wordrank-' + p, model_payload, 'build/typing-word-ranking/data/', p, model.sources.ENTRY)
               for p in ('train', 'dev', 'test')]]
    for name, archive, directory, part, parent in specs:
        manifest = json.loads(archive[directory + 'manifest.json'])
        records = [json.loads(line) for line in archive[directory + part + '-text.jsonl'].splitlines()]
        entry = make_entry(name, records, manifest['partitions'][part]['articles'], parent, before)
        result['entries'].append(entry)
        counts[name] = {'textRecords': len(records), 'manifestArticles': len(set(manifest['partitions'][part]['articles'])),
                        'distinctSegments': len(entry['keys']['sentence'])}
    if before != {str(p.relative_to(ROOT)): windows.sha(p) for p in paths}: raise ValueError('TEXT_INPUT_DRIFT')
    return validate_ledger(result), {'purpose': 'HISTORICAL_TEXT_SEGMENTS_NOT_QUALIFICATION',
        'counts': counts, 'modelCalls': 0, 'globalCoverageComplete': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    args = p.parse_args(); root = args.output.resolve()
    if root.exists() or not root.is_relative_to(ROOT / 'build'): raise ValueError('FRESH_BUILD_OUTPUT_REQUIRED')
    result, receipt = build(load_ledger(args.base))
    root.mkdir(parents=True, mode=0o700)
    for name, value in (('ledger.json', result), ('receipt.json', receipt)):
        (root / name).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps(receipt['counts'], sort_keys=True))


if __name__ == '__main__': main()
