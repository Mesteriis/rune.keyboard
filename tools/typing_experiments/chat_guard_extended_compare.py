#!/usr/bin/env python3
"""Compare all non-timing observer fields for disclosed RU overlay inputs."""
import argparse
from collections import Counter
import hashlib
from itertools import zip_longest
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
old_path=sys.path[:]
try:
    sys.path.insert(0,str(ROOT/'tools/eval/smart-typing-0.3/pipeline'))
    import replay_projection as projection
finally:
    sys.path[:]=old_path


def compare(rows,baseline,overlay):
    counts=Counter();fields=Counter()
    for index,(row,a,b) in enumerate(zip_longest(rows,baseline,overlay)):
        if row is None or a is None or b is None:raise ValueError('EXTENDED_COMPARE_COUNT')
        if (a.get('id')!=row['id'] or b.get('id')!=f'joint-replay-{index:08d}' or a.get('status')!='COMPLETE'
                or b.get('status')!='COMPLETE' or a.get('index')!=index or b.get('index')!=index
                or any(a.get(k)!=row[k] or b.get(k)!=row[k] for k in ('split','language','prefix','typed'))):
            raise ValueError('EXTENDED_COMPARE_IDENTITY')
        left={k:v for k,v in a.items() if k not in projection.TIMING_FIELDS}
        right={k:v for k,v in b.items() if k not in projection.TIMING_FIELDS}|{'id':a['id']}
        paths=projection.changed_paths(left,right)
        group=row.get('sourceProfile','reviewed')
        if group not in ('product-replay-v1','product-replay-history-v1','reviewed'):raise ValueError('EXTENDED_COMPARE_GROUP')
        counts[group+'Rows']+=1
        if paths:
            counts[group+'DifferentRows']+=1
            for field in {path.split('/')[1] for path in paths if path.startswith('/')}:
                fields[group+':'+field]+=1
        if a['afterBoundary']['text']!=b['afterBoundary']['text']:
            counts[group+'DifferentBoundaryTexts']+=1
    if counts['product-replay-v1Rows']!=720 or counts['product-replay-history-v1Rows']!=4000 or counts['reviewedRows']!=8:
        raise ValueError('EXTENDED_COMPARE_SCOPE')
    return dict(purpose='DISCLOSED_OVERLAY_PARITY_NOT_QUALIFICATION',counts=dict(sorted(counts.items())),
        differentFields=dict(sorted(fields.items())),independentQualification=False,
        caveat='Q7 inputs are label-free, previously disclosed and are not independent accuracy data.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('rows','baseline','overlay','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();paths={'rows':args.rows,'baseline':args.baseline,'overlay':args.overlay}
    def digest(path):
        with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
    bindings={name:digest(path) for name,path in paths.items()}
    def read(path):
        with path.open(encoding='utf-8') as stream:
            for line in stream:yield json.loads(line)
    result=compare(read(args.rows),read(args.baseline),read(args.overlay))
    if any(digest(path)!=bindings[name] for name,path in paths.items()):raise ValueError('EXTENDED_COMPARE_DRIFT')
    result['inputs']=bindings;result['sourceSha256']=digest(Path(__file__))
    with args.output.open('x') as stream:json.dump(result,stream,sort_keys=True,indent=2);stream.write('\n')
    print(json.dumps(result['counts']))

if __name__=='__main__':main()
