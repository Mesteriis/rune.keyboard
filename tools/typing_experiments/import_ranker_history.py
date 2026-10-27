"""Import pinned public ranker training/dev/test exposure, without scoring."""
import argparse
import copy
import json
from pathlib import Path
import sys

from holdout_ledger import keys_for, load_ledger, validate_ledger
from recover_legacy_families import recover_rows, sha

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = 'build/typing-ranker-v2/data/manifest.json'
MANIFEST_SHA = '20b32e840b890aab726fabea30c6409fce058d0c9ba3dd64d603aaaa24475ce7'
SOURCE = 'build/smart-typing-0.3/model-v02/wikipedia-20231101/ru-0007.parquet'
PREFIX = 'public-ranker-history-'


def partition_entries(part, metadata, rows, lexicon, bindings):
    if part not in ('train', 'dev', 'test'):
        raise ValueError('RANKER_PARTITION')
    articles = metadata['articles']
    if not isinstance(articles, list) or len(set(articles)) != len(articles) or not articles:
        raise ValueError('RANKER_ARTICLE_LIST')
    article_keys = sorted(keys_for([dict(article=a) for a in articles], 'article'))
    if len(rows) != metadata['rows'] or not rows:
        raise ValueError('RANKER_ROW_COUNT')
    if any(r.get('articleId') not in articles or r.get('partition') != part or r.get('language') != 'ru'
           for r in rows):
        raise ValueError('RANKER_ROW_SOURCE')
    family_keys, counts = recover_rows(rows, lexicon)
    entries = [dict(id=PREFIX+part, usage='historical-exclusion', bindings=bindings,
        keys={'article': article_keys}, missingAxes=['family', 'sentence', 'context'],
        rowCount=len(rows), sourceArticleCount=len(articles),
        notes='All manifest text-partition articles, including articles without target rows. Family addendum is partial.')]
    if family_keys:
        entries.append(dict(id=PREFIX+part+'-families', bindings=bindings,
            usage='supervised' if part == 'train' else 'historical-family-exclusion',
            keys={'family': family_keys}, missingAxes=[], parentEntries=[PREFIX+part],
            notes='All dictionary-supported target analyses only. Unknown targets remain pending in parent.'))
    return entries, counts


def build(root, base, lexicon):
    root = Path(root); result = copy.deepcopy(validate_ledger(base))
    if any(e['id'].startswith(PREFIX) for e in result['entries']):
        raise ValueError('RANKER_ALREADY_IMPORTED')
    if sha(root / MANIFEST) != MANIFEST_SHA:
        raise ValueError('RANKER_MANIFEST_IDENTITY')
    manifest = json.loads((root / MANIFEST).read_text())
    if (manifest['containsPersonalMessages'] is not False or manifest['sourceRepository'] != 'wikimedia/wikipedia'
            or manifest['sourceRevision'] != 'a634f78b1c435397c07001e175fa74cc4ad5e775'
            or manifest['sourcePath'] != '20231101.ru/train/0007.parquet'
            or sha(root / SOURCE) != manifest['sourceSha256']):
        raise ValueError('RANKER_PUBLIC_SOURCE')
    bindings = {MANIFEST: MANIFEST_SHA, SOURCE: manifest['sourceSha256']}
    # Verify every file advertised in the frozen manifest, including text exposure.
    for filename, digest in manifest['files'].items():
        path = Path(MANIFEST).parent / filename
        if Path(filename).name != filename or sha(root / path) != digest:
            raise ValueError('RANKER_FILE_IDENTITY')
        bindings[str(path)] = digest
    bindings.update({p:sha(root/p) for p in ('tools/typing_experiments/import_ranker_history.py',
        'tools/typing_experiments/recover_legacy_families.py','tools/morphology/ranker.py')})
    counts = {}
    for part in ('train', 'dev', 'test'):
        rows = [json.loads(line) for line in (root/Path(MANIFEST).parent/f'{part}-rows.jsonl').read_text().splitlines()]
        entries, counts[part] = partition_entries(part, manifest['partitions'][part], rows, lexicon, bindings)
        result['entries'].extend(entries)
    receipt = dict(purpose='PUBLIC_RANKER_HISTORY_EXCLUSIONS_NOT_QUALIFICATION',
        bindings=bindings, dictionary=lexicon.receipt(), counts=counts, modelCalls=0,
        currentCorpusArticleOverlap={e['id']:len(set(e['keys'].get('article',[])) &
            {k for x in result['entries'] if x['id'] in [PREFIX+p for p in ('train','dev','test')]
             for k in x['keys']['article']}) for e in base['entries']
             if e['id'].startswith('public-right-context-available-')})
    return validate_ledger(result), receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output already exists')
    sys.path.insert(0, str(ROOT/'tools/morphology'))
    from ranker import PymorphyLexicon
    ledger, receipt = build(ROOT, load_ledger(args.base), PymorphyLexicon(cache_size=16384))
    args.output.mkdir(parents=True,exist_ok=False)
    for name,value in (('ledger.json',ledger),('receipt.json',receipt)):
        (args.output/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps(dict(entriesAdded=6, counts={p:dict(rows=c['rows'],unresolvedRows=len(c['unresolvedRows']))
        for p,c in receipt['counts'].items()}, currentCorpusArticleOverlap=receipt['currentCorpusArticleOverlap'])))


if __name__ == '__main__':
    main()
