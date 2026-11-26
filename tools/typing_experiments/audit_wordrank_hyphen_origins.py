"""Resolve disclosed unknown word-ranking targets against their pinned source articles."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/ci'),str(ROOT/'tools/morphology')]
import historical_model_fixtures as fixtures
from ranker import PymorphyLexicon

SOURCE_LOCK=ROOT/'tools/model/rune-text-0.2/source-lock.json'
TARGET='build/typing-word-ranking/data/all-rows.jsonl'
EXPECTED={'галло','кибер','прайм'}
COMPOUND=re.compile(r'[а-яё]+(?:-[а-яё]+)+',re.IGNORECASE)


def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def derive(rows, articles, lexicon):
    unknown=[];seen=set()
    for row in rows:
        rid=row.get('id');target=row.get('expectedSpelling');article=row.get('articleId');prefix=row.get('prefix')
        if (not isinstance(rid,str) or not rid or rid in seen or row.get('language')!='ru' or
            not isinstance(target,str) or not target or not isinstance(article,str) or not article.isascii() or not article.isdecimal() or
            not isinstance(prefix,str) or not prefix):raise ValueError('HYPHEN_ROW_SCHEMA')
        seen.add(rid)
        if not lexicon.analyses(target):unknown.append(row)
    if {r['expectedSpelling'] for r in unknown}!=EXPECTED or len(unknown)!=5:
        raise ValueError('HYPHEN_UNKNOWN_SCOPE')
    out=[]
    for row in unknown:
        article=row['articleId'];text=articles.get(article)
        if not isinstance(text,str):raise ValueError('HYPHEN_ARTICLE_MISSING')
        needle=row['prefix']+row['expectedSpelling']
        if text.count(needle)!=1:raise ValueError('HYPHEN_SOURCE_MATCH')
        start=text.index(needle)+len(row['prefix']);match=COMPOUND.match(text,start)
        if match is None or match.group().split('-')[0]!=row['expectedSpelling']:
            raise ValueError('HYPHEN_SOURCE_TOKEN')
        compound=match.group();parts=compound.split('-');tails=[]
        for part in parts[1:]:
            lemmas=sorted({a.lemma for a in lexicon.analyses(part)})
            if not lemmas:raise ValueError('HYPHEN_TAIL_UNRESOLVED')
            tails.extend(lemmas)
        out.append(dict(id=row['id'],language='ru',article=article,prefix=row['prefix'].strip(),typed=compound,
                        expectedSpelling=compound,head=row['expectedSpelling'],tailFamilies=sorted(set(tails))))
    return sorted(out,key=lambda v:v['id'])


def run(parquet,output):
    import pyarrow.parquet as pq
    parquet=Path(parquet).resolve(strict=True);output=Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('HYPHEN_OUTPUT')
    lock_raw=SOURCE_LOCK.read_bytes();source=json.loads(lock_raw)['wikipediaContext']['files']['ru-0007.parquet']
    if parquet.stat().st_size!=source['bytes'] or digest(parquet)!=source['sha256']:raise ValueError('HYPHEN_SOURCE_IDENTITY')
    _,data=fixtures.verify();rows=[json.loads(x) for x in data[TARGET].splitlines()]
    dictionary=PymorphyLexicon(cache_size=16384);receipt=dictionary.receipt()
    unknown=[r for r in rows if not dictionary.analyses(r['expectedSpelling'])]
    wanted={r['articleId'] for r in unknown};articles={}
    for batch in pq.ParquetFile(parquet).iter_batches(batch_size=128,columns=['id','text']):
        for a,t in zip(batch.column(0).to_pylist(),batch.column(1).to_pylist(),strict=True):
            a=str(a)
            if a in wanted:
                if a in articles:raise ValueError('HYPHEN_ARTICLE_DUPLICATE')
                articles[a]=t
    if set(articles)!=wanted:raise ValueError('HYPHEN_ARTICLE_MISSING')
    derived=derive(rows,articles,dictionary)
    if dictionary.receipt()!=receipt or SOURCE_LOCK.read_bytes()!=lock_raw or digest(parquet)!=source['sha256']:
        raise ValueError('HYPHEN_INPUT_DRIFT')
    output.mkdir(parents=True,mode=0o700)
    data_raw=''.join(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for v in derived).encode()
    (output/'contexts.jsonl').write_bytes(data_raw)
    result=dict(scope='disclosed-historical-source-token-audit',independentQualification=False,unknownTargetRows=5,
        sourceSha256=source['sha256'],sourceLockSha256=hashlib.sha256(lock_raw).hexdigest(),
        archiveRowsSha256=hashlib.sha256(data[TARGET]).hexdigest(),contextsSha256=hashlib.sha256(data_raw).hexdigest(),
        dictionary=receipt,analyzerSha256=digest(Path(__file__)),headCounts=dict(sorted(Counter(v['head'] for v in derived).items())))
    (output/'receipt.json').write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'rows':len(derived),'headCounts':result['headCounts'],'independentQualification':False},ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--parquet',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.parquet,a.output)
