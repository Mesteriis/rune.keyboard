"""Inspect source-token boundaries of disclosed historical word-ranking targets."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/ci'))
import historical_model_fixtures as fixtures

SOURCE_LOCK=ROOT/'tools/model/rune-text-0.2/source-lock.json'
ARCHIVE='build/typing-word-ranking/data/all-rows.jsonl'
HYPHENS='-‐‑–'
TOKEN=re.compile(r'\w+(?:[-‐‑–]\w+)*',re.UNICODE)


def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def inspect(rows,articles):
    counts=Counter();affected=[];ids=set()
    for row in rows:
        rid=row.get('id');target=row.get('expectedSpelling');prefix=row.get('prefix');article=row.get('articleId')
        if (not isinstance(rid,str) or not rid or rid in ids or row.get('language')!='ru' or
            not isinstance(target,str) or not target or not isinstance(prefix,str) or not prefix or
            not isinstance(article,str) or not article.isascii() or not article.isdecimal()):raise ValueError('SOURCE_BOUNDARY_ROW')
        ids.add(rid);text=articles.get(article)
        if not isinstance(text,str):raise ValueError('SOURCE_BOUNDARY_ARTICLE')
        needle=prefix+target;positions=[m.start()+len(prefix) for m in re.finditer(re.escape(needle),text)]
        if not positions:raise ValueError('SOURCE_BOUNDARY_MISSING')
        endings=[]
        for start in positions:
            end=start+len(target);before=text[start-1:start] if start else '';after=text[end:end+1]
            if before and (before.isalnum() or before in HYPHENS):raise ValueError('SOURCE_BOUNDARY_LEFT')
            if after and after in HYPHENS:
                token=TOKEN.match(text,start)
                if token is None or not token.group().startswith(target+after) or token.end()<=end+1:
                    raise ValueError('SOURCE_BOUNDARY_COMPOUND')
                endings.append(('hyphen',token.group()))
            elif after and after.isalnum():
                token=TOKEN.match(text,start)
                if token is None or not token.group().startswith(target) or token.end()<=end:
                    raise ValueError('SOURCE_BOUNDARY_MIXED')
                endings.append(('alphanumeric',token.group()))
            else:endings.append(('standalone',target))
        counts['rows']+=1
        if len(positions)>1:counts['multipleSourceMatches']+=1
        classes={x[0] for x in endings}
        if len(classes)!=1 or len({x[1] for x in endings})!=1:
            counts['ambiguousBoundary']+=1
            continue
        kind,full=endings[0];counts[kind+'Rows']+=1
        if kind!='standalone':
            affected.append(dict(id=rid,language='ru',article=article,prefix=prefix.strip(),typed=full,
                                 expectedSpelling=full,head=target,boundaryKind=kind))
    if not ids:raise ValueError('SOURCE_BOUNDARY_EMPTY')
    return sorted(affected,key=lambda r:r['id']),dict(sorted(counts.items()))


def run(parquet,output):
    import pyarrow.parquet as pq
    parquet=Path(parquet).resolve(strict=True);output=Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('SOURCE_BOUNDARY_OUTPUT')
    lock=SOURCE_LOCK.read_bytes();source=json.loads(lock)['wikipediaContext']['files']['ru-0007.parquet']
    if parquet.stat().st_size!=source['bytes'] or digest(parquet)!=source['sha256']:raise ValueError('SOURCE_BOUNDARY_IDENTITY')
    _,archive=fixtures.verify();raw=archive[ARCHIVE];rows=[json.loads(line) for line in raw.splitlines()]
    wanted={r['articleId'] for r in rows};articles={}
    for batch in pq.ParquetFile(parquet).iter_batches(batch_size=128,columns=['id','text']):
        for article,text in zip(batch.column(0).to_pylist(),batch.column(1).to_pylist(),strict=True):
            article=str(article)
            if article in wanted:
                if article in articles:raise ValueError('SOURCE_BOUNDARY_DUPLICATE_ARTICLE')
                articles[article]=unicodedata.normalize('NFC',text or '')
    if set(articles)!=wanted:raise ValueError('SOURCE_BOUNDARY_ARTICLE')
    affected,counts=inspect(rows,articles)
    if SOURCE_LOCK.read_bytes()!=lock or digest(parquet)!=source['sha256']:raise ValueError('SOURCE_BOUNDARY_DRIFT')
    output.mkdir(parents=True,mode=0o700)
    payload=''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for r in affected).encode()
    (output/'contexts.jsonl').write_bytes(payload)
    receipt=dict(scope='disclosed-historical-source-boundary-audit',independentQualification=False,counts=counts,
        sourceArticles=len(wanted),sourceSha256=source['sha256'],sourceLockSha256=hashlib.sha256(lock).hexdigest(),
        archiveRowsSha256=hashlib.sha256(raw).hexdigest(),contextsSha256=hashlib.sha256(payload).hexdigest(),
        analyzerSha256=digest(Path(__file__)))
    (output/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps(receipt['counts'],sort_keys=True))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--parquet',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.parquet,a.output)
