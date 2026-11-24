"""Recover all matching public source windows for frozen joint exclusions."""
import argparse
import copy
import json
from pathlib import Path

from holdout_ledger import keys_for, load_ledger, validate_ledger
from import_joint_history import BASE, MANIFESTS, SOURCES
from import_legacy_context_history import captures
from recover_legacy_families import sha
from recover_legacy_holdout import ORIGINAL, load_generator

ROOT=Path(__file__).resolve().parents[2]
PREFIX='public-joint-source-windows-'
GENERATOR_SHA='2cbcb2508ef66b32a60b5c7665ad96c66dc1c6477c9da4ad6dde0ea969806e65'


def build(root,base,read_batches):
    root=Path(root);result=copy.deepcopy(validate_ledger(base))
    if any(e['id'].startswith(PREFIX) for e in result['entries']):
        raise ValueError('JOINT_WINDOWS_ALREADY_IMPORTED')
    by_id={e['id']:e for e in result['entries']}; jobs=[];needed={}
    for corpus,digest in MANIFESTS.items():
        manifest_path=f'{BASE}/{corpus}/manifest.json'
        if sha(root/manifest_path)!=digest:raise ValueError('JOINT_WINDOWS_MANIFEST')
        manifest=json.loads((root/manifest_path).read_text())
        parts=('train','calibration','holdout') if corpus=='corpus' else ('calibration','holdout')
        if set(manifest['files'])!={p+'.jsonl' for p in parts}:raise ValueError('JOINT_WINDOWS_SCOPE')
        for part in parts:
            parent=by_id.get(f'public-joint-history-{corpus}-{part}')
            path=f'{BASE}/{corpus}/{part}.jsonl'
            if not parent or parent['bindings'].get(manifest_path)!=digest:raise ValueError('JOINT_WINDOWS_PARENT')
            file_hash=sha(root/path)
            if parent['bindings'].get(path)!=file_hash or manifest['files'][part+'.jsonl']!=file_hash:raise ValueError('JOINT_WINDOWS_ROWS')
            rows=[json.loads(line) for line in (root/path).read_text().splitlines()]
            if len(rows)!=parent.get('rowCount') or len(rows)!=manifest['counts'][part]['rows'] or len({r['id'] for r in rows})!=len(rows):raise ValueError('JOINT_WINDOWS_COUNT')
            source_name={'train':'ru-0011.parquet','calibration':'0018.parquet','holdout':'0019.parquet'}[part] if corpus=='corpus' else '0020.parquet'
            source=next(p for p in SOURCES if Path(p).name==source_name)
            if parent['bindings'].get(source)!=SOURCES[source]:raise ValueError('JOINT_WINDOWS_SOURCE_BINDING')
            for row in rows:
                if row.get('split')!=part or row.get('source')!=source_name or row.get('language')!='ru':raise ValueError('JOINT_WINDOWS_ROW_SCOPE')
                needed.setdefault(source,{}).setdefault(row['article'],set()).add((row['word'],row['prefix']))
            jobs.append((corpus,part,rows,parent,path,source))
    generator=load_generator(GENERATOR_SHA);windows={};source_hashes={}
    for source,wanted in needed.items():
        if sha(root/source)!=SOURCES[source]:raise ValueError('JOINT_WINDOWS_SOURCE_HASH')
        source_hashes[source]=SOURCES[source];remaining=set(wanted);seen=set()
        for articles,texts in read_batches(root/source):
            for article,text in zip(articles,texts,strict=True):
                article=str(article)
                if article not in wanted:continue
                if article in seen:raise ValueError('JOINT_WINDOWS_DUPLICATE_ARTICLE')
                seen.add(article)
                for frame,hashes in captures(text,wanted[article],generator).items():windows[(source,article,*frame)]=hashes
                remaining.remove(article)
        if remaining:raise ValueError('JOINT_WINDOWS_ARTICLE_MISSING')
    code_paths=('tools/typing_experiments/import_joint_source_windows.py','tools/typing_experiments/import_legacy_context_history.py',
                'tools/typing_experiments/recover_legacy_holdout.py','tools/typing_experiments/right_context_sentence_audit.py')
    code={p:sha(root/p) for p in code_paths};counts={}
    for corpus,part,rows,parent,path,source in jobs:
        projected=[{'article':r['article'],'contextHash':window} for r in rows
                   for window in windows[(source,r['article'],r['word'],r['prefix'])]]
        keys={axis:sorted(keys_for(projected,axis)) for axis in ('article','sentence')}
        result['entries'].append(dict(id=PREFIX+corpus+'-'+part,usage='historical-source-exclusion',keys=keys,missingAxes=[],
            bindings={path:parent['bindings'][path],f'{BASE}/{corpus}/manifest.json':MANIFESTS[corpus],source:SOURCES[source]}|code,
            parentEntries=[parent['id']],generatorBindings={ORIGINAL:GENERATOR_SHA},
            notes='All matching public article windows; historical parent family and sentence gaps remain disclosed.'))
        counts[corpus+'/'+part]={'rows':len(rows),'windows':len(keys['sentence']),'articles':len(keys['article'])}
    for entry in result['entries']:
        if entry['id'].startswith(PREFIX):
            if any(sha(root/path)!=digest for path,digest in entry['bindings'].items()):
                raise ValueError('JOINT_WINDOWS_INPUT_DRIFT')
    return validate_ledger(result),dict(purpose='JOINT_PUBLIC_WINDOWS_NOT_QUALIFICATION',counts=counts,sourceBindings=source_hashes,codeBindings=code,generatorSha256=GENERATOR_SHA,modelCalls=0)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():parser.error('output already exists')
    import pyarrow.parquet as parquet
    def batches(path):
        for batch in parquet.ParquetFile(path).iter_batches(batch_size=128,columns=['id','text']):yield batch.column(0).to_pylist(),batch.column(1).to_pylist()
    ledger,receipt=build(ROOT,load_ledger(args.base),batches)
    args.output.mkdir(parents=True,exist_ok=False)
    for name,value in (('ledger.json',ledger),('receipt.json',receipt)):(args.output/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps(receipt['counts']))

if __name__=='__main__':main()
