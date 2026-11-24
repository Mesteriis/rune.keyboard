#!/usr/bin/env python3
"""Describe chat-regression product observations; never qualify a policy."""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path

from typing_quality_slices import evaluate,read


def wilson(success,total):
    if type(success) is not int or type(total) is not int or not 0<=success<=total:raise ValueError('CHAT_COUNT')
    if total==0:return None
    z=1.959963984540054;p=success/total;den=1+z*z/total
    center=(p+z*z/(2*total))/den;radius=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/den
    return dict(lower=max(0,center-radius),upper=min(1,center+radius))


def report(rows,observations):
    overall=evaluate(rows,observations)
    groups=defaultdict(lambda:([],[]));clusters={}
    for row,obs in zip(rows,observations,strict=True):
        if row.get('register')!='chat-shaped-lowercase' or row.get('language')!='ru' or row.get('purpose')!='DISCLOSED_REGRESSION_NOT_QUALIFICATION':raise ValueError('CHAT_SCOPE')
        cluster=row.get('clusterId');kind=row.get('edit_kind')
        if not isinstance(cluster,str) or not cluster or not isinstance(kind,str) or not kind:raise ValueError('CHAT_GROUP')
        if (kind=='control' and (row.get('cohort')!='correct' or row.get('noAuto') is not True or row.get('typed')!=row.get('expectedSpelling'))
                or (kind!='control' and (row.get('cohort')!='typo' or row.get('noAuto') is not False))):
            raise ValueError('CHAT_COHORT')
        groups[kind][0].append(row);groups[kind][1].append(obs)
        if row.get('cohort')=='correct':
            changed=obs['boundaryChangedBeyondInsertedSpace'];clusters[cluster]=clusters.get(cluster,False) or changed
    slices={kind:evaluate(*group)['slices']['all'] for kind,group in sorted(groups.items())}
    controls=slices.get('control',{});control_rows=controls.get('rows',0);control_changes=controls.get('controlChanges',0)
    cluster_changes=sum(clusters.values());cluster_count=len(clusters)
    return dict(schema=1,purpose='DESCRIPTIVE_CHAT_REGRESSION_NOT_QUALIFICATION',language='ru',
        overall=overall['slices']['all'],byEditKind=slices,
        controlRows=dict(changed=control_changes,total=control_rows,wilson95=wilson(control_changes,control_rows)),
        controlClusters=dict(changed=cluster_changes,total=cluster_count,wilson95=wilson(cluster_changes,cluster_count)),
        caveats=['Tatoeba sentences are previously exposed; this is not a holdout.',
                 'Source control spellings are not independently verified and may contain typos; changes are not necessarily false corrections.',
                 'Wilson intervals are descriptive and do not account for correlated sentences or authors.',
                 'Synthetic edits may be valid words and do not prove user intent.',
                 'Token replay does not measure accumulated phrase revisions.'],independentQualification=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('rows','observations','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();result=report(read(args.rows),read(args.observations))
    result['inputs']={name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in [('rows',args.rows),('observations',args.observations)]}
    with args.output.open('x') as f:json.dump(result,f,ensure_ascii=False,sort_keys=True,indent=2);f.write('\n')

if __name__=='__main__':main()
