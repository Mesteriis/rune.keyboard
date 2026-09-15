#!/usr/bin/env python3
"""Public-only deterministic training. No private input path is accepted."""
from pathlib import Path
import hashlib
import json
import math
import struct
import numpy as np
from catboost import CatBoostClassifier

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / 'tools/eval/smart-typing-0.3/qualification-v2/corpus'
EXPORT = ROOT / 'build/morphology-public-export-v3'
OUT = ROOT / 'build/typing-experiments'
ASSETS = OUT / 'assets'
ALPHABET = ' абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
WINDOW, HIDDEN, FEATURES = 24, 24, 22

def mm(a, b):
    """Fixed-order contraction avoids platform BLAS floating-point status differences."""
    return np.einsum("...i,ij->...j", a, b, optimize=False)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')

def ids(text):
    return [ALPHABET.find(c) if c in ALPHABET else 0 for c in text.lower()]

def features(context, original, candidate):
    word = candidate['text'].lower()
    prev = context[-128:].lower().split()
    suffix = (prev[-1][-2:] if prev else '') + ':' + word[-2:]
    bucket = sum((i + 1) * ord(c) for i, c in enumerate(suffix)) % 16
    value = [min(max(candidate['unitDistance'], 0), 3)/3,
             math.log1p(min(max(candidate['frequencyRank'], 1), 1_000_000))/math.log1p(1_000_000),
             min(abs(len(original)-len(word)),6)/6,
             min(max(candidate['editCost'],0),4)/4,
             float(candidate['isFallback']), float(original.lower()[-2:] == word[-2:])]
    return value + [float(i == bucket) for i in range(16)]

def probabilities(weights, history):
    w1,b1,w2,b2 = weights
    x = ([0]*WINDOW + ids(history[-WINDOW:]))[-WINDOW:]
    h = np.tanh(b1 + sum(w1[i*len(ALPHABET)+v] for i,v in enumerate(x)))
    z = mm(h,w2)+b2
    z -= z.max()
    p=np.exp(z)
    return p/p.sum()

def context_score(weights, context, candidate):
    history = context[-WINDOW:].lower()
    if history and not history[-1].isspace(): history += ' '
    score=0.0
    for c in candidate.lower()[:32]:
        p=probabilities(weights,history)
        score += math.log(max(p[ids(c)[0]],1e-9))
        history=(history+c)[-WINDOW:]
    return max(-.5,min(.5,(score/max(1,min(len(candidate),32))+3)*.25))

def load_public():
    manifest=json.loads((CORPUS/'manifest.json').read_text())
    assert manifest['containsPersonalMessages'] is False
    assert sha(CORPUS/'spelling-ru.jsonl') == manifest['files']['spelling-ru.jsonl']
    receipt=json.loads((EXPORT/'receipt.json').read_text())
    for name in ('rows.jsonl','observations.jsonl','source-freeze.json'):
        assert sha(EXPORT/name)==receipt['files'][str(EXPORT/name)]
    # Only dependencies of candidate generation; mutable UI/integration files are not used.
    verified={}
    for path,digest in receipt['sources'].items():
        relative=Path(path).relative_to(ROOT).as_posix() if Path(path).is_relative_to(ROOT) else ''
        if (relative.startswith('app/src/main/assets/smarttyping/lexicon/') or
            relative.startswith('app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/lexicon/') or
            relative.startswith('app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/correction/') or
            relative == 'tools/morphology/ProductionCandidates.kt'):
            assert sha(Path(path))==digest, relative
            verified[relative]=digest
    assert len(verified)>20
    rows=[json.loads(x) for x in (EXPORT/'rows.jsonl').read_text().splitlines()]
    source=[json.loads(x) for x in (CORPUS/'spelling-ru.jsonl').read_text().splitlines()]
    source_by_id={r['id']:r for r in source}
    observations=[json.loads(x) for x in (EXPORT/'observations.jsonl').read_text().splitlines()]
    assert len(rows)==len(observations)
    public=[]
    for i,(r,o) in enumerate(zip(rows,observations)):
        assert o['index']==i and o['generation']['original']==r['typed']
        if r['id'] in source_by_id:
            assert r==source_by_id[r['id']]
            public.append((r,o))
    return public,verified,manifest

def main():
    OUT.mkdir(parents=True,exist_ok=True); ASSETS.mkdir(parents=True,exist_ok=True)
    public, verified, manifest=load_public()
    train=[(r,o) for r,o in public if r['split']=='calibration']
    holdout=[(r,o) for r,o in public if r['split']=='holdout']
    assert train and holdout
    for field in ('id','family','template'):
        assert not ({r[field] for r,o in train} & {r[field] for r,o in holdout})
    train.sort(key=lambda pair:hashlib.sha256(pair[0]['id'].encode()).digest())
    holdout.sort(key=lambda pair:hashlib.sha256(pair[0]['id'].encode()).digest())
    freeze={'corpus':sha(CORPUS/'spelling-ru.jsonl'),'manifest':sha(CORPUS/'manifest.json'),
            'observations':sha(EXPORT/'observations.jsonl'),'candidateSources':verified,
            'trainIds':[r['id'] for r,o in train], 'holdoutIds':[r['id'] for r,o in holdout]}
    write(OUT/'split-freeze.json',freeze) # Written before fitting.
    rng=np.random.default_rng(15092026)
    samples=[]; targets=[]
    for r,o in train:
        if r['noAuto'] or r['cohort'] not in ('correct','typo'): continue
        clean=r['prefix'].strip()+' '+r.get('expectedSpelling',r['typed'])
        seq=[0]*WINDOW+ids(clean)
        for i in range(WINDOW,len(seq)):
            samples.append(seq[i-WINDOW:i]); targets.append(seq[i])
    x=np.array(samples,dtype=np.int64); y=np.array(targets)
    # Bound training cost deterministically without admitting any holdout rows.
    if len(x)>180000:
        selection=rng.permutation(len(x))[:180000]; x=x[selection]; y=y[selection]
    n=len(ALPHABET)
    w1=rng.normal(0,.08,(WINDOW*n,HIDDEN)); b1=np.zeros(HIDDEN)
    w2=rng.normal(0,.08,(HIDDEN,n)); b2=np.zeros(n)
    train_losses=[]
    for epoch in range(18):
        total=0
        for start in range(0,len(x),256):
            # Same deterministic shuffled sequence per epoch.
            if start==0: order=rng.permutation(len(x))
            batch=order[start:start+256]; xx=x[batch]+np.arange(WINDOW)*n; yy=y[batch]
            h=np.tanh(w1[xx].sum(axis=1)+b1); logits=mm(h,w2)+b2
            logits-=logits.max(axis=1,keepdims=True); p=np.exp(logits); p/=p.sum(axis=1,keepdims=True)
            total-=np.log(p[np.arange(len(batch)),yy]).sum()
            p[np.arange(len(batch)),yy]-=1; p/=len(batch)
            dh=(mm(p,w2.T))*(1-h*h); rate=.25/(1+epoch*.07)
            w2-=rate*(mm(h.T,p)+1e-5*w2); b2-=rate*p.sum(axis=0)
            grad=np.zeros_like(w1)
            for j in range(WINDOW): np.add.at(grad,xx[:,j],dh)
            w1-=rate*(grad+1e-5*w1); b1-=rate*dh.sum(axis=0)
        assert all(np.isfinite(a).all() for a in (w1,b1,w2,b2))
        train_losses.append(total/len(x))
    weights=[a.astype(np.float32).astype(np.float64) for a in (w1,b1,w2,b2)]
    groups=[]
    for r,o in train+holdout:
        if r['cohort']!='typo' or r['noAuto']: continue
        candidates=o['generation']['alternatives']
        if not candidates: continue
        expected=r['expectedSpelling'].lower()
        labels=np.array([int(c['text'].lower()==expected) for c in candidates])
        groups.append((r,np.array([features(r['prefix'],r['typed'],c) for c in candidates]),labels,candidates))
    fit=[g for g in groups if g[0]['split']=='calibration' and g[2].sum() and len(g[2])>1]
    diffs=np.array([xx[yy.argmax()]-xx[i] for r,xx,yy,cc in fit for i in range(len(yy)) if not yy[i]])
    assert len(diffs)>0
    rank=np.zeros(FEATURES)
    for step in range(1200):
        z=np.clip(np.einsum("ij,j->i",diffs,rank),-30,30)
        rank+=.15*((diffs/(1+np.exp(z))[:,None]).mean(axis=0)-.005*rank)
    rank=rank.astype(np.float32).astype(np.float64)
    cat=CatBoostClassifier(iterations=80,depth=4,learning_rate=.05,loss_function='Logloss',
                           random_seed=15092026,thread_count=2,verbose=False,allow_writing_files=False)
    cat.fit(np.concatenate([g[1] for g in fit]),np.concatenate([g[2] for g in fit]))
    cat.save_model(str(OUT/'catboost-reference.cbm'))
    cat.save_model(str(OUT/'catboost-reference.json'),format='json')
    results={}
    for split in ('calibration','holdout'):
        gs=[g for g in groups if g[0]['split']==split]
        result={'rowsWithAlternatives':len(gs),'expectedAvailable':sum(int(g[2].sum()>0) for g in gs)}
        for label,score in [('generatorFirst',lambda r,x,c:np.arange(len(x))*-1),
                            ('learnedLinear',lambda r,x,c:np.einsum("ij,j->i",x,rank)),
                            ('catboostHost',lambda r,x,c:cat.predict_proba(x)[:,1]),
                            ('compactContext',lambda r,x,c:np.array([context_score(weights,r['prefix'],v['text']) for v in c])),
                            ('catboostPlusContextFixed',lambda r,x,c:.8*np.tanh(cat.predict(x,prediction_type='RawFormulaVal')/4)+np.array([context_score(weights,r['prefix'],v['text']) for v in c]))]:
            correct=sum(int(yy[np.argmax(score(r,xx,cc))]) for r,xx,yy,cc in gs)
            result[label]={'correctTop1':correct,'top1OverRowsWithAlternatives':correct/len(gs)}
        results[split]=result
    hx=[];hy=[]
    for r,o in holdout:
        if r['noAuto'] or r['cohort'] not in ('correct','typo'):continue
        seq=[0]*WINDOW+ids(r['prefix'].strip()+' '+r.get('expectedSpelling',r['typed']))
        for i in range(WINDOW,len(seq)):hx.append(seq[i-WINDOW:i]);hy.append(seq[i])
    hx=np.array(hx);hy=np.array(hy); a,b,c,d=weights
    z=mm(np.tanh(a[hx+np.arange(WINDOW)*n].sum(axis=1)+b),c)+d
    z-=z.max(axis=1,keepdims=True); p=np.exp(z);p/=p.sum(axis=1,keepdims=True)
    neural={'trainCharacters':len(x),'holdoutCharacters':len(hx),'trainCrossEntropy':train_losses,
            'holdoutCrossEntropy':float(-np.log(p[np.arange(len(hy)),hy]).mean()),
            'holdoutNextCharAccuracy':float((p.argmax(axis=1)==hy).mean()),'uniformCrossEntropy':math.log(n)}
    # Exact fixed versioned little-endian float layout.
    tree_json=json.loads((OUT/'catboost-reference.json').read_text())
    scale,bias=tree_json['scale_and_bias']; assert len(bias)==1
    trees=tree_json['oblivious_trees']; assert 0<len(trees)<=128
    binary=b'RET1'+struct.pack('<IIff',FEATURES,len(trees),scale,bias[0])
    for tree in trees:
        splits=tree['splits']; assert 0<len(splits)<=6
        binary+=struct.pack('<I',len(splits))
        for split in splits:
            assert split['split_type']=='FloatFeature'
            binary+=struct.pack('<If',split['float_feature_index'],split['border'])
        binary+=np.array(tree['leaf_values'],dtype='<f4').tobytes()
    (ASSETS/'ru-ranker.bin').write_bytes(binary)
    (ASSETS/'ru-context.bin').write_bytes(b'REC1'+struct.pack('<III',WINDOW,HIDDEN,n)+b''.join(a.astype('<f4').tobytes() for a in weights))
    asset_hashes={p.name:sha(p) for p in (ASSETS/'ru-ranker.bin',ASSETS/'ru-context.bin')}
    report={'schemaVersion':1,'experimental':True,'productionQualified':False,'privateDataUsed':False,
            'evaluation':'public Wikipedia qualification rows with synthetic spelling corruptions; not chat accuracy',
            'split':'existing disjoint calibration/holdout families and templates, SHA256 row-ID ordering',
            'fitRows':len(train),'holdoutRows':len(holdout),'rankPairCount':len(diffs),
            'ranking':results,'neural':neural,'assetSha256':asset_hashes,
            'source':manifest['source'],'sourceCorpusSha256':freeze['corpus'],
            'trainingScriptSha256':sha(Path(__file__)),'numpy':np.__version__,
            'personalTouch':'not supervised; separately bounded existing adjustments only',
            'blend':'fixed before holdout: 0.8*tanh(CatBoost raw/4) + clip((mean neural logP+3)*0.25,-0.5,0.5)',
            'androidPerformanceMeasured':False}
    write(OUT/'training-report.json',report); write(ASSETS/'provenance.json',report)
    parity=[]
    for context,word in [('это','слово'),('мы идем','домой'),('привет','мир'),('','я')]:
        candidate={'text':word,'unitDistance':1,'frequencyRank':300,'editCost':1.,'isFallback':False}
        f=features(context,word+'а',candidate)
        parity.append({'context':context,'original':word+'а','candidate':word,
                      'features':f,'rankScore':.8*math.tanh(float(cat.predict(np.array([f]),prediction_type='RawFormulaVal')[0])/4),
                      'contextScore':context_score(weights,context,word),
                      'next':probabilities(weights,context+' '+word).tolist()})
    write(OUT/'parity.json',parity)
    emit_runtime_fixtures(asset_hashes,parity)
    print(json.dumps({'ranking':results,'neural':neural,'assets':asset_hashes},ensure_ascii=False))

def emit_runtime_fixtures(asset_hashes, parity):
    runtime=OUT/'FrozenExperimentAssets.kt'
    runtime.write_text('package io.github.mesteriis.rune.keyboard.smarttyping.experiments\n\n'
        '/** Generated from public-only tools/typing_experiments/train.py assets. */\n'
        'internal object FrozenExperimentAssets {\n'
        f'    const val RANK_BYTES = {(ASSETS/"ru-ranker.bin").stat().st_size}\n'
        f'    const val RANK_SHA256 = "{asset_hashes["ru-ranker.bin"]}"\n'
        f'    const val CONTEXT_BYTES = {(ASSETS/"ru-context.bin").stat().st_size}\n'
        f'    const val CONTEXT_SHA256 = "{asset_hashes["ru-context.bin"]}"\n' + '}\n')
    lines=[]
    for p in parity:
        letters=p['next'][1:]; total=sum(letters)
        lines.append('\t'.join([p['context'],p['original'],p['candidate'],str(p['rankScore']),str(p['contextScore']),
                              ','.join(str(x/total) for x in letters)]))
    (OUT/'parity.tsv').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':main()
