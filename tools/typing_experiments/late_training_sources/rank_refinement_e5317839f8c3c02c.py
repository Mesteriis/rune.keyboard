#!/usr/bin/env python3
"""Bounded numeric CatBoost comparison; dev selection precedes a separate test command."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import struct
import numpy as np
from catboost import CatBoostClassifier, CatBoostRanker, Pool
import train as baseline

ROOT = Path(__file__).resolve().parents[2]
ENDINGS = ('ть','ти','ет','ют','ут','ит','ат','ят','ла','ли','ый','ий','ая','яя','ое','ее','ые','ие','ого','ему','ому','ой','ей','ам','ям','ах','ях','ом','ем','ов','ев','а','я','ы','и','у','ю','о','е','ь')
PREPOSITIONS = ('в','на','с','к','по','из','от','до','для','у','о','об','без','за','под','над','перед','при','через','между')
FEATURES = 22 + 13 + len(ENDINGS) + len(PREPOSITIONS)


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path, obj): Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True,allow_nan=False)+'\n')

def features(context, original, candidate):
    a, b = original.lower(), candidate['text'].lower()
    n = max(len(a),len(b),1)
    prefix = 0
    for x,y in zip(a,b):
        if x != y: break
        prefix += 1
    suffix = 0
    for x,y in zip(a[::-1],b[::-1]):
        if x != y: break
        suffix += 1
    def overlap(k):
        left={a[i:i+k] for i in range(max(0,len(a)-k+1))}
        right={b[i:i+k] for i in range(max(0,len(b)-k+1))}
        return len(left&right)/max(1,len(left|right))
    substitution = len(a)==len(b) and sum(x!=y for x,y in zip(a,b))==1
    transposition = len(a)==len(b) and any(a[:i]+a[i+1]+a[i]+a[i+2:]==b for i in range(len(a)-1))
    # Names describe the corruption in the typed token, not the repair direction.
    missing = len(b)==len(a)+1 and any(b[:i]+b[i+1:]==a for i in range(len(b)))
    extra = len(a)==len(b)+1 and any(a[:i]+a[i+1:]==b for i in range(len(a)))
    repeat = extra and any(a[i]==a[i+1] and a[:i]+a[i+1:]==b for i in range(len(a)-1))
    previous = context[-128:].lower().split()
    prev = previous[-1] if previous else ''
    return baseline.features(context,original,candidate) + [
        prefix/n,suffix/n,(len(b)-len(a))/max(n,1),overlap(2),overlap(3),
        float(substitution),float(transposition),float(missing),float(extra),float(repeat),
        min(len(a),32)/32,min(len(b),32)/32,float(a[:1]==b[:1]),
    ] + [float(b.endswith(e)) for e in ENDINGS] + [float(prev==p) for p in PREPOSITIONS]


def load_groups(path):
    result=[]
    for line in Path(path).read_text().splitlines():
        item=json.loads(line);r,o=item['row'],item['observation']
        assert r['typed']==o['generation']['original']
        cs=o['generation']['alternatives']
        if cs: result.append((r,cs,np.array([c['text'].lower()==r['expectedSpelling'].lower() for c in cs],dtype=int)))
    return result


def verified_groups(path, partition, *, allow_test=False):
    path=Path(path).resolve()
    if partition not in (('train','dev','test') if allow_test else ('train','dev')) or path.name != partition+'.jsonl': raise ValueError('TRAIN_DEV_ONLY')
    binding=json.loads((path.parent/'manifest.json').read_text())
    if sha(path)!=binding['partitions'][partition]: raise ValueError('OBSERVATION_IDENTITY')
    data_path=Path(binding['dataManifest'])
    if sha(data_path)!=binding['dataManifestSha256']: raise ValueError('MANIFEST_IDENTITY')
    manifest=json.loads(data_path.read_text())
    if manifest.get('containsPersonalMessages') is not False: raise ValueError('PUBLIC_DATA_REQUIRED')
    source=json.loads((ROOT/'tools/model/rune-text-0.2/source-lock.json').read_text())
    if manifest['sourceSha256']!=source['wikipediaContext']['files']['ru-0007.parquet']['sha256']: raise ValueError('PUBLIC_SOURCE_IDENTITY')
    receipt_path=Path(binding['exportReceipt'])
    if sha(receipt_path)!=binding['exportReceiptSha256']: raise ValueError('RECEIPT_IDENTITY')
    receipt=json.loads(receipt_path.read_text())
    for name,digest in receipt['files'].items():
        if sha(name)!=digest: raise ValueError('EXPORT_IDENTITY')
    for name,digest in receipt['sources'].items():
        if '/smarttyping/lexicon/' in name or '/smarttyping/correction/' in name or name.endswith('/ProductionCandidates.kt'):
            if sha(name)!=digest: raise ValueError('GENERATOR_SOURCE_CHANGED')
    row_path=data_path.parent/(partition+'-rows.jsonl')
    if sha(row_path)!=manifest['files'][row_path.name]: raise ValueError('PUBLIC_ROWS_IDENTITY')
    rows=[json.loads(line) for line in row_path.read_text().splitlines()]
    records=[json.loads(line) for line in path.read_text().splitlines()]
    if [item['row'] for item in records]!=rows or any(r['partition']!=partition for r in rows): raise ValueError('ROW_PARTITION_ALIGNMENT')
    return load_groups(path)


def export_tree(model, path, count):
    json_path=Path(path).with_suffix('.json');model.save_model(str(json_path),format='json')
    obj=json.loads(json_path.read_text());scale,bias=obj['scale_and_bias'];trees=obj['oblivious_trees']
    assert len(bias)==1 and 0<len(trees)<=128
    blob=b'RET1' if count==22 else b'RET2'
    blob+=struct.pack('<IIff',count,len(trees),scale,bias[0])
    for t in trees:
        splits=t['splits'];assert 1<=len(splits)<=6
        blob+=struct.pack('<I',len(splits))
        for s in splits:
            assert s['split_type']=='FloatFeature' and 0<=s['float_feature_index']<count
            blob+=struct.pack('<If',s['float_feature_index'],s['border'])
        assert all(math.isfinite(v) and abs(v)<=32 for v in t['leaf_values'])
        blob+=np.asarray(t['leaf_values'],dtype='<f4').tobytes()
    assert len(blob)<=65536
    Path(path).write_bytes(blob)


def tree_score(blob, vector):
    assert blob[:4] in (b'RET1',b'RET2')
    n,count,scale,bias=struct.unpack_from('<IIff',blob,4);assert len(vector)==n
    offset=20;result=0
    for _ in range(count):
        depth,=struct.unpack_from('<I',blob,offset);offset+=4;leaf=0
        for d in range(depth):
            index,border=struct.unpack_from('<If',blob,offset);offset+=8
            if np.float32(vector[index])>border: leaf|=1<<d
        values=struct.unpack_from('<'+'f'*(1<<depth),blob,offset);offset+=4*(1<<depth)
        result+=values[leaf]
    assert offset==len(blob)
    return float(result*scale+bias)


def scores(path, groups):
    blob=Path(path).read_bytes();fn=baseline.features if blob[:4]==b'RET1' else features
    return [[.8*math.tanh(tree_score(blob,fn(r['prefix'],r['typed'],c))/4) for c in cs] for r,cs,_ in groups]


def accuracy(groups, values):
    return sum(int(y[np.argmax(v)]) for (_,_,y),v in zip(groups,values))


def fit(args):
    root=Path(args.output);root.mkdir(parents=True,exist_ok=False)
    train=verified_groups(args.train,'train');dev=verified_groups(args.dev,'dev')
    assert not ({r['articleId'] for r,_,_ in train}&{r['articleId'] for r,_,_ in dev})
    write(root/'freeze.json',{'trainSha256':sha(args.train),'devSha256':sha(args.dev),
          'scriptSha256':sha(__file__),'features':FEATURES,'models':['current22','enriched','pairwise'],
          'blendGains':[0,.25,.5,1], 'seed':15092026,'selection':'best dev top1; ties prefer smaller artifact'})
    result={};all_scores={}
    for name,fn,kind,iters,depth in [('current22',baseline.features,'classifier',80,4),('enriched',features,'classifier',80,5),('pairwise',features,'ranker',128,5)]:
        samples=[(r,cs,y) for r,cs,y in train if y.sum() and len(y)>1]
        x=np.array([fn(r['prefix'],r['typed'],c) for r,cs,y in samples for c in cs]);y=np.concatenate([y for r,cs,y in samples])
        common=dict(iterations=iters,depth=depth,learning_rate=.05,random_seed=15092026,thread_count=2,verbose=False,allow_writing_files=False)
        if kind=='ranker':
            model=CatBoostRanker(loss_function='PairLogitPairwise',**common)
            group_ids=np.concatenate([np.full(len(cs),i) for i,(r,cs,y) in enumerate(samples)])
            model.fit(Pool(x,y,group_id=group_ids))
        else:
            model=CatBoostClassifier(loss_function='Logloss',**common);model.fit(x,y)
        model.save_model(str(root/f'{name}.cbm'))
        path=root/f'{name}.bin';export_tree(model,path,x.shape[1]);values=scores(path,dev)
        vectors=np.array([fn(r['prefix'],r['typed'],c) for r,cs,y in dev for c in cs])
        host=model.predict(vectors,**({'prediction_type':'RawFormulaVal'} if kind=='classifier' else {}))
        exported=np.array([tree_score(path.read_bytes(),v) for v in vectors]);error=float(np.max(np.abs(host-exported)))
        assert error<1e-5
        result[name]={'correctTop1':accuracy(dev,values),'bytes':path.stat().st_size,'sha256':sha(path),'parityMaxError':error,'parityCandidates':len(vectors),'fitGroups':len(samples)}
        all_scores[name]=values
    old=ROOT/'tools/typing_experiments/baseline/ru-ranker.bin'
    oldvalues=scores(old,dev);all_scores['shipped']=oldvalues
    result['shipped']={'correctTop1':accuracy(dev,oldvalues),'bytes':old.stat().st_size,'sha256':sha(old)}
    selection=max(result,key=lambda k:(result[k]['correctTop1'],-result[k]['bytes']))
    report={'rowsWithAlternatives':len(dev),'expectedAvailable':sum(int(y.sum()>0) for _,_,y in dev),'generatorFirst':sum(int(y[0]) for _,_,y in dev),'models':result,'selected':selection}
    write(root/'dev-report.json',report);write(root/'dev-scores.json',{'rowIds':[r['id'] for r,_,_ in dev],'scores':all_scores})
    print(json.dumps(report))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--train',required=True);p.add_argument('--dev',required=True);p.add_argument('--output',required=True);fit(p.parse_args())
