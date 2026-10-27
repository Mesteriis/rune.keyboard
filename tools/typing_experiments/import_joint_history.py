"""Import explicitly pinned public joint/follow-up histories without scoring."""
import argparse
import copy
import json
from pathlib import Path
import sys

from holdout_ledger import keys_for, load_ledger, validate_ledger
from recover_legacy_families import recover_rows, sha

ROOT = Path(__file__).resolve().parents[2]
BASE = 'build/joint-correction-20261025'
MANIFESTS = {
    'corpus': '27c7084f8c739f608da77f617eca1c5ac552ff16b74da05a1a3c3cc888120e3f',
    'followup-corpus': 'abfb4cdea2657478f7834f4d645339238907bce71de31f13339a1410967f471b',
    'followup-corpus-v3': '9e8f8e5ec18825b340b9da68956fa75f55432f45ad1d21c01347e99430d7216b',
}
SOURCES = {
    'build/typing-ranker-v2/ru-0011.parquet': '30a2bd638e0556d1d09d459fd5ef5a4a7accbd54a7cc452798770bd80481dc5f',
    BASE+'/0018.parquet': '588e30523cfed480151b4bd5c1a7d7211dc03971fee399a3db6af3ad04e42c87',
    BASE+'/0019.parquet': '4c3bd676fbeb9d92ae7ed324e99f329de2542f5399cbf39b924529fff944dec6',
    BASE+'/0020.parquet': 'fc1e2edc58fa27085d36c32c38922d7904077d9cdac05719efbcefa3faeea240',
}
PREFIX = 'public-joint-history-'


def partition_entries(corpus, part, rows, expected_count, source_name, source_articles, lexicon, bindings):
    if not rows or len(rows) != expected_count:
        raise ValueError('JOINT_ROW_COUNT')
    if any(r.get('source') != source_name or r.get('article') not in source_articles
           or r.get('split') != part or r.get('language') != 'ru' for r in rows):
        raise ValueError('JOINT_ROW_SOURCE')
    families, counts = recover_rows(rows, lexicon)
    name = PREFIX+corpus+'-'+part
    entries = [dict(id=name,usage='historical-exclusion',bindings=bindings,rowCount=len(rows),
        keys={axis:sorted(keys_for(rows,axis)) for axis in ('article','context')},
        missingAxes=['family','sentence'],
        notes='Original article and typo-independent target-context keys. Native numeric family IDs are not Pymorph lemmas.')]
    if families:
        entries.append(dict(id=name+'-families',usage='supervised' if part=='train' else 'historical-family-exclusion',
            bindings=bindings,keys={'family':families},missingAxes=[],parentEntries=[name],
            notes='Dictionary-only union of all target analyses. Parent family coverage remains pending.'))
    return entries,counts


def build(root, base, lexicon, read_articles):
    root=Path(root);result=copy.deepcopy(validate_ledger(base))
    if any(e['id'].startswith(PREFIX) for e in result['entries']):
        raise ValueError('JOINT_ALREADY_IMPORTED')
    # Sources are pinned public Wikipedia shards, never arbitrary local corpora.
    articles={}
    for path,digest in SOURCES.items():
        if sha(root/path)!=digest:
            raise ValueError('JOINT_PUBLIC_SOURCE_IDENTITY')
        articles[Path(path).name]=read_articles(root/path)
    bindings=dict(SOURCES)
    for relative in ('public-source-lock.json','followup-source-lock.json'):
        path=BASE+'/'+relative;lock=json.loads((root/path).read_text())
        if lock['repository']!='wikimedia/wikipedia' or lock['revision']!='a634f78b1c435397c07001e175fa74cc4ad5e775':
            raise ValueError('JOINT_PUBLIC_PROVENANCE')
        for source in lock['files']:
            local=BASE+'/'+Path(source['path']).name
            if (not source['path'].startswith('20231101.ru/train/') or SOURCES.get(local)!=source['lfs']['oid']
                    or (root/local).stat().st_size!=source['size']):
                raise ValueError('JOINT_PUBLIC_PROVENANCE')
        bindings[path]=sha(root/path)
    for path in ('tools/typing_experiments/import_joint_history.py','tools/typing_experiments/recover_legacy_families.py','tools/morphology/ranker.py'):
        bindings[path]=sha(root/path)
    counts={};builders={}
    for corpus,digest in MANIFESTS.items():
        manifest_path=BASE+'/'+corpus+'/manifest.json'
        if sha(root/manifest_path)!=digest:
            raise ValueError('JOINT_MANIFEST_IDENTITY')
        manifest=json.loads((root/manifest_path).read_text());corpus_bindings=bindings|{manifest_path:digest}
        if corpus=='corpus':
            if manifest['sourceBindings']!={k:v for k,v in SOURCES.items() if not k.endswith('0020.parquet')}:
                raise ValueError('JOINT_CORPUS_SOURCE')
            builders[corpus]=manifest['builder']
        else:
            if manifest['sourceSha256']!=SOURCES[BASE+'/0020.parquet'] or manifest['priorCorpusSha256']!=MANIFESTS['corpus']:
                raise ValueError('JOINT_CORPUS_SOURCE')
            builders[corpus]=manifest['builderSha256']
        parts=('train','calibration','holdout') if corpus=='corpus' else ('calibration','holdout')
        if set(manifest['files'])!={part+'.jsonl' for part in parts}:
            raise ValueError('JOINT_CORPUS_FILES')
        for part in parts:
            path=BASE+'/'+corpus+'/'+part+'.jsonl'
            if sha(root/path)!=manifest['files'][part+'.jsonl']:
                raise ValueError('JOINT_FILE_IDENTITY')
            rows=[json.loads(line) for line in (root/path).read_text().splitlines()]
            source_name={'train':'ru-0011.parquet','calibration':'0018.parquet','holdout':'0019.parquet'}[part] if corpus=='corpus' else '0020.parquet'
            entries,counts[corpus+'/'+part]=partition_entries(corpus,part,rows,manifest['counts'][part]['rows'],
                source_name,articles[source_name],lexicon,corpus_bindings|{path:sha(root/path)})
            result['entries'].extend(entries)
    imported_articles={key for e in result['entries'] if e['id'].startswith(PREFIX) for key in e['keys'].get('article',[])}
    receipt=dict(purpose='PUBLIC_JOINT_HISTORY_EXCLUSIONS_NOT_QUALIFICATION',bindings=bindings,
        counts=counts,originalBuilderHashes=builders,dictionary=lexicon.receipt(),modelCalls=0,
        publicRepository='wikimedia/wikipedia',publicRevision='a634f78b1c435397c07001e175fa74cc4ad5e775',
        importedArticles=len(imported_articles),currentCorpusArticleOverlap={e['id']:len(imported_articles & set(e['keys'].get('article',[])))
            for e in base['entries'] if e['id'].startswith('public-right-context-available-')})
    return validate_ledger(result),receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('output already exists')
    sys.path.insert(0,str(ROOT/'tools/morphology'))
    from ranker import PymorphyLexicon
    import pyarrow.parquet as parquet
    def read_articles(path):
        return {str(article) for batch in parquet.ParquetFile(path).iter_batches(columns=['id']) for article in batch.column(0).to_pylist()}
    ledger,receipt=build(ROOT,load_ledger(args.base),PymorphyLexicon(cache_size=16384),read_articles)
    args.output.mkdir(parents=True,exist_ok=False)
    for name,value in (('ledger.json',ledger),('receipt.json',receipt)):
        (args.output/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps(dict(importedArticles=receipt['importedArticles'],rows=sum(v['rows'] for v in receipt['counts'].values()),
        unresolvedRows=sum(len(v['unresolvedRows']) for v in receipt['counts'].values()),currentCorpusArticleOverlap=receipt['currentCorpusArticleOverlap'])))


if __name__=='__main__':main()
