#!/usr/bin/env python3
"""Reproduce the public-only 128-tree, depth-six joint rescue model; pinned input files only."""
import sys,json
from pathlib import Path
import numpy as np
from catboost import CatBoostRanker,Pool
import train_joint_correction as t
import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-root',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();root=args.source_root.resolve();out=args.output.resolve()
repo=Path(__file__).resolve().parents[2]
if out.exists() or not out.is_relative_to(repo/'build'):raise ValueError('FRESH_BUILD_OUTPUT')
PINS={'corpus/train.jsonl': 'a67ee9d103851f8b5c54e4059338a60e1cd5b8776e22440057eb48f07885bab9', 'evidence/train/observations.jsonl': '09a01ebcc7e5a683854f8a18d8c88a0b0c83a12d1e56af5380515797517ac19f', 'followup-corpus/calibration.jsonl': '09089d6d173268f5908a7b320a99dfd5f6778a672f09baa67a3fc92c785421ff', 'followup-calibration-export-v2/observations.jsonl': 'ecd92c00756328798542aed1ce1c22fff8ddb10a0dc2c83e42fc9ca6510a7dff'}
if any(t.sha(root/path)!=digest for path,digest in PINS.items()):raise ValueError('PUBLIC_INPUT_IDENTITY')
out.mkdir(parents=True)
train=t.groups(t.read(root/'corpus/train.jsonl'),t.read(root/'evidence/train/observations.jsonl'))
cal=t.groups(t.read(root/'followup-corpus/calibration.jsonl'),t.read(root/'followup-calibration-export-v2/observations.jsonl'))
assert not {g['row']['family'] for g in train}&{g['row']['family'] for g in cal}
x=[];y=[];ids=[]
for index,g in enumerate(train):
 row=g['row'];context=(row['prefix']+' ' if row['prefix'] else '')[-128:]
 for i,c in enumerate(g['candidates']):
  x.append(t.rank.features(context,row['typed'],c));y.append(int(i==g['target']));ids.append(index)
model=CatBoostRanker(iterations=128,depth=6,learning_rate=.05,loss_function='PairLogitPairwise',random_seed=t.SEED,thread_count=2,verbose=False,allow_writing_files=False)
model.fit(Pool(np.asarray(x,dtype=np.float32),np.asarray(y),group_id=np.asarray(ids)));t.rank.export_tree(model,out/'ranker.bin',t.rank.FEATURES)
records=t.score(out/'ranker.bin',cal);t.write(out/'calibration-scores.json',records)
t.write(out/'receipt.json',dict(trainingGroups=len(train),calibrationGroups=len(cal),rankerSha256=t.sha(out/'ranker.bin'),trainRowsSha256=t.sha(root/'corpus/train.jsonl'),trainExportSha256=t.sha(root/'evidence/train/observations.jsonl'),calibrationRowsSha256=t.sha(root/'followup-corpus/calibration.jsonl'),calibrationExportSha256=t.sha(root/'followup-calibration-export-v2/observations.jsonl'),parameters=dict(iterations=128,depth=6,learningRate=.05,seed=t.SEED),containsPrivateText=False));print('Public-only rescue model fitted and scored',len(train),len(cal))
