#!/usr/bin/env python3
"""Replay pinned disclosed rescue calibration; never inspect holdout labels."""
import argparse
import json
import math
import struct
from pathlib import Path
import joint_calibration_receipt as binding

PINS={'followup-corpus/calibration.jsonl':'09089d6d173268f5908a7b320a99dfd5f6778a672f09baa67a3fc92c785421ff',
 'followup-calibration-export-v2/observations.jsonl':'ecd92c00756328798542aed1ce1c22fff8ddb10a0dc2c83e42fc9ca6510a7dff',
 'followup-policy-v2/calibration-scores.json':'3d6a5d2b4bd52d09fe773527aa0eed821b7b677de9aad67de38187e989875907'}
MODEL_PIN='16c1a81a86ce5e71a23d4dbd2b22297abe30529a3c3d75560d6163a12685d168'


def run(root,out,historical_reproduction=False):
    frozen=binding.freeze_rescue(root,out,PINS,MODEL_PIN,historical_reproduction)
    root=Path(root).resolve();out=Path(out).resolve();output=out/'rescue-model-frozen-policy.json'
    binding.require(not output.exists() and not output.is_symlink(),'FRESH_POLICY')
    import numpy as np
    binding.require(np.__version__=='2.2.6','CALIBRATION_NUMERICAL_DEPENDENCIES')
    rows={r['id']:r for r in frozen['rows']};exports={r['id']:r for r in frozen['observations']}
    old_scores={r['id']:r for r in frozen['primary']};scores=frozen['secondary']
    b=frozen['morphology'];width,count,_,pos=struct.unpack_from('<IIII',b,8);prev=b'';morph={}
    for i in range(count):
     if i%width==0:prev=b''
     pre,size,lemma=struct.unpack_from('<BBI',b,pos);prev=prev[:pre]+b[pos+6:pos+6+size];pos+=6+size;morph[prev.decode()]=lemma
    values=[]
    for s in scores:
     r=rows[s['id']];e=exports[s['id']];binding.require(e['typed']==r['typed']==s['original'],'RESCUE_ROW_IDENTITY')
     pool=e['jointSearch']['alternatives'];sc=s['scores'];binding.require(len(sc)==len(pool)+1,'RESCUE_POOL_IDENTITY')
     if not 5<=len(r['typed'])<=32 or s['baseline']!=r['typed'].casefold():continue
     prior=old_scores[s['id']]['scores'];order=sorted(range(len(prior)),key=lambda i:(-prior[i],i));ix=order[0]
     def admitted(i):
      if not i:return False
      c=pool[i-1];local=e['fullTokenGeneration']['localSearch']
      return e['jointAdmission'].get(c['text'],False) or (c['terminalKey'] in morph and morph[c['terminalKey']]==0 and local['completion']=='COMPLETE' and len(local['alternatives'])==1 and local['alternatives'][0]['canonicalKey']==c['canonicalKey'])
     if prior[ix]>=.5526915271546093 and prior[ix]-prior[order[1]]>=.4475581943461431 and admitted(ix):continue
     values.append((r,pool,np.asarray(sc)))
    best=None
    for alpha in [0.,.05,.1,.15,.2,.3,.4,.6]:
     data=[]
     for r,pool,sc in values:
      v=sc.copy()
      for i,c in enumerate(pool,1):v[i]-=alpha*math.log1p(c['frequencyRank']/5000.)
      order=np.argsort(-v,kind='stable');i=int(order[0]);c=pool[i-1] if i else None
      allowed=c is not None and c['terminalKey'] in morph and 1<=c['frequencyRank']<=50000
      if not allowed:continue
      data.append((float(v[i]),float(v[i]-v[order[1]]),c['text'].casefold()==r['expectedSpelling'].casefold() and not r['noAuto'],r['noAuto'],r['family']))
     if not data:continue
     a=np.asarray([[x[0],x[1],x[2],x[3]] for x in data]);thresholds=np.unique(np.quantile(a[:,0],np.linspace(0,1,65)));margins=np.unique(np.quantile(a[:,1],np.linspace(0,1,65)))
     for score in thresholds:
      if score<.45:continue
      for margin in margins:
       if margin<.15:continue
       selected=(a[:,0]>=score)&(a[:,1]>=margin);n=int(selected.sum());correct=int(a[selected,2].sum());wrong=n-correct;controls=int(a[selected,3].sum())
       if correct<100 or controls or correct/max(1,n)<.995:continue
       families=len({data[i][4] for i in np.flatnonzero(selected) if data[i][2]})
       if families<20:continue
       key=(correct,-wrong,margin,score,-alpha)
       if best is None or key>best[0]:best=(key,dict(alpha=alpha,frequencyScale=5000.,minimumScore=float(score),minimumMargin=float(margin),calibrationCorrect=correct,calibrationWrong=wrong,calibrationFamilies=families))
    if best is None:raise RuntimeError('NO_QUALIFIED_CALIBRATION')
    policy=dict(stage='frozen-before-independent-holdout',version=1,scope='New long RU replacements only when raw legacy and existing qualified joint both retain the original; complete pool, known morphology target, ranked dictionary frequency <=50000; original protections retained.',protocol='Calibration precision >=99.5%; independent new-change precision >=99%, >=100 new correct, >=20 families; zero control changes, old correct-to-wrong, prefix and Undo failures. No model or threshold fitting on private user text or holdout.',**best[1],holdoutSha256=binding.file_hash(out/'fresh-corpus/holdout.jsonl'),calibrationRowsSha256=binding.file_hash(root/'followup-corpus/calibration.jsonl'),calibrationScoresSha256=binding.file_hash(root/'followup-policy-v2/calibration-scores.json'),modelSha256=binding.file_hash(out/'rescue-model/ranker.bin'))
    policy['secondaryCalibrationScoresSha256']=binding.file_hash(out/'rescue-model/calibration-scores.json')
    policy['trainingReceiptSha256']=binding.file_hash(out/'rescue-model/receipt.json')
    if policy['alpha']!=0.:raise ValueError('NONZERO_PRIOR_REQUIRES_SEPARATE_IMPLEMENTATION')
    policy['hostScoringVersions']=dict(numpy=np.__version__)
    binding.seal_policy(frozen,policy,True)
    encoded=json.dumps(policy,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n'
    binding.shared.verify(frozen)
    with output.open('x',encoding='utf-8') as stream:stream.write(encoded)
    print(json.dumps(policy));return policy


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True);parser.add_argument('--work-root',type=Path,required=True)
    parser.add_argument('--historical-reproduction',action='store_true');args=parser.parse_args()
    run(args.source_root,args.work_root,args.historical_reproduction)


if __name__=='__main__':main()
