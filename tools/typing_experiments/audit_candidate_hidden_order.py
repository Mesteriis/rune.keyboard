"""Measure controller-validated hidden candidate positions in two bound replays."""
import argparse
from collections import Counter
import json
from pathlib import Path
from audit_candidate_strip_utility import digest


def measure(rows,on,off,identities):
    groups={language:Counter() for language in ('ru','en','es')};seen=set();count=0
    for row,yes,no,identity in zip(rows,on,off,identities,strict=True):
        if (identity['index']!=count or identity['sourceId']!=row['id'] or row['id'] in seen or
            any(x.get('id')!=identity['id'] or x.get('status')!='COMPLETE' or
                any(x.get(k)!=row[k] for k in ('language','typed','prefix','split')) for x in (yes,no))):
            raise ValueError('HIDDEN_ORDER_IDENTITY')
        count+=1;seen.add(row['id']);group=groups[row['language']];group['rows']+=1
        results=[]
        for obs in (yes,no):
            order=obs.get('fullCandidateOrder');view=obs['candidateView']['candidates']
            if not isinstance(order,list) or len(order)>7:raise ValueError('HIDDEN_ORDER_SCOPE')
            if any(not isinstance(x,dict) or set(x)!={'id','text'} or not isinstance(x['id'],str) or not isinstance(x['text'],str) for x in order):raise ValueError('HIDDEN_ORDER_SCHEMA')
            ids=[x['id'] for x in order]
            if len(ids)!=len(set(ids)):raise ValueError('HIDDEN_ORDER_DUPLICATE')
            visible=[{'id':x['id'],'text':x['text']} for x in view if x['role']=='CORRECTION']
            if order[:len(visible)]!=visible:raise ValueError('HIDDEN_ORDER_VISIBLE_MISMATCH')
            results.append(order)
        if row['cohort']!='typo' or row.get('ambiguous'):continue
        index=row['expectedCandidate'];candidates=row['candidates']
        if type(index)!=int or not 0<=index<len(candidates):raise ValueError('HIDDEN_ORDER_LABEL')
        target=candidates[index].strip().casefold()
        if not target:raise ValueError('HIDDEN_ORDER_LABEL')
        group['typos']+=1
        for mode,order in zip(('on','off'),results,strict=True):
            words=[x['text'].casefold() for x in order]
            if target not in words[:2] and target in words[2:7]:group['hidden3to7_'+mode]+=1
    if not count:raise ValueError('HIDDEN_ORDER_EMPTY')
    return dict(rows=count,languages={k:dict(v) for k,v in groups.items()})


def run(rows,on,off,on_ids,off_ids,on_receipt,off_receipt):
    paths=[Path(p) for p in (rows,on,off,on_ids,off_ids,on_receipt,off_receipt)]+[Path(__file__),Path(__file__).with_name('audit_candidate_strip_utility.py')]
    before=[digest(p) for p in paths]
    if before[3]!=before[4]:raise ValueError('HIDDEN_ORDER_MAPPING')
    for i,mode,observation,ids in ((5,'on',1,3),(6,'off',2,4)):
        receipt=json.loads(paths[i].read_text())
        if (receipt.get('status')!='COMPLETE' or receipt.get('deterministic') is not True or
            receipt.get('mode')!='current-product' or receipt.get('manualExpansion')!=mode or
            receipt.get('candidateOrderObserved') is not True or receipt.get('baselineMatches') is not True or
            receipt.get('baselineObservationExcludedFields')!=['fullCandidateOrder'] or
            receipt['first']['observationsSha256']!=before[observation] or receipt['hostOnlyIdentitiesSha256']!=before[ids] or
            before[0] not in receipt['files'].values()):raise ValueError('HIDDEN_ORDER_RECEIPT')
    def read(path):
        with path.open(encoding='utf-8') as stream:
            for line in stream:yield json.loads(line)
    counts=measure(*(read(paths[i]) for i in (0,1,2,3)))
    if any(json.loads(paths[i].read_text())['rows']!=counts['rows'] for i in (5,6)):raise ValueError('HIDDEN_ORDER_COUNT')
    if before!=[digest(p) for p in paths]:raise ValueError('HIDDEN_ORDER_DRIFT')
    return dict(schema=1,purpose='U14_VALIDATED_HIDDEN_ORDER_NOT_UI_ACCEPTANCE',counts=counts,
        bindings=dict(zip(('rows','on','off','onIdentities','offIdentities','onReceipt','offReceipt','audit','utility'),before,strict=True)),
        limitations=['Existing synthetic corpus; no physical device or native model.',
                     'Hypothetical full order preserves existing visible corrections first; hidden candidates remain unselectable.',
                     'No observation of user selection or practical value.'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('rows','on','off','on-ids','off-ids','on-receipt','off-receipt','output'):parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args()
    if a.output.exists():raise ValueError('HIDDEN_ORDER_OUTPUT_EXISTS')
    result=run(a.rows,a.on,a.off,a.on_ids,a.off_ids,a.on_receipt,a.off_receipt)
    a.output.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n');print(json.dumps(result['counts']))


if __name__=='__main__':main()
