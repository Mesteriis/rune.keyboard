"""Recover early RU spelling source articles using exact archived selection rules."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path

from holdout_ledger import load_ledger
from import_early_ru_history import CORPORA,PREFIX,ROOT
from recover_legacy_families import sha
from recover_legacy_holdout import LegacySelections


def archived_source(root,original,digest):
    directory=Path(root)/'tools/typing_experiments/frozen_sources'
    entry=json.loads((directory/'manifest.json').read_text())['sources'][digest]
    path=directory/entry['file']
    if entry['originalPath']!=original or path.parent!=directory or sha(path)!=digest:
        raise ValueError('EARLY_RECOVERY_ARCHIVE_IDENTITY')
    return path


def article_selected(article,selection):
    if (not isinstance(article,str) or not article.isascii() or not article.isdecimal()
            or type(selection.get('seed')) is not int or type(selection.get('modulus')) is not int
            or selection['modulus']<=0 or type(selection.get('residue')) is not int
            or not 0<=selection['residue']<selection['modulus']):
        raise ValueError('EARLY_RECOVERY_ARTICLE_SELECTION')
    rank=int.from_bytes(hashlib.sha256(f"{selection['seed']}:ru:{article}".encode()).digest()[:8],'big')
    return rank%selection['modulus']==selection['residue']


def prepare_selection(rows,generator,seed,generator_sha):
    adapted=[]
    for row in rows:
        split=row.get('split')
        if row.get('language')!='ru' or row.get('task')!='spelling' or split not in ('calibration','holdout'):
            raise ValueError('EARLY_RECOVERY_ROW_SCOPE')
        prefix=split+'-wikipedia-';template=row.get('template')
        if not isinstance(template,str) or not template.startswith(prefix):
            raise ValueError('EARLY_RECOVERY_TEMPLATE')
        adapted.append(row|dict(template='holdout-wikipedia-'+template.removeprefix(prefix)))
    return LegacySelections(adapted,generator,seed,generator_sha)


def recover(corpus,base_path,output):
    root=ROOT;output=Path(output).resolve()
    if output.exists() or not output.is_relative_to(root/'build'):
        raise ValueError('EARLY_RECOVERY_FRESH_OUTPUT')
    directory,manifest_sha,source=CORPORA[corpus]
    manifest_path=root/directory/'manifest.json';rows_path=root/directory/'spelling-ru.jsonl'
    if sha(manifest_path)!=manifest_sha:raise ValueError('EARLY_RECOVERY_MANIFEST')
    manifest=json.loads(manifest_path.read_text())
    parent=next(e for e in load_ledger(base_path)['entries'] if e['id']==PREFIX+corpus)
    if (sha(rows_path)!=parent['bindings'][str(rows_path.relative_to(root))]
            or sha(rows_path)!=manifest['files']['spelling-ru.jsonl']
            or sha(root/source)!=manifest['source']['files'][Path(source).name]):
        raise ValueError('EARLY_RECOVERY_INPUT')
    generator_original=next(p for p in manifest['sources'] if p.endswith('/generate_corpus.py'))
    lock_original=next(p for p in manifest['sources'] if p.endswith('/source-lock.json'))
    generator_sha=manifest['sources'][generator_original]
    generator_path=archived_source(root,generator_original,generator_sha)
    lock_path=archived_source(root,lock_original,manifest['sources'][lock_original])
    lock=json.loads(lock_path.read_text())
    if (lock['articleSelection']!=manifest['source']['articleSelection']
            or lock['languageFiles']['ru']!=Path(source).name
            or lock['files'][Path(source).name]['sha256']!=sha(root/source)
            or lock['files'][Path(source).name]['bytes']!=(root/source).stat().st_size):
        raise ValueError('EARLY_RECOVERY_SOURCE_LOCK')
    # v2 passes this literal in its archived build(); v3/v4 read corpusSeed.
    seed=3042026 if corpus=='qualification-v2' else lock['corpusSeed']
    spec=importlib.util.spec_from_file_location('frozen_early_'+generator_sha,generator_path)
    generator=importlib.util.module_from_spec(spec);spec.loader.exec_module(generator)
    rows=[json.loads(line) for line in rows_path.read_text().splitlines()]
    selection=prepare_selection(rows,generator,seed,generator_sha)
    import pyarrow.parquet as parquet
    records=[];scanned=0;eligible=0
    for batch in parquet.ParquetFile(root/source).iter_batches(batch_size=128,columns=['id','text']):
        for article,text in zip(batch.column(0).to_pylist(),batch.column(1).to_pylist(),strict=True):
            scanned+=1;article=str(article)
            if not article_selected(article,lock['articleSelection']):continue
            eligible+=1;records.extend(selection.recover_article(article,text))
        if scanned%8192==0:print(json.dumps(dict(corpus=corpus,scanned=scanned,occurrences=len(records))),flush=True)
    matched=Counter(r['id'] for r in records);missing=sorted({r['id'] for r in rows}-matched.keys())
    output.mkdir(parents=True,exist_ok=False)
    identities=output/'identities.jsonl'
    identities.write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in sorted(records,key=lambda r:(r['id'],r['article'],r['contextHash']))))
    bindings={str(p.relative_to(root)):sha(p) for p in (manifest_path,rows_path,root/source,generator_path,lock_path,identities,
        root/'tools/typing_experiments/recover_early_ru_sources.py',root/'tools/typing_experiments/import_early_ru_history.py',
        root/'tools/typing_experiments/recover_legacy_holdout.py',root/'tools/typing_experiments/right_context_sentence_audit.py')}
    receipt=dict(purpose='EARLY_RU_SOURCE_RECOVERY_NOT_QUALIFICATION',corpus=corpus,bindings=bindings,
        sourceArticlesScanned=scanned,eligibleArticles=eligible,corpusSeed=seed,articleSelection=lock['articleSelection'],
        sourceRows=len(rows),recoveredRows=len(matched),missingRows=missing,allRowsRecovered=not missing,
        matchedOccurrences=len(records),articles=len({r['article'] for r in records}),modelCalls=0,
        projection='Current whole-article 256-char prefix input / 128-char suffix source-window hash; not a full-sentence hash')
    (output/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:receipt[k] for k in ('corpus','sourceRows','recoveredRows','missingRows','articles','matchedOccurrences')}),flush=True)
    if missing:raise ValueError('EARLY_RECOVERY_INCOMPLETE')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus',choices=tuple(CORPORA),required=True);parser.add_argument('--base',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    recover(args.corpus,args.base,args.output)


if __name__=='__main__':main()
