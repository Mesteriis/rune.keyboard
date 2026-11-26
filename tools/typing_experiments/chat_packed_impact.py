#!/usr/bin/env python3
"""Describe boundary changes from an unqualified packed rare-word candidate."""
import argparse
from collections import Counter
import hashlib
from itertools import zip_longest
import json
from pathlib import Path


def analyze(rows,baseline,candidate):
    counts=Counter()
    for index,(row,a,b) in enumerate(zip_longest(rows,baseline,candidate)):
        if row is None or a is None or b is None:raise ValueError('PACKED_IMPACT_COUNT')
        if (a.get('id')!=row['id'] or b.get('id')!=f'joint-replay-{index:08d}' or a.get('index')!=index or b.get('index')!=index
                or a.get('status')!='COMPLETE' or b.get('status')!='COMPLETE'
                or any(a.get(k)!=row[k] or b.get(k)!=row[k] for k in ('split','language','prefix','typed'))):raise ValueError('PACKED_IMPACT_IDENTITY')
        before=a['beforeBoundary']['text']
        if b['beforeBoundary']['text']!=before:raise ValueError('PACKED_IMPACT_INPUT')
        for obs in (a,b):
            after=obs['afterBoundary']['text'];flag=obs.get('boundaryChangedBeyondInsertedSpace')
            if not isinstance(after,str) or not after.endswith(' ') or type(flag) is not bool or flag!=(after!=before+' '):raise ValueError('PACKED_IMPACT_EDITOR')
        if row.get('cohort')=='unlabeled':
            counts['unlabeledRows']+=1;old=a['boundaryChangedBeyondInsertedSpace'];new=b['boundaryChangedBeyondInsertedSpace']
            counts['baselineBoundaryChanges']+=old;counts['candidateBoundaryChanges']+=new
            counts['baselineChangedCandidateUnchanged']+=old and not new
            counts['baselineUnchangedCandidateChanged']+=not old and new
            counts['differentBoundaryText']+=a['afterBoundary']['text']!=b['afterBoundary']['text']
        elif row.get('cohort')=='correct' and row.get('noAuto') is True:
            counts['reviewedRows']+=1
            counts['reviewedPreserved']+=b['afterBoundary']['text'].casefold()==(before+' ').casefold()
        else:raise ValueError('PACKED_IMPACT_COHORT')
        if b['boundaryChangedBeyondInsertedSpace'] and b.get('restoredBeforeBoundaryExactly') is not True:counts['candidateUndoFailures']+=1
    if counts['unlabeledRows']!=4720 or counts['reviewedRows']!=8:raise ValueError('PACKED_IMPACT_SCOPE')
    return dict(purpose='UNQUALIFIED_PACKED_CANDIDATE_IMPACT',independentQualification=False,counts=dict(sorted(counts.items())),
        caveat='Inputs are previously disclosed and unlabeled; change counts do not establish whether outcomes are correct.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('rows','baseline','candidate','output'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();paths={'rows':args.rows,'baseline':args.baseline,'candidate':args.candidate}
    def digest(path):
        with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
    hashes={name:digest(path) for name,path in paths.items()}
    def read(path):
        with path.open(encoding='utf-8') as stream:
            for line in stream:yield json.loads(line)
    result=analyze(read(args.rows),read(args.baseline),read(args.candidate))
    if any(digest(path)!=hashes[name] for name,path in paths.items()):raise ValueError('PACKED_IMPACT_DRIFT')
    result['inputs']=hashes;result['sourceSha256']=digest(Path(__file__))
    with args.output.open('x') as stream:json.dump(result,stream,sort_keys=True,indent=2);stream.write('\n')
    print(json.dumps(result['counts']))

if __name__=='__main__':main()
