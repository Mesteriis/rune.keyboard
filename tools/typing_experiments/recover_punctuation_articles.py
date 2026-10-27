"""Recover every eligible source article for pinned punctuation components."""
import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path

from control_ledger import LANGUAGES,article_key,key_for,load,validate
from import_control_components import load_original,validate_rows
from import_early_ru_history import CORPORA,ROOT
from recover_early_ru_sources import archived_source
from recover_legacy_families import sha


def selected_rows(rows,seed):
    validate_rows(rows,'punctuation',seed)
    result={r['template'].removeprefix(r['split']+'-punctuation-'):r for r in rows}
    if len(result)!=len(rows):raise ValueError('PUNCTUATION_DUPLICATE_SELECTION')
    return result


def matches(article,text,selected,generator,language,seed):
    records=[]
    for item in generator.punctuation_candidates(text or '',language,seed):
        row=selected.get(item['selectionHash'])
        if row is None:continue
        if (row['prefix']!=item['prefix'] or row['currentWord']!=item['word'] or row['expectedBoundary']!=item['boundary']):
            raise ValueError('PUNCTUATION_SOURCE_DIVERGENCE')
        records.append(dict(id=row['id'],selectionHash=item['selectionHash'],language=language,article=article))
    return records


def recover(corpus,language,control_path,output):
    output=Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('PUNCTUATION_FRESH_OUTPUT')
    directory,manifest_sha,ru_source=CORPORA[corpus]
    manifest_path=ROOT/directory/'manifest.json';rows_path=ROOT/directory/f'punctuation-{language}.jsonl'
    if sha(manifest_path)!=manifest_sha:raise ValueError('PUNCTUATION_MANIFEST_IDENTITY')
    control_bytes=Path(control_path).read_bytes()
    controls=validate(json.loads(control_bytes))
    manifest=json.loads(manifest_path.read_text());entry=next(e for e in controls['entries'] if e['id']==corpus+'-punctuation-'+language)
    if (sha(rows_path)!=manifest['files'][rows_path.name] or entry['bindings'].get(str(rows_path.relative_to(ROOT)))!=sha(rows_path)):
        raise ValueError('PUNCTUATION_ROWS_IDENTITY')
    generator,generator_path=load_original(ROOT,manifest)
    original=next(p for p in manifest['sources'] if p.endswith('/source-lock.json'))
    lock_path=archived_source(ROOT,original,manifest['sources'][original]);lock=json.loads(lock_path.read_text())
    source=ROOT/Path(ru_source).parent/lock['languageFiles'][language];spec=lock['files'][source.name]
    if (spec['repositoryPath']!=f'20231101.{language}/train/'+source.name.split('-')[1]
            or sha(source)!=spec['sha256'] or source.stat().st_size!=spec['bytes']
            or manifest['source']['files'][source.name]!=spec['sha256']
            or lock['articleSelection']!=manifest['source']['articleSelection']):raise ValueError('PUNCTUATION_PUBLIC_SOURCE')
    rows=[json.loads(line) for line in rows_path.read_text().splitlines()]
    if len(rows)!=entry['rowCount'] or sorted({key_for(r,'punctuation') for r in rows})!=entry['keys']:
        raise ValueError('PUNCTUATION_REGISTRY_IDENTITY')
    seed=3042026 if corpus=='qualification-v2' else lock['corpusSeed'];selected=selected_rows(rows,seed)
    import pyarrow.parquet as parquet
    records=[];scanned=0;eligible=0;selection=lock['articleSelection']
    for batch in parquet.ParquetFile(source).iter_batches(batch_size=128,columns=['id','text']):
        for article,text in zip(batch.column(0).to_pylist(),batch.column(1).to_pylist(),strict=True):
            article=str(article);scanned+=1
            rank=int.from_bytes(hashlib.sha256(f"{selection['seed']}:{language}:{article}".encode()).digest()[:8],'big')
            if rank%selection['modulus']!=selection['residue']:continue
            eligible+=1;records.extend(matches(article,text,selected,generator,language,seed))
        if scanned%16384==0:print(json.dumps(dict(corpus=corpus,language=language,scanned=scanned,matches=len(records))),flush=True)
    found={r['id'] for r in records};missing=sorted({r['id'] for r in rows}-found)
    output.mkdir(parents=True,exist_ok=False);identities=output/'identities.jsonl'
    identities.write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in sorted(records,key=lambda r:(r['id'],r['article']))))
    control_snapshot=output/'source-controls.json';control_snapshot.write_bytes(control_bytes)
    paths=[manifest_path,rows_path,source,generator_path,lock_path,identities,control_snapshot]
    paths += [ROOT/'tools/typing_experiments'/p for p in ('recover_punctuation_articles.py','control_ledger.py','import_control_components.py','recover_early_ru_sources.py')]
    receipt=dict(purpose='PUNCTUATION_ARTICLE_RECOVERY_NOT_QUALIFICATION',corpus=corpus,language=language,modelCalls=0,
        bindings={str(p.relative_to(ROOT)):sha(p) for p in paths},sourceRows=len(rows),recoveredRows=len(found),missingRows=missing,
        allRowsRecovered=not missing,occurrences=len(records),articles=len({r['article'] for r in records}),scanned=scanned,eligible=eligible)
    (output/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n');print(json.dumps({k:receipt[k] for k in ('corpus','language','recoveredRows','missingRows','articles','occurrences')}),flush=True)
    if missing:raise ValueError('PUNCTUATION_RECOVERY_INCOMPLETE')


def merge(base,groups):
    result=copy.deepcopy(validate(base))
    expected={(c,l) for c in CORPORA for l in LANGUAGES}
    if {(r['corpus'],r['language']) for r,_ in groups}!=expected or len(groups)!=len(expected):raise ValueError('PUNCTUATION_RECOVERY_GROUPS')
    for receipt,records in groups:
        entry=next(e for e in result['entries'] if e['id']==receipt['corpus']+'-punctuation-'+receipt['language'])
        if (receipt.get('allRowsRecovered') is not True or receipt.get('missingRows')!=[] or receipt.get('modelCalls')!=0
                or receipt['sourceRows']!=entry['rowCount'] or receipt['recoveredRows']!=entry['rowCount']
                or len({r['id'] for r in records})!=entry['rowCount'] or receipt['occurrences']!=len(records)
                or any(r['language']!=entry['language'] for r in records)):
            raise ValueError('PUNCTUATION_RECOVERY_RECEIPT')
        entry['articleKeys']=sorted(set(entry.get('articleKeys',[]))|{article_key(r) for r in records})
        entry['articleRecovery']=dict(rows=receipt['recoveredRows'],occurrences=len(records),articles=len(entry['articleKeys']))
    return validate(result)


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='mode',required=True)
    scan=sub.add_parser('scan');scan.add_argument('--corpus',choices=tuple(CORPORA),required=True);scan.add_argument('--language',choices=LANGUAGES,required=True)
    scan.add_argument('--controls',type=Path,required=True);scan.add_argument('--output',type=Path,required=True)
    merge_parser=sub.add_parser('merge');merge_parser.add_argument('--base',type=Path,required=True);merge_parser.add_argument('--recovery-root',type=Path,required=True);merge_parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.mode=='scan':recover(args.corpus,args.language,args.controls,args.output);return
    base=load(args.base);groups=[]
    for corpus in CORPORA:
        for lang in LANGUAGES:
            directory=args.recovery_root/(corpus+'-'+lang);receipt=json.loads((directory/'receipt.json').read_text())
            for path,digest in receipt['bindings'].items():
                if sha(ROOT/path)!=digest:raise ValueError('PUNCTUATION_RECOVERY_BINDING')
            path=directory/'identities.jsonl'
            if receipt['bindings'].get(str(path.resolve().relative_to(ROOT)))!=sha(path):raise ValueError('PUNCTUATION_RECOVERY_IDENTITIES')
            rows_path=CORPORA[corpus][0]+f'/punctuation-{lang}.jsonl';rows=[json.loads(line) for line in (ROOT/rows_path).read_text().splitlines()]
            records=[json.loads(line) for line in path.read_text().splitlines()];selected={r['id']:r['template'].removeprefix(r['split']+'-punctuation-') for r in rows}
            if ({r['id'] for r in records}!=set(selected) or any(r['selectionHash']!=selected[r['id']] for r in records)):
                raise ValueError('PUNCTUATION_RECOVERY_SELECTION')
            groups.append((receipt,records))
    result=merge(base,groups)
    with args.output.open('x') as stream:stream.write(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps(dict(entries=len(result['entries']),punctuationArticles=sum(len(e.get('articleKeys',[])) for e in result['entries']))))


if __name__=='__main__':main()
