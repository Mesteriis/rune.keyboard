"""Compare two source-bound product replays with manual candidate expansion on and off."""
import argparse
from collections import Counter
import json
from pathlib import Path
from audit_candidate_strip_utility import digest


def compare(rows,on,off,identities):
    groups={lang:Counter() for lang in ('ru','en','es')}; seen=set();count=0
    for row,yes,no,identity in zip(rows,on,off,identities,strict=True):
        if (identity['index']!=count or identity['sourceId']!=row['id'] or row['id'] in seen or
                identity['id']!=yes['id'] or identity['id']!=no['id'] or
                any(item.get('status')!='COMPLETE' or any(item.get(k)!=row[k] for k in ('language','typed','prefix','split')) for item in (yes,no))):
            raise ValueError('STRIP_COMPARISON_IDENTITY')
        seen.add(row['id']);count+=1;metrics=groups[row['language']];metrics['rows']+=1
        for key in ('candidateView','afterBoundary','afterBackspace','restoredBeforeBoundaryExactly'):
            if key not in yes or key not in no:raise ValueError('STRIP_COMPARISON_OBSERVATION')
        if yes['candidateView']!=no['candidateView']:metrics['visibleViewChanges']+=1
        def visible_text(obs):
            return [(item['role'],item['text']) for item in obs['candidateView']['candidates']]
        if visible_text(yes)!=visible_text(no):metrics['visibleTextChanges']+=1
        if yes['candidateView'].get('selectedCandidateId')!=no['candidateView'].get('selectedCandidateId'):
            metrics['selectedIdChanges']+=1
        if yes['afterBoundary']!=no['afterBoundary']:metrics['boundaryChanges']+=1
        if yes['afterBackspace']!=no['afterBackspace'] or yes['restoredBeforeBoundaryExactly']!=no['restoredBeforeBoundaryExactly']:
            metrics['undoChanges']+=1
        if row['cohort']!='typo' or row.get('ambiguous'):continue
        index=row['expectedCandidate'];candidates=row['candidates']
        if type(index)!=int or not 0<=index<len(candidates):raise ValueError('STRIP_COMPARISON_LABEL')
        target=candidates[index].strip().casefold()
        if not target:raise ValueError('STRIP_COMPARISON_LABEL')
        metrics['typos']+=1
        def found(obs):
            return target in {item['text'].casefold() for item in obs['candidateView']['candidates'] if item['role']=='CORRECTION'}
        a=found(yes);b=found(no)
        if a:metrics['targetVisibleOn']+=1
        if b:metrics['targetVisibleOff']+=1
        if a and not b:metrics['targetGainedOn']+=1
        if b and not a:metrics['targetLostOn']+=1
    if not count:raise ValueError('STRIP_COMPARISON_EMPTY')
    return dict(rows=count,languages={lang:dict(counts) for lang,counts in groups.items()})


def run(rows,on,off,on_ids,off_ids,on_receipt,off_receipt):
    paths=[Path(p) for p in (rows,on,off,on_ids,off_ids,on_receipt,off_receipt)]+[Path(__file__),Path(__file__).with_name('audit_candidate_strip_utility.py')]
    before=[digest(p) for p in paths]
    if before[3]!=before[4]:raise ValueError('STRIP_IDENTITY_MAPPING')
    for n,mode,output,ids in ((5,'on',1,3),(6,'off',2,4)):
        receipt=json.loads(paths[n].read_text())
        if (receipt.get('status')!='COMPLETE' or receipt.get('mode')!='current-product' or receipt.get('manualExpansion')!=mode or
                receipt.get('deterministic') is not True or receipt['first']['observationsSha256']!=before[output] or
                receipt['hostOnlyIdentitiesSha256']!=before[ids] or before[0] not in receipt['files'].values()):
            raise ValueError('STRIP_COMPARISON_RECEIPT')
    def read(path):
        with path.open(encoding='utf-8') as f:
            for line in f:yield json.loads(line)
    counts=compare(*(read(paths[i]) for i in (0,1,2,3)))
    if any(json.loads(paths[i].read_text())['rows']!=counts['rows'] for i in (5,6)):raise ValueError('STRIP_COMPARISON_COUNT')
    if before!=[digest(p) for p in paths]:raise ValueError('STRIP_COMPARISON_DRIFT')
    return dict(schema=1,purpose='U14_CURRENT_VISIBLE_STRIP_ON_OFF_COMPARISON_NOT_QUALIFICATION',counts=counts,
                bindings=dict(zip(('rows','on','off','onIdentities','offIdentities','onReceipt','offReceipt','audit','utility'),before,strict=True)),
                limitations=['Observed current visible candidates only, not positions 3–7.',
                             'Synthetic regression corpus; no native model calls or device behavior.',
                             'Setting on/off may change existing suggestions and is not a UI expansion parity test.'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('rows','on','off','on-ids','off-ids','on-receipt','off-receipt','output'):parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args()
    if a.output.exists():raise ValueError('STRIP_OUTPUT_EXISTS')
    result=run(a.rows,a.on,a.off,a.on_ids,a.off_ids,a.on_receipt,a.off_receipt)
    a.output.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps(result['counts']))


if __name__=='__main__':main()
