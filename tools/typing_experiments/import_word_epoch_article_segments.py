"""Quarantine selector-delimited segments of historical manifest articles."""
import argparse
import copy
import json
from pathlib import Path

import import_word_epoch_text_segments as text_import
from holdout_ledger import keys_for, load_ledger, validate_ledger

ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'public-word-epoch-article-segments-'


def collect(sets, batches):
    needed = set().union(*sets.values()); seen = set(); found = {name: set() for name in sets}
    for articles, texts in batches:
        for article, text in zip(articles, texts, strict=True):
            article = str(article)
            if article not in needed: continue
            if article in seen: raise ValueError('ARTICLE_SEGMENT_DUPLICATE')
            seen.add(article)
            keys = text_import.segment_keys(text)
            for name, ids in sets.items():
                if article in ids: found[name].update(keys)
    if seen != needed: raise ValueError('ARTICLE_SEGMENT_MISSING')
    return found


def build(base, read_batches):
    original = validate_ledger(base)
    if any(e['id'].startswith(PREFIX) for e in original['entries']): raise ValueError('ARTICLE_SEGMENT_ALREADY_IMPORTED')
    data, model, windows = text_import.data, text_import.model, text_import.windows
    paths = [Path(__file__).resolve(), Path(text_import.__file__).resolve(), Path(windows.__file__).resolve(),
             ROOT / windows.SOURCE, ROOT / 'tools/model/rune-text-0.2/source-lock.json',
             ROOT / 'tools/typing_experiments/frozen_sources/manifest.json',
             ROOT / 'tools/typing_experiments/recover_ranker_sources.py', ROOT / 'tools/typing_experiments/holdout_ledger.py',
             ROOT / 'tools/ci/historical_data_fixtures.py', ROOT / 'tools/ci/historical_model_fixtures.py',
             ROOT / 'tools/ci/historical_model_sources.py']
    for folder in (data.DATA, model.DATA): paths += [folder / n for n in ('manifest.json', 'files.tar.gz', 'articles.jsonl', 'NOTICE.md')]
    paths.append(model.sources.DATA / 'word-data-manifest.json')
    before = {str(p.relative_to(ROOT)): windows.sha(p) for p in paths}
    if before[windows.SOURCE] != windows.SOURCE_SHA: raise ValueError('ARTICLE_SEGMENT_SOURCE_IDENTITY')
    payload = data.verify(); _, model_payload = model.verify()
    windows.verify_parents(original, payload)
    specs = [('extra-test', payload, 'typing-extra-epochs/data/', 'test', data.ENTRY),
             *[('wordrank-' + p, model_payload, 'build/typing-word-ranking/data/', p, model.sources.ENTRY)
               for p in ('train', 'dev', 'test')]]
    sets, parents = {}, {}
    for name, archive, directory, part, parent in specs:
        manifest = json.loads(archive[directory + 'manifest.json'])
        ids = manifest['partitions'][part]['articles']
        if not ids or any(not str(i).isascii() or not str(i).isdecimal() for i in ids):
            raise ValueError('ARTICLE_SEGMENT_MANIFEST')
        sets[name] = {str(i) for i in ids}; parents[name] = parent
        parent_entry = next(e for e in original['entries'] if e['id'] == parent)
        if not keys_for([{'article': i} for i in sets[name]], 'article') <= set(parent_entry['keys']['article']):
            raise ValueError('ARTICLE_SEGMENT_PARENT')
    found = collect(sets, read_batches(ROOT / windows.SOURCE))
    if before != {str(p.relative_to(ROOT)): windows.sha(p) for p in paths}: raise ValueError('ARTICLE_SEGMENT_INPUT_DRIFT')
    result = copy.deepcopy(original); counts = {}
    for name in sets:
        if not found[name]: raise ValueError('ARTICLE_SEGMENT_EMPTY')
        result['entries'].append({'id': PREFIX + name, 'usage': 'historical-source-exclusion',
            'rowCount': len(sets[name]), 'keys': {'article': sorted(keys_for([{'article': i} for i in sets[name]], 'article')),
            'sentence': sorted(found[name])}, 'missingAxes': [], 'bindings': before, 'parentEntries': [parents[name]],
            'notes': 'Full source articles segmented by historical delimiters; not verified linguistic sentences.'})
        counts[name] = {'articles': len(sets[name]), 'distinctSegments': len(found[name])}
    return validate_ledger(result), {'purpose': 'HISTORICAL_ARTICLE_SEGMENTS_NOT_QUALIFICATION',
        'counts': counts, 'modelCalls': 0, 'globalCoverageComplete': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    args = p.parse_args(); root = args.output.resolve()
    if root.exists() or not root.is_relative_to(ROOT / 'build'): raise ValueError('FRESH_BUILD_OUTPUT_REQUIRED')
    import pyarrow.parquet as parquet
    def batches(path):
        for batch in parquet.ParquetFile(path).iter_batches(batch_size=128, columns=['id', 'text']):
            yield batch.column(0).to_pylist(), batch.column(1).to_pylist()
    result, receipt = build(load_ledger(args.base), batches)
    root.mkdir(parents=True, mode=0o700)
    for name, value in (('ledger.json', result), ('receipt.json', receipt)):
        (root / name).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps(receipt['counts'], sort_keys=True))


if __name__ == '__main__': main()
