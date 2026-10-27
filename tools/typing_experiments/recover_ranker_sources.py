"""Recover public ranker target windows after byte-identical corpus reproduction."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from holdout_ledger import keys_for,load_ledger,validate_ledger
from import_ranker_history import MANIFEST,MANIFEST_SHA,SOURCE
from recover_legacy_families import sha
from recover_legacy_holdout import load_generator
from right_context_sentence_audit import _source_hash

ROOT=Path(__file__).resolve().parents[2]
PREFIX='public-ranker-source-windows-'
PRODUCER='tools/typing_experiments/prepare_refinement.py'
PRODUCER_SHA='d2d84c3f328771fd0b9908a9216ee428eb2877079c8dacb481c42a0dafe11bab'
SEED='rune-refinement-20260915-v1'
WORD=re.compile('[а-яё]+',re.IGNORECASE)
BOUNDARY=re.compile(r'(?<=[.!?])\s+|\n+')


def verify_reproduction(original,reproduced):
    original=Path(original);reproduced=Path(reproduced)
    if sha(original/'manifest.json')!=MANIFEST_SHA or sha(reproduced/'manifest.json')!=MANIFEST_SHA:
        raise ValueError('RANKER_REPRODUCTION_MANIFEST')
    manifest=json.loads((original/'manifest.json').read_text())
    for name,digest in manifest['files'].items():
        if Path(name).name!=name or sha(original/name)!=digest or sha(reproduced/name)!=digest:
            raise ValueError('RANKER_REPRODUCTION_FILE')
    return manifest


def recover_article(article,text,rows,generator):
    """Match original sentence-local selection IDs; preserve every occurrence."""
    text=unicodedata.normalize('NFC',text or '');wanted={r['id']:r for r in rows}
    if len(wanted)!=len(rows) or any(r['articleId']!=article for r in rows):raise ValueError('RANKER_CAPTURE_ROWS')
    found={identity:set() for identity in wanted};start=0;segments=[]
    for boundary in BOUNDARY.finditer(text):
        segments.append((start,text[start:boundary.start()]));start=boundary.end()
    segments.append((start,text[start:]))
    for offset,sentence in segments:
        for ordinal,match in enumerate(WORD.finditer(sentence)):
            word=match.group()
            if ordinal<3 or word!=word.lower() or not 5<=len(word)<=12:continue
            prefix=sentence[:match.start()][-128:].lstrip()
            if not prefix or not prefix[-1].isspace():continue
            context=hashlib.sha256((prefix.lower()+'\0'+word).encode()).hexdigest()
            identity='refine-'+hashlib.sha256((SEED+':'+article+':'+str(match.start())+':'+context).encode()).hexdigest()[:24]
            if identity not in wanted:continue
            row=wanted[identity]
            if row['prefix']!=prefix or row['expectedSpelling']!=word:raise ValueError('RANKER_CAPTURE_DIVERGENCE')
            begin=offset+match.start();end=offset+match.end()
            projected=generator.bounded_prefix(text[max(0,begin-256):begin]).rstrip(' \t')
            found[identity].add(_source_hash(projected,word,text[end:end+128]))
    if any(not windows for windows in found.values()):raise ValueError('RANKER_SOURCE_CAPTURE_MISSING')
    return found


def window_entry(part,rows,windows,bindings):
    projected=[row|dict(article=row['articleId'],contextHash=window) for row in rows for window in windows[row['id']]]
    keys={axis:sorted(keys_for(projected,axis)) for axis in ('article','sentence','context')}
    entry=dict(id=PREFIX+part,usage='historical-exclusion',rowCount=len(rows),bindings=bindings,keys=keys,missingAxes=['family'],
        parentEntries=['public-ranker-history-'+part],
        notes='Byte-identical public corpus reproduction; all matching source target windows retained. Parent text-exposure article exclusions and partial family addenda remain necessary.')
    return entry,dict(rows=len(rows),articles=len(keys['article']),sourceWindows=len(keys['sentence']),contexts=len(keys['context']))


def build(root,base,reproduced,read_batches):
    root=Path(root);result=copy.deepcopy(validate_ledger(base))
    if any(e['id'].startswith(PREFIX) for e in result['entries']):raise ValueError('RANKER_WINDOWS_ALREADY_IMPORTED')
    manifest=verify_reproduction(root/Path(MANIFEST).parent,reproduced)
    if manifest['preparationScriptSha256']!=PRODUCER_SHA or sha(root/PRODUCER)!=PRODUCER_SHA:raise ValueError('RANKER_PRODUCER_IDENTITY')
    if sha(root/SOURCE)!=manifest['sourceSha256']:raise ValueError('RANKER_SOURCE_IDENTITY')
    bindings={MANIFEST:MANIFEST_SHA,SOURCE:manifest['sourceSha256'],PRODUCER:PRODUCER_SHA}
    jobs={};needed={}
    for part in ('train','dev','test'):
        parent=next(e for e in base['entries'] if e['id']=='public-ranker-history-'+part)
        for name,digest in manifest['files'].items():
            path=str(Path(MANIFEST).parent/name)
            if parent['bindings'].get(path)!=digest:raise ValueError('RANKER_PARENT_BINDING')
            bindings[path]=digest
        path=Path(MANIFEST).parent/(part+'-rows.jsonl');rows=[json.loads(line) for line in (root/path).read_text().splitlines()]
        if len(rows)!=manifest['partitions'][part]['rows'] or len({r['id'] for r in rows})!=len(rows):raise ValueError('RANKER_ROWS')
        jobs[part]=rows
        for row in rows:needed.setdefault(row['articleId'],[]).append(row)
    generator=load_generator('2cbcb2508ef66b32a60b5c7665ad96c66dc1c6477c9da4ad6dde0ea969806e65')
    remaining=set(needed);windows={}
    for articles,texts in read_batches(root/SOURCE):
        for article,text in zip(articles,texts,strict=True):
            article=str(article)
            if article in remaining:
                windows.update(recover_article(article,text,needed[article],generator));remaining.remove(article)
    if remaining:raise ValueError('RANKER_SOURCE_ARTICLES_MISSING')
    source_bindings={p:sha(root/p) for p in ('tools/typing_experiments/recover_ranker_sources.py','tools/typing_experiments/right_context_sentence_audit.py')}
    counts={}
    for part,rows in jobs.items():
        entry,counts[part]=window_entry(part,rows,windows,bindings|source_bindings);result['entries'].append(entry)
    receipt=dict(purpose='PUBLIC_RANKER_TARGET_WINDOW_EXCLUSIONS_NOT_QUALIFICATION',counts=counts,bindings=bindings,
        sourceBindings=source_bindings,reproductionManifestSha256=sha(Path(reproduced)/'manifest.json'),
        allTargetCapturesVerified=True,modelCalls=0,globalCoverageComplete=False)
    return validate_ledger(result),receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base',type=Path,required=True)
    parser.add_argument('--reproduced',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():parser.error('output already exists')
    import pyarrow.parquet as parquet
    def batches(path):
        for batch in parquet.ParquetFile(path).iter_batches(batch_size=128,columns=['id','text']):yield batch.column(0).to_pylist(),batch.column(1).to_pylist()
    ledger,receipt=build(ROOT,load_ledger(args.base),args.reproduced,batches)
    args.output.mkdir(parents=True,exist_ok=False)
    for name,value in (('ledger.json',ledger),('receipt.json',receipt)):(args.output/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps(receipt['counts']))


if __name__=='__main__':main()
