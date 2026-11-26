#!/usr/bin/env python3
"""Audit disclosed post-hoc control labels against the original observer output."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from typing_quality_slices import evaluate,read
from holdout_ledger import keys_for,load_ledger


def verify_exclusions(rows,review,ledger):
    """Reject reviewed examples whose public source article is not excluded."""
    cases=review.get('cases')
    if not isinstance(cases,list) or not cases:raise ValueError('CHAT_REVIEW_IDS')
    wanted={item['id'] for item in cases};found=set()
    blocked={key for entry in ledger['entries'] for key in entry['keys'].get('article',[])}
    for row in rows:
        if row.get('id') not in wanted:continue
        if keys_for([row],'article')-blocked:raise ValueError('CHAT_REVIEW_SOURCE_NOT_EXCLUDED')
        found.add(row['id'])
    if found!=wanted:raise ValueError('CHAT_REVIEW_MISSING')


def audit(rows,observations,review):
    evaluate(rows,observations)
    if review.get('schema')!=1 or review.get('purpose')!='POSTHOC_DISCLOSED_REGRESSION_NOT_QUALIFICATION':raise ValueError('CHAT_REVIEW_SCOPE')
    cases=review.get('cases')
    if not isinstance(cases,list) or not cases or len({x['id'] for x in cases})!=len(cases):raise ValueError('CHAT_REVIEW_IDS')
    indexed={r['id']:(r,o) for r,o in zip(rows,observations,strict=True)};counts=Counter()
    for item in cases:
        if set(item)!={'id','typed','baseline','label'} or item['label'] not in ('preserve','possible_source_typo'):
            raise ValueError('CHAT_REVIEW_SCHEMA')
        if item['id'] not in indexed:raise ValueError('CHAT_REVIEW_MISSING')
        row,obs=indexed[item['id']]
        if (row.get('edit_kind')!='control' or row.get('cohort')!='correct' or row.get('noAuto') is not True
                or row.get('typed')!=item['typed'] or row.get('expectedSpelling')!=item['typed']):
            raise ValueError('CHAT_REVIEW_ROW')
        before=obs['beforeBoundary']['text'];after=obs['afterBoundary']['text']
        if not obs['boundaryChangedBeyondInsertedSpace'] or after.casefold()==(before+' ').casefold():raise ValueError('CHAT_REVIEW_BASELINE')
        prefix=before[:-len(item['typed'])] if before.endswith(item['typed']) else None
        if prefix is None or after!=prefix+item['baseline']+' ':raise ValueError('CHAT_REVIEW_BASELINE')
        counts[item['label']]+=1
    all_noncase={r['id'] for r,o in zip(rows,observations,strict=True)
        if r.get('edit_kind')=='control' and o['boundaryChangedBeyondInsertedSpace']
        and o['afterBoundary']['text'].casefold()!=(o['beforeBoundary']['text']+' ').casefold()}
    if all_noncase!={item['id'] for item in cases}:raise ValueError('CHAT_REVIEW_INCOMPLETE')
    return dict(purpose='POSTHOC_DISCLOSED_REGRESSION_NOT_QUALIFICATION',counts=dict(sorted(counts.items())),
        unreviewedSourceControls=sum(r.get('edit_kind')=='control' for r in rows)-len(cases),
        caveat='Editorial, post-hoc cases; no population estimate or original user intent is established.',independentQualification=False)


def compare(rows,observations,review):
    """Recheck preservation expectations on a later observation, never qualify."""
    evaluate(rows,observations)
    if review.get('schema')!=1 or review.get('purpose')!='POSTHOC_DISCLOSED_REGRESSION_NOT_QUALIFICATION':raise ValueError('CHAT_REVIEW_SCOPE')
    cases=review.get('cases')
    if not isinstance(cases,list) or not cases or len({x['id'] for x in cases})!=len(cases):raise ValueError('CHAT_REVIEW_IDS')
    indexed={r['id']:(r,o) for r,o in zip(rows,observations,strict=True)};failures=[];checked=0
    for item in cases:
        if set(item)!={'id','typed','baseline','label'} or item['label'] not in ('preserve','possible_source_typo'):raise ValueError('CHAT_REVIEW_SCHEMA')
        if item['id'] not in indexed:raise ValueError('CHAT_REVIEW_MISSING')
        row,obs=indexed[item['id']]
        if (row.get('edit_kind')!='control' or row.get('cohort')!='correct' or row.get('noAuto') is not True
                or row.get('typed')!=item['typed'] or row.get('expectedSpelling')!=item['typed']):raise ValueError('CHAT_REVIEW_ROW')
        if item['label']!='preserve':continue
        checked+=1;before=obs['beforeBoundary']['text'];after=obs['afterBoundary']['text']
        if after.casefold()!=(before+' ').casefold():failures.append(item['id'])
    if not checked:raise ValueError('CHAT_REVIEW_EMPTY_PRESERVE')
    return dict(purpose='POSTHOC_DISCLOSED_REGRESSION_NOT_QUALIFICATION',checked=checked,
        preserved=checked-len(failures),failureIds=sorted(failures),independentQualification=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('rows','observations','review','ledger','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--mode',choices=('baseline','compare'),default='baseline')
    args=p.parse_args();function=audit if args.mode=='baseline' else compare
    paths={'rows':args.rows,'observations':args.observations,'review':args.review,'ledger':args.ledger}
    def digest(path):
        with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
    bindings={name:digest(path) for name,path in paths.items()}
    rows=read(args.rows);observations=read(args.observations)
    review=json.loads(args.review.read_text());ledger=load_ledger(args.ledger)
    verify_exclusions(rows,review,ledger)
    result=function(rows,observations,review)
    if any(digest(path)!=bindings[name] for name,path in paths.items()):raise ValueError('CHAT_REVIEW_INPUT_DRIFT')
    result['inputs']=bindings
    result['auditSha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with args.output.open('x') as f:json.dump(result,f,ensure_ascii=False,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(result.get('counts',{'checked':result.get('checked'),'preserved':result.get('preserved')})))

if __name__=='__main__':main()
