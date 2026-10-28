#!/usr/bin/env python3
"""Fit one joint RET2 ranker and freeze short/long arbitration using calibration only."""
import argparse
import hashlib
import json
import math
import struct
from functools import lru_cache
from pathlib import Path
import numpy as np
from catboost import CatBoostRanker, Pool
import abstaining_ranker as base
import rank_refinement as rank
import neural_refinement as neural

SEED=25102026


def read(path):return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,obj):Path(path).write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n')


def groups(rows,observations):
    if [r['id'] for r in rows]!=[o.get('id') for o in observations]:raise ValueError('IDENTITY')
    result=[]
    for r,o in zip(rows,observations,strict=True):
        if o.get('status')!='COMPLETE' or o.get('typed')!=r['typed'] or o.get('prefix')!=r['prefix']:raise ValueError('INCOMPLETE_OR_SUBSTITUTED_INPUT')
        pool=o.get('jointSearch') or {}
        if pool.get('completion')!='COMPLETE' or not pool.get('alternatives') or o.get('inputChangedByTyping'):continue
        candidates=[base.original_candidate(r)]+pool['alternatives']
        if len(candidates)>65:raise ValueError('POOL_BUDGET')
        target=r.get('expectedSpelling',r['typed']).casefold()
        wanted=next((i for i,c in enumerate(candidates) if c['text'].casefold()==target),0) if not r['noAuto'] else 0
        result.append(dict(row=r,candidates=candidates,target=wanted,
            baseline=o['afterBoundary']['text'].rstrip().split()[-1].casefold(),
            admission=o.get('jointAdmission',{})))
    return result


def fit(data,path):
    features=[];labels=[];ids=[]
    for identity,g in enumerate(data):
        r=g['row'];context=(r['prefix']+' ' if r['prefix'] else '')[-128:]
        for index,candidate in enumerate(g['candidates']):
            features.append(rank.features(context,r['typed'],candidate));labels.append(int(index==g['target']));ids.append(identity)
    model=CatBoostRanker(iterations=128,depth=5,learning_rate=.05,loss_function='PairLogitPairwise',
        random_seed=SEED,thread_count=2,verbose=False,allow_writing_files=False)
    model.fit(Pool(np.asarray(features,dtype=np.float32),np.asarray(labels),group_id=np.asarray(ids)))
    rank.export_tree(model,path,rank.FEATURES)
    model.save_model(str(path.with_suffix('.json')),format='json')


def tree_matrix(blob, vectors):
    count, trees, scale, bias=struct.unpack_from('<IIff',blob,4)
    if blob[:4]!=b'RET2' or vectors.shape[1]!=count:raise ValueError('TREE_SHAPE')
    result=np.zeros(len(vectors),dtype=np.float64);offset=20
    for _ in range(trees):
        depth,=struct.unpack_from('<I',blob,offset);offset+=4
        leaves=np.zeros(len(vectors),dtype=np.int32)
        for bit in range(depth):
            index,border=struct.unpack_from('<If',blob,offset);offset+=8
            leaves|=(vectors[:,index]>np.float32(border)).astype(np.int32)<<bit
        values=np.frombuffer(blob,dtype='<f4',count=1<<depth,offset=offset);offset+=4*(1<<depth)
        result+=values[leaves]
    if offset!=len(blob):raise ValueError('TREE_LENGTH')
    return result*scale+bias


def score(path,data):
    weights=Path(path).read_bytes();model=neural.load_model(base.CONTEXT_MODEL)
    vectors=np.asarray([rank.features((g['row']['prefix']+' ' if g['row']['prefix'] else '')[-128:],g['row']['typed'],c)
        for g in data for c in g['candidates']],dtype=np.float32)
    raw=tree_matrix(weights,vectors)
    for index in range(min(32,len(vectors))):
        if abs(raw[index]-rank.tree_score(weights,vectors[index]))>1e-7:raise ValueError('TREE_MATRIX_PARITY')
    raw=.8*np.tanh(raw/4)
    @lru_cache(maxsize=65536)
    def context_score(context,word):return neural.context_score(model,context,word)
    output=[];cursor=0
    for g in data:
        r=g['row'];context=(r['prefix']+' ' if r['prefix'] else '')[-128:]
        values=[float(raw[cursor+i])+context_score(context,c['text']) for i,c in enumerate(g['candidates'])]
        cursor+=len(values)
        order=sorted(range(len(values)),key=lambda i:(-values[i],i));winner=order[0]
        candidate=g['candidates'][winner]['text'].casefold()
        expected=r.get('expectedSpelling',r['typed']).casefold();original=r['typed'].casefold()
        if winner and not g['admission'].get(g['candidates'][winner]['text'],False):candidate=g['baseline']
        output.append(dict(id=r['id'],family=r['family'],band='short' if len(r['typed'])<=4 else 'long',
            topScore=values[winner],margin=values[winner]-values[order[1]],candidate=candidate,
            original=original,expected=expected,baseline=g['baseline'],control=r['noAuto'],scores=values))
    return output


def metrics(records,score_threshold,margin_threshold):
    chosen=[r for r in records if r['topScore']>=score_threshold and r['margin']>=margin_threshold]
    changed=[r for r in chosen if r['candidate']!=r['baseline']]
    new=[r for r in changed if r['baseline']==r['original'] and r['candidate']!=r['original']]
    baseline_correct=lambda r:r['baseline']==r['expected']
    return dict(changes=len(changed),newCorrect=sum(r['candidate']==r['expected'] and not r['control'] for r in new),
        newWrong=sum(r['candidate']!=r['expected'] or r['control'] for r in new),
        regressions=sum(baseline_correct(r) and r['candidate']!=r['expected'] for r in changed),
        correctedWrong=sum(not baseline_correct(r) and r['candidate']==r['expected'] for r in changed),
        suppressedWrong=sum(not baseline_correct(r) and r['candidate']==r['original'] for r in changed),
        wrongChanged=sum(r['candidate'] not in (r['expected'],r['original']) for r in changed),
        controlChanges=sum(r['control'] and r['candidate']!=r['original'] for r in changed),
        newCorrectFamilies=len({r['family'] for r in new if r['candidate']==r['expected'] and not r['control']}))


def calibrate(records,band):
    values=[r for r in records if r['band']==band]
    scores=np.unique(np.quantile([r['topScore'] for r in values],np.linspace(0,1,65))).tolist()+[2.0]
    margins=np.unique(np.quantile([r['margin'] for r in values],np.linspace(0,1,65))).tolist()+[2.0]
    best=None
    top=np.asarray([r['topScore'] for r in values]);margin=np.asarray([r['margin'] for r in values])
    bad=np.asarray([r['candidate']!=r['baseline'] and ((r['baseline']==r['expected'] and r['candidate']!=r['expected']) or
        (r['control'] and r['candidate']!=r['original']) or r['candidate'] not in (r['expected'],r['original'])) for r in values])
    for s in scores:
        for m in margins:
            if m<=0:continue
            selected=(top>=s)&(margin>=m)
            if np.any(selected&bad):continue
            result=metrics(values,s,m)
            if band=='short' and (result['newCorrect']<50 or result['newCorrectFamilies']<20):continue
            benefit=result['newCorrect']+result['correctedWrong']+result['suppressedWrong']
            if band=='long' and result['correctedWrong']+result['suppressedWrong']<10:continue
            key=(benefit,result['newCorrect'],s,m)
            if best is None or key>best[0]:best=(key,s,m,result)
    if best is None:return dict(qualifiedCalibration=False,minimumScore=2.0,minimumMargin=2.0,metrics=metrics(values,2.,2.))
    return dict(qualifiedCalibration=True,minimumScore=best[1],minimumMargin=best[2],metrics=best[3])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['corpus','train_export','calibration_export','output']:p.add_argument(name,type=Path)
    a=p.parse_args()
    if a.output.exists():raise ValueError('FRESH_OUTPUT')
    manifest=json.loads((a.corpus/'manifest.json').read_text())
    for part in ['train','calibration']:
        if sha(a.corpus/f'{part}.jsonl')!=manifest['files'][f'{part}.jsonl']:raise ValueError('CORPUS_DRIFT')
    train=groups(read(a.corpus/'train.jsonl'),read(a.train_export/'observations.jsonl'))
    calibration=groups(read(a.corpus/'calibration.jsonl'),read(a.calibration_export/'observations.jsonl'))
    if {g['row']['family'] for g in train}&{g['row']['family'] for g in calibration}:raise ValueError('FAMILY_OVERLAP')
    a.output.mkdir();fit(train,a.output/'joint-ranker.bin');print('FIT_COMPLETE',len(train),flush=True)
    records=score(a.output/'joint-ranker.bin',calibration)
    write(a.output/'calibration-scores.json',records)
    policies={band:calibrate(records,band) for band in ['short','long']}
    policy=dict(schema=1,stage='frozen-before-independent-holdout',seed=SEED,modelSha256=sha(a.output/'joint-ranker.bin'),
        contextSha256=sha(base.CONTEXT_MODEL),corpusManifestSha256=sha(a.corpus/'manifest.json'),
        holdoutSha256=manifest['files']['holdout.jsonl'],thresholds=policies,
        trainingGroups=len(train),calibrationGroups=len(calibration),trainerSha256=sha(Path(__file__)),
        featureCodeSha256=sha(Path(rank.__file__)),contextCodeSha256=sha(Path(neural.__file__)),
        trainExportReceiptSha256=sha(a.train_export/'receipt.json'),calibrationExportReceiptSha256=sha(a.calibration_export/'receipt.json'))
    write(a.output/'frozen-policy.json',policy);print(json.dumps(policies),flush=True)


if __name__=='__main__':main()
