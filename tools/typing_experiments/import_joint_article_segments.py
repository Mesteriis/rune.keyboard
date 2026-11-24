"""Quarantine full selector segments of pinned historical joint articles."""
import argparse
import copy
import json
from pathlib import Path

from holdout_ledger import keys_for, load_ledger, validate_ledger
from import_joint_history import BASE, MANIFESTS, SOURCES
from import_word_epoch_article_segments import collect
from recover_legacy_families import sha

ROOT=Path(__file__).resolve().parents[2]
PREFIX='public-joint-article-segments-'


def build(root,base,read_batches):
    root=Path(root);original=validate_ledger(base)
    if any(e['id'].startswith(PREFIX) for e in original['entries']):raise ValueError('JOINT_SEGMENTS_ALREADY_IMPORTED')
    entries={e['id']:e for e in original['entries']};jobs={};bindings={}
    code=('tools/typing_experiments/import_joint_article_segments.py',
          'tools/typing_experiments/import_word_epoch_article_segments.py',
          'tools/typing_experiments/import_word_epoch_text_segments.py',
          'tools/typing_experiments/import_joint_history.py','tools/typing_experiments/holdout_ledger.py',
          'tools/typing_experiments/recover_ranker_sources.py','tools/typing_experiments/recover_legacy_families.py')
    for name in code:bindings[name]=sha(root/name)
    for name,digest in SOURCES.items():
        if sha(root/name)!=digest:raise ValueError('JOINT_SEGMENTS_SOURCE_IDENTITY')
        bindings[name]=digest
    for corpus,digest in MANIFESTS.items():
        manifest_name=f'{BASE}/{corpus}/manifest.json';path=root/manifest_name
        if sha(path)!=digest:raise ValueError('JOINT_SEGMENTS_MANIFEST_IDENTITY')
        bindings[manifest_name]=digest;manifest=json.loads(path.read_text())
        parts=('train','calibration','holdout') if corpus=='corpus' else ('calibration','holdout')
        if set(manifest['files'])!={part+'.jsonl' for part in parts}:raise ValueError('JOINT_SEGMENTS_SCOPE')
        for part in parts:
            parent=f'public-joint-history-{corpus}-{part}';window=f'public-joint-source-windows-{corpus}-{part}'
            if parent not in entries or window not in entries:raise ValueError('JOINT_SEGMENTS_PARENT')
            relative=f'{BASE}/{corpus}/{part}.jsonl';digest=sha(root/relative)
            if (digest!=manifest['files'][part+'.jsonl'] or entries[parent]['bindings'].get(relative)!=digest or
                    entries[window]['bindings'].get(relative)!=digest):raise ValueError('JOINT_SEGMENTS_ROWS_IDENTITY')
            bindings[relative]=digest;rows=[json.loads(line) for line in (root/relative).read_text().splitlines()]
            if len(rows)!=entries[parent].get('rowCount') or len({r['id'] for r in rows})!=len(rows):raise ValueError('JOINT_SEGMENTS_ROW_COUNT')
            source={'train':'ru-0011.parquet','calibration':'0018.parquet','holdout':'0019.parquet'}[part] if corpus=='corpus' else '0020.parquet'
            if any(r.get('split')!=part or r.get('source')!=source or r.get('language')!='ru' for r in rows):raise ValueError('JOINT_SEGMENTS_ROW_SCOPE')
            ids={r['article'] for r in rows};article_keys=keys_for([{'article':i} for i in ids],'article')
            if not article_keys<=set(entries[parent]['keys']['article']):raise ValueError('JOINT_SEGMENTS_PARENT_ARTICLES')
            jobs[f'{corpus}-{part}']=(source,ids,len(rows),parent,window,article_keys)
    grouped={}
    for name,(source,ids,*_) in jobs.items():grouped.setdefault(source,{})[name]=ids
    found={}
    for source,sets in grouped.items():
        source_paths=[name for name in SOURCES if Path(name).name==source]
        if len(source_paths)!=1:raise ValueError('JOINT_SEGMENTS_SOURCE_SCOPE')
        found.update(collect(sets,read_batches(root/source_paths[0])))
    if any(sha(root/name)!=digest for name,digest in bindings.items()):raise ValueError('JOINT_SEGMENTS_INPUT_DRIFT')
    result=copy.deepcopy(original);counts={}
    for name,(source,ids,row_count,parent,window,article_keys) in jobs.items():
        if not found[name]:raise ValueError('JOINT_SEGMENTS_EMPTY')
        result['entries'].append(dict(id=PREFIX+name,usage='historical-source-exclusion',rowCount=row_count,
            keys={'article':sorted(article_keys),'sentence':sorted(found[name])},missingAxes=[],bindings=bindings,
            parentEntries=[parent,window],notes='All historical source article segments, including alternative matching windows; not linguistic sentence validation.'))
        counts[name]=dict(rows=row_count,articles=len(ids),distinctSegments=len(found[name]))
    return validate_ledger(result),dict(purpose='HISTORICAL_JOINT_ARTICLE_SEGMENTS_NOT_QUALIFICATION',counts=counts,modelCalls=0,globalCoverageComplete=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    output=args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('FRESH_BUILD_OUTPUT_REQUIRED')
    import pyarrow.parquet as parquet
    def batches(path):
        for batch in parquet.ParquetFile(path).iter_batches(batch_size=128,columns=['id','text']):yield batch.column(0).to_pylist(),batch.column(1).to_pylist()
    result,receipt=build(ROOT,load_ledger(args.base),batches)
    output.mkdir(parents=True,mode=0o700)
    for name,value in (('ledger.json',result),('receipt.json',receipt)):(output/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps(receipt['counts'],sort_keys=True))


if __name__=='__main__':main()
