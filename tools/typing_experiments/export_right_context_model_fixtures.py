"""Freeze a trained experimental model and authored numeric-bridge references.

No accuracy qualification, fitting, user text or Android model registration.
"""
import argparse
import base64
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import numpy as np
import rank_refinement as rank
import neural_refinement as neural
from grammar_context_features import GrammarContextFeatures
from word_context_features import WordContextFeatures
from right_context_grammar_features import RightContextGrammarFeatures
from right_context_role_features import RightContextRoleFeatures,role_revision_features,FEATURES


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--model-root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    repo=Path(__file__).resolve().parents[2];model_root=args.model_root.resolve();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    if not model_root.is_relative_to(repo/'build'):parser.error('Use a workspace build model')
    frozen=json.loads((model_root/'frozen-model.json').read_text());model_path=model_root/'experimental-ranker.bin';blob=model_path.read_bytes()
    if frozen['featureCount']!=FEATURES or sha(model_path)!=frozen['modelSha256']:raise ValueError('BRIDGE_MODEL_IDENTITY')
    for name,h in frozen['modelFeatureSources'].items():
        p=Path(name).resolve()
        if not p.is_relative_to(repo) or sha(p)!=h:raise ValueError('BRIDGE_FEATURE_SOURCE_IDENTITY')
    args.output.mkdir(parents=True,exist_ok=False);sys.path.insert(0,str(repo/'tools/morphology'));from ranker import PymorphyLexicon
    lex=PymorphyLexicon();right=RightContextGrammarFeatures(lex);role=RightContextRoleFeatures(lex)
    cases=[('',' будут ','готов','готовы'),('она пришла, теперь ',' будешь ','готва','готова'),
      ('она пришла, иди теперь ',' будешь ','готов','готова'),('',' модели ','готв','готовы'),
      ('',' и ','готв','готовы'),('',' будет ','ГОТОВА','готова'),('',' будет ','готова','ГОТОВА'),
      ('',' будет ','е\u0308лки','ёлки'),('🙂'*70+'она пришла, теперь ',' будут она ','готв','готовы'),
      ('',' он','готов','готовы'),('',' были ','зол','зал'),('',' будет ','готв','неизвестноеслово')]
    bases=[[0.]*146,[(i-73)/128 for i in range(146)],[float(math.nextafter(.5,math.inf)) if i%2 else -.5 for i in range(146)]]
    enc=lambda text:base64.b64encode(text.encode()).decode();rows=[]
    for left,suffix,applied,candidate in cases:
        for base in bases:
            vector=role_revision_features(base,right,role,left,suffix,applied,candidate)
            rows.append('\t'.join([enc(left),enc(suffix),enc(applied),enc(candidate),','.join(map(repr,base)),','.join(map(repr,vector)),repr(rank.tree_score(blob,vector))]))
    (args.output/'vectors.tsv').write_text('\n'.join(rows)+'\n');(args.output/'model.bin').write_bytes(blob)
    training=json.loads((model_root/'plan.json').read_text());assets=repo/'app/src/main/assets/smarttyping/experiments'
    for name,h in training['installedAssets'].items():
        if sha(assets/name)!=h:raise ValueError('BRIDGE_INSTALLED_ASSET_CHANGED')
    counts=[repo/'build/context-ranking-20261025/counts-v3/model-counts.jsonl',repo/'build/context-feature-ranker-20261026/tatoeba-train-counts.jsonl']
    if [sha(p) for p in counts]!=training['countsSha256']:raise ValueError('BRIDGE_COUNTS_IDENTITY')
    tables=[WordContextFeatures.load(p) for p in counts];character=neural.load_model(assets/'ru-ranking-context.bin');grammar_features=GrammarContextFeatures(lex);runtime=[]
    for left,suffix,applied,candidate in cases:
        original='готв' if candidate.lower().startswith('готов') else applied
        for mode in ['candidate','fallback','original']:
            word=original if mode=='original' else candidate;distance=0 if mode=='original' else 1;frequency=2147483647 if mode=='original' else 300;cost=0. if mode=='original' else 1.;fallback=mode=='fallback'
            c=dict(text=word,unitDistance=distance,frequencyRank=frequency,editCost=cost,isFallback=fallback)
            base=rank.features(left,original,c)+[v for table in tables for v in table.extract(left,original,word)]+[neural.context_score(character,left,word)]+grammar_features.extract(left,original,word)
            if len(base)!=146 or not all(math.isfinite(v) for v in base):raise ValueError('BRIDGE_BASE_UNAVAILABLE')
            vector=role_revision_features(base,right,role,left,suffix,applied,word)
            raw_score=rank.tree_score(blob,vector)
            runtime.append('\t'.join([enc(left),enc(suffix),enc(original),enc(applied),enc(word),mode,str(distance),str(frequency),repr(cost),str(int(fallback)),','.join(map(repr,base)),','.join(map(repr,vector)),repr(raw_score),repr(.8*math.tanh(raw_score/4))]))
    (args.output/'runtime-vectors.tsv').write_text('\n'.join(runtime)+'\n')
    n,count,scale,bias=struct.unpack_from('<IIff',blob,4);assert blob[:4]==b'RET2' and n==FEATURES and 1<=count<=128;offset=20;boundaries=set()
    for _ in range(count):
        depth,=struct.unpack_from('<I',blob,offset);offset+=4;assert 1<=depth<=6
        for _ in range(depth):
            index,border=struct.unpack_from('<If',blob,offset);offset+=8;assert 0<=index<n and math.isfinite(border);boundaries.add((index,border))
        offset+=4*(1<<depth)
    assert offset==len(blob)
    probes=[]
    for index,border in sorted(boundaries):
        values=[float(np.nextafter(np.float32(border),np.float32(-math.inf))),border,math.nextafter(border,math.inf),float(np.nextafter(np.float32(border),np.float32(math.inf)))]
        for value in values:
            vector=[0.]*FEATURES;vector[index]=value;probes.append(f'{index}\t{value!r}\t{rank.tree_score(blob,vector)!r}')
    (args.output/'probes.tsv').write_text('\n'.join(probes)+'\n')
    manifest=dict(purpose='AUTHORED_BRIDGE_AND_FROZEN_MODEL_PARITY_ONLY',modelSha256=sha(model_path),modelFrozenReceiptSha256=sha(model_root/'frozen-model.json'),features=FEATURES,cases=len(rows),runtimeCases=len(runtime),boundaryProbes=len(probes),distinctSplitBoundaries=len(boundaries),dictionary=lex.receipt(),containsOwnerText=False,qualificationPerformed=False,exporterSha256=sha(__file__),vectorsSha256=sha(args.output/'vectors.tsv'),runtimeVectorsSha256=sha(args.output/'runtime-vectors.tsv'),probesSha256=sha(args.output/'probes.tsv'))
    (args.output/'provenance.json').write_text(json.dumps(manifest,indent=2)+'\n');(args.output/'hashes.properties').write_text('model='+manifest['modelSha256']+'\ncases='+str(len(rows))+'\nruntimeCases='+str(len(runtime))+'\nprobes='+str(len(probes))+'\n')
    print(json.dumps({k:manifest[k] for k in ['features','cases','boundaryProbes','distinctSplitBoundaries','modelSha256']}),flush=True)


if __name__=='__main__':main()
