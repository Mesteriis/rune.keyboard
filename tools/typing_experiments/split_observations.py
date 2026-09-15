#!/usr/bin/env python3
"""Route source-bound candidate observations without scoring or fitting any labels."""
from pathlib import Path
import argparse
import hashlib
import json
ROOT=Path(__file__).resolve().parents[2]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,obj):Path(path).write_text(json.dumps(obj,sort_keys=True,indent=2)+'\n')
def split(data,export,output):
    manifest=json.loads((data/'manifest.json').read_text())
    if manifest.get('containsPersonalMessages') is not False:raise ValueError('PUBLIC_DATA_REQUIRED')
    receipt=json.loads((export/'receipt.json').read_text())
    for path,digest in receipt['files'].items():
        if sha(path)!=digest:raise ValueError('EXPORT_IDENTITY')
    expected=[]
    for part in ('train','dev','test'):
        path=data/f'{part}-rows.jsonl'
        if sha(path)!=manifest['files'][path.name]:raise ValueError('ROW_IDENTITY')
        expected.extend(json.loads(s) for s in path.read_text().splitlines())
    actual=[json.loads(s) for s in (export/'rows.jsonl').read_text().splitlines()]
    observations=[json.loads(s) for s in (export/'observations.jsonl').read_text().splitlines()]
    if actual!=expected or len(actual)!=len(observations):raise ValueError('EXPORT_ALIGNMENT')
    output.mkdir(parents=True,exist_ok=False)
    for part in ('train','dev','test'):
        records=[]
        for i,(r,o) in enumerate(zip(actual,observations)):
            if o['index']!=i or o['generation']['original']!=r['typed']:raise ValueError('CANDIDATE_ALIGNMENT')
            if r['partition']==part:records.append({'row':r,'observation':o})
        (output/f'{part}.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records))
    write(output/'manifest.json',{'schema':1,'dataManifest':str(data/'manifest.json'),'dataManifestSha256':sha(data/'manifest.json'),
        'exportReceipt':str(export/'receipt.json'),'exportReceiptSha256':sha(export/'receipt.json'),
        'partitions':{part:sha(output/f'{part}.jsonl') for part in ('train','dev','test')}})
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--export',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();split(a.data.resolve(),a.export.resolve(),a.output.resolve())
