#!/usr/bin/env python3
"""Bounded public-text neural experiment; inference depends only on NumPy."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import struct
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'build/typing-refinement/data'
OUT = ROOT / 'build/typing-refinement/neural'
ALPHABET = ' абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
SEED = 15092026

@dataclass
class Model:
    window: int
    hidden: int
    weights: list

def ids(text):
    return [max(ALPHABET.find(c), 0) for c in text.lower()]

def load_model(path):
    raw = Path(path).read_bytes()
    if len(raw) < 16:
        raise ValueError('truncated model')
    magic, w, h, n = struct.unpack('<4sIII', raw[:16])
    if (magic, w, h, n) not in ((b'REC1',24,24,34),(b'REC2',48,48,34)):
        raise ValueError('unsupported model dimensions')
    shapes = [(w*n,h),(h,),(h,n),(n,)]
    counts = [int(np.prod(s)) for s in shapes]
    if len(raw) != 16+4*sum(counts):
        raise ValueError('incorrect model size')
    a = np.frombuffer(raw, dtype='<f4', offset=16).copy()
    if not np.isfinite(a).all() or np.abs(a).max() > 32:
        raise ValueError('invalid model weights')
    chunks = np.split(a,np.cumsum(counts)[:-1])
    return Model(w,h,[a.reshape(s) for a,s in zip(chunks,shapes)])

def export_model(model, path):
    magic = b'REC1' if (model.window,model.hidden)==(24,24) else b'REC2'
    raw = struct.pack('<4sIII',magic,model.window,model.hidden,len(ALPHABET))
    raw += b''.join(np.asarray(a,dtype='<f4').tobytes() for a in model.weights)
    Path(path).write_bytes(raw)
    return load_model(path)

def logits(model, x):
    w1,b1,w2,b2 = [a.astype(np.float64) for a in model.weights]
    # Match Android's sequential accumulation of decoded float32 weights.
    hidden = np.broadcast_to(b1,(len(x),model.hidden)).copy()
    for j in range(model.window):
        hidden += w1[x[:,j]+j*len(ALPHABET)]
    return np.einsum("bi,ij->bj",np.tanh(hidden),w2,optimize=False) + b2

def probabilities(model, history):
    x = ([0]*model.window+ids(history[-model.window:]))[-model.window:]
    z = logits(model,np.array([x]))[0]
    p = np.exp(z-z.max())
    return p/p.sum()

def context_score(model, context, candidate, language='ru', end_of_word=True):
    if language != 'ru' or not candidate or len(candidate)>128:
        return 0.0
    history = context[-model.window:].lower()
    if history and not history[-1].isspace():
        history += ' '
    word = candidate[:32].lower()+(' ' if end_of_word else '')
    contexts = []
    for c in word:
        contexts.append(([0]*model.window+ids(history[-model.window:]))[-model.window:])
        history = (history+c)[-model.window:]
    z = logits(model,np.asarray(contexts))
    z -= z.max(axis=1,keepdims=True)
    p = np.exp(z); p /= p.sum(axis=1,keepdims=True)
    total = np.log(np.maximum(p[np.arange(len(word)),ids(word)],1e-9)).sum()
    return float(np.clip((total/len(word)+3)*.25,-.5,.5))

def verified_text(data, split, manifest):
    if split not in ('train','dev'):
        raise ValueError('only train/dev are permitted')
    name = split+'-text.jsonl'
    raw = (data/name).read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest['files'][name]:
        raise ValueError('input hash mismatch: '+name)
    rows = [json.loads(line) for line in raw.splitlines()]
    if not {r['articleId'] for r in rows}.issubset(set(manifest['partitions'][split]['articles'])):
        raise ValueError('article partition mismatch')
    return rows

def samples(rows, window):
    xs,ys = [],[]
    for row in rows:
        sequence = np.array([0]*window+ids(row['text']),dtype=np.int32)
        views = np.lib.stride_tricks.sliding_window_view(sequence,window+1)
        xs.append(views[:,:-1]); ys.append(views[:,-1])
    return np.concatenate(xs),np.concatenate(ys)

def cross_entropy(model,x,y):
    total = 0.0
    for start in range(0,len(y),4096):
        z = logits(model,x[start:start+4096]); yy=y[start:start+4096]
        z -= z.max(axis=1,keepdims=True)
        total += (np.log(np.exp(z).sum(axis=1))-z[np.arange(len(yy)),yy]).sum()
    return float(total/len(y))

def main():
    import mlx.core as mx
    import mlx.nn as nn
    import mlx.optimizers as optim
    OUT.mkdir(parents=True,exist_ok=False)
    manifest = json.loads((DATA/'manifest.json').read_text())
    if manifest['containsPersonalMessages'] is not False:
        raise ValueError('public-only provenance required')
    train = verified_text(DATA,'train',manifest)
    dev = verified_text(DATA,'dev',manifest)
    if {r['articleId'] for r in train} & {r['articleId'] for r in dev}:
        raise ValueError('overlapping train/dev articles')
    plan = {'seed':SEED,'candidates':[[24,24],[48,48]],'epochs':6,'checkpoints':[2,4,6],
            'batchSize':1024,'optimizer':'Adam bias_correction=True','learningRate':0.003,
            'epochDecay':0.85,'trainTextSha256':manifest['files']['train-text.jsonl'],
            'devTextSha256':manifest['files']['dev-text.jsonl'],'testAccess':False}
    (OUT/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    metrics = {'plan':plan,'checkpoints':[]}
    for window,hidden in plan['candidates']:
        x,y=samples(train,window); dx,dy=samples(dev,window)
        if window==24:
            old=load_model(ROOT/'app/src/main/assets/smarttyping/experiments/ru-context.bin')
            metrics['shippedDevCE']=cross_entropy(old,dx,dy)
            print('baseline',metrics['shippedDevCE'],flush=True)
        rng=np.random.default_rng(SEED)
        class Network(nn.Module):
            def __init__(self):
                super().__init__()
                self.w1=mx.array(rng.normal(0,.035,(window*34,hidden)).astype(np.float32))
                self.b1=mx.zeros(hidden)
                self.w2=mx.array(rng.normal(0,.08,(hidden,34)).astype(np.float32))
                self.b2=mx.zeros(34)
            def __call__(self,xx):
                h=mx.tanh(self.w1[xx+mx.arange(window)*34].sum(axis=1)+self.b1)
                return h@self.w2+self.b2
        net=Network(); optimizer=optim.Adam(learning_rate=.003,bias_correction=True)
        loss_grad=nn.value_and_grad(net,lambda m,xx,yy: nn.losses.cross_entropy(m(xx),yy,reduction='mean'))
        for epoch in range(1,7):
            optimizer.learning_rate=.003*(.85**(epoch-1))
            order=rng.permutation(len(y)); total=0.0
            for start in range(0,len(y),1024):
                batch=order[start:start+1024]
                loss,grad=loss_grad(net,mx.array(x[batch]),mx.array(y[batch]))
                optimizer.update(net,grad); mx.eval(net.parameters(),optimizer.state,loss)
                total+=float(loss.item())*len(batch)
            print('epoch',window,epoch,'trainCE',total/len(y),flush=True)
            if epoch in (2,4,6):
                model=Model(window,hidden,[np.array(net[k]) for k in ('w1','b1','w2','b2')])
                path=OUT/f'context-{window}-epoch{epoch}.bin'
                decoded=export_model(model,path)
                ce=cross_entropy(decoded,dx,dy)
                metrics['checkpoints'].append({'window':window,'hidden':hidden,'epoch':epoch,'trainCE':total/len(y),'devCE':ce,'path':str(path),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
                (OUT/'metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
                print('checkpoint',window,epoch,'devCE',ce,flush=True)
    print('finished',flush=True)

def verified_dev_observations(path):
    # Reuse source/receipt/partition validation; host timings vary between valid exports.
    from rank_refinement import verified_groups
    verified_groups(path, 'dev')
    raw=Path(path).read_bytes()
    return raw, hashlib.sha256(raw).hexdigest()

def evaluate_dev():
    """Frozen dev-only comparison; candidate order is preserved in score arrays."""
    path=ROOT/'build/typing-refinement/verified-observations/dev.jsonl'
    raw,digest=verified_dev_observations(path)
    groups=[json.loads(line) for line in raw.splitlines()]
    manifest=json.loads((DATA/'manifest.json').read_text())
    rowraw=(DATA/'dev-rows.jsonl').read_bytes()
    if hashlib.sha256(rowraw).hexdigest()!=manifest['files']['dev-rows.jsonl']:
        raise ValueError('dev rows hash mismatch')
    declared=[json.loads(line) for line in rowraw.splitlines()]
    if [g['row'] for g in groups] != declared:
        raise ValueError('dev row alignment mismatch')
    checkpoints=json.loads((OUT/'metrics.json').read_text())
    models=[('shipped',ROOT/'app/src/main/assets/smarttyping/experiments/ru-context.bin',False,checkpoints['shippedDevCE'])]
    models += [(Path(c['path']).stem,Path(c['path']),True,c['devCE']) for c in checkpoints['checkpoints']]
    result={'observationsSha256':digest,'models':{},'rows':[]}
    for g in groups:
        row=g['row']; gen=g['observation']['generation']
        if row['partition']!='dev' or gen['original']!=row['typed']:
            raise ValueError('incorrect development envelope')
        result['rows'].append({'id':row['id'],'candidates':[c['text'] for c in gen['alternatives']],'scores':{}})
    for name,path,terminal,ce in models:
        model=load_model(path)
        correct=0; reciprocal=0.; included=0; ambiguous=0; amb_correct=0; ties=0; amb_ties=0
        valid=0; valid_original_first=0
        for g,output in zip(groups,result['rows']):
            row=g['row']; gen=g['observation']['generation']; words=output['candidates']
            scores=[context_score(model,row['prefix'],word,end_of_word=terminal) for word in words]
            output['scores'][name]=scores
            # Preserve product's mandatory original-first handling for valid words.
            order=sorted(range(len(words)),key=lambda i:(-(float('inf') if gen['isValidWord'] and words[i].lower()==row['typed'].lower() else scores[i]),i))
            if gen['isValidWord']:
                valid+=1
                valid_original_first+=int(bool(order) and words[order[0]].lower()==row['typed'].lower())
            expected=row.get('expectedSpelling',row['typed']).lower()
            eligible=[i for i,w in enumerate(words) if w.lower()==expected]
            if not eligible:
                continue
            included+=1
            rank=min(order.index(i)+1 for i in eligible)
            correct+=int(rank==1); reciprocal+=1/rank
            is_tie=len(scores)>1 and sum(abs(s-max(scores))<1e-12 for s in scores)>1
            ties+=int(is_tie)
            if len(words)>1 and not gen['isValidWord']:
                ambiguous+=1; amb_correct+=int(rank==1); amb_ties+=int(is_tie)
        metrics={'allRows':len(groups),'expectedPresent':included,'top1':correct,'top1Rate':correct/included,'mrr':reciprocal/included,'ambiguousInvalidRows':ambiguous,'ambiguousTop1':amb_correct,'ambiguousTop1Rate':amb_correct/ambiguous,'topScoreTies':ties,'ambiguousTopScoreTies':amb_ties,'validRows':valid,'validOriginalFirst':valid_original_first,'devCE':ce,'endOfWord':terminal,'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        result['models'][name]=metrics
        print(name,json.dumps(metrics),flush=True)
    candidates=[name for name in result['models'] if name!='shipped']
    # Rank on ambiguous invalid rows; singleton/mandatory original-first rows cannot distinguish models.
    result['selected']=min(candidates,key=lambda k:(-result['models'][k]['ambiguousTop1'],result['models'][k]['devCE']))
    (OUT/'dev-scores.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (OUT/'dev-ranking.json').write_text(json.dumps({'selected':result['selected'],'models':result['models']},indent=2)+'\n')
    print('selected',result['selected'],flush=True)

if __name__=='__main__':
    import sys
    if sys.argv[1:]==['--evaluate-dev']:
        evaluate_dev()
    elif not sys.argv[1:]:
        main()
    else:
        raise SystemExit('supported arguments: --evaluate-dev or none (train)')
