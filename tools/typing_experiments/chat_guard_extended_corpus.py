#!/usr/bin/env python3
"""Prepare disclosed RU parity inputs plus reviewed cases for overlay comparison."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
old_path=sys.path[:]
try:
    sys.path.insert(0,str(ROOT/'tools/ci'))
    import product_replay_ci as ci
finally:
    sys.path[:]=old_path


def assemble(profiles,review,chat_rows):
    if review.get('purpose')!='POSTHOC_DISCLOSED_REGRESSION_NOT_QUALIFICATION':raise ValueError('EXTENDED_REVIEW_SCOPE')
    wanted={x['id'] for x in review['cases'] if x['label']=='preserve'}
    if len(wanted)!=8:raise ValueError('EXTENDED_REVIEW_COUNT')
    rows=[];counts={}
    for name,observations in profiles:
        current=0
        for item in observations:
            if item.get('language')!='ru':continue
            if item.get('status')!='COMPLETE' or any(not isinstance(item.get(k),str) for k in ('id','split','prefix','typed')):
                raise ValueError('EXTENDED_INPUT')
            rows.append(dict(id='extended-'+name+'-'+item['id'],split=item['split'],language='ru',prefix=item['prefix'],typed=item['typed'],
                expectedSpelling=item['typed'],cohort='unlabeled',noAuto=False,sourceProfile=name))
            current+=1
        counts[name]=current
    found=set()
    for row in chat_rows:
        if row.get('id') in wanted:
            if row.get('cohort')!='correct' or row.get('noAuto') is not True:raise ValueError('EXTENDED_REVIEW_ROW')
            rows.append(row);found.add(row['id'])
    if found!=wanted or len({r['id'] for r in rows})!=len(rows):raise ValueError('EXTENDED_IDENTITIES')
    counts['reviewed']=len(found)
    return rows,counts


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('review','chat-rows','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();output=args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('EXTENDED_OUTPUT')
    ci.validate();ci.validate_history()
    names=('product-replay-v1','product-replay-history-v1')
    paths=[ROOT/'tools/ci'/name/'baseline.jsonl.gz' for name in names]
    def digest(path):
        with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
    hashes={name:digest(path) for name,path in zip(names,paths,strict=True)}
    def observations(path):
        with gzip.open(path,'rt',encoding='utf-8') as stream:
            for line in stream:yield json.loads(line)
    review_raw=args.review.read_bytes();chat_raw=args.chat_rows.read_bytes();review=json.loads(review_raw)
    rows,counts=assemble([(name,observations(path)) for name,path in zip(names,paths,strict=True)],review,
        (json.loads(line) for line in chat_raw.splitlines() if line.strip()))
    if counts!={'product-replay-v1':720,'product-replay-history-v1':4000,'reviewed':8}:raise ValueError('EXTENDED_SOURCE_COUNT')
    for name,path in zip(names,paths,strict=True):
        with path.open('rb') as stream:
            if hashlib.file_digest(stream,'sha256').hexdigest()!=hashes[name]:raise ValueError('EXTENDED_INPUT_DRIFT')
    if args.review.read_bytes()!=review_raw or args.chat_rows.read_bytes()!=chat_raw:raise ValueError('EXTENDED_INPUT_DRIFT')
    payload=''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for r in rows).encode()
    output.mkdir(parents=True);(output/'rows.jsonl').write_bytes(payload)
    manifest=dict(purpose='DISCLOSED_PARITY_AND_REVIEW_NOT_QUALIFICATION',counts=counts,rowsSha256=hashlib.sha256(payload).hexdigest(),
        baselineSha256=hashes,reviewSha256=hashlib.sha256(review_raw).hexdigest(),chatRowsSha256=hashlib.sha256(chat_raw).hexdigest(),
        generatorSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),independentQualification=False,
        caveat='Parity inputs are unlabeled; expectedSpelling is a transport placeholder and is not a correctness label.')
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2)+'\n');print(json.dumps(counts))

if __name__=='__main__':main()
