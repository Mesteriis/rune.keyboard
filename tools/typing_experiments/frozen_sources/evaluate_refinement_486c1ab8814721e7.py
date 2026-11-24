#!/usr/bin/env python3
"""Evaluate frozen selected artifacts, without training or choosing replacements."""
from pathlib import Path
import json
import numpy as np
import rank_refinement as rank
import neural_refinement as neural

ROOT=rank.ROOT
OUT=ROOT/'build/typing-refinement'

def evaluate(groups, tree, network, oldtree, oldnetwork):
    oldrank=rank.scores(oldtree,groups);newrank=rank.scores(tree,groups)
    oldcontext=[[neural.context_score(oldnetwork,r['prefix'],c['text'],end_of_word=False) for c in cs] for r,cs,_ in groups]
    newcontext=[[neural.context_score(network,r['prefix'],c['text']) for c in cs] for r,cs,_ in groups]
    modes={'generatorFirst':[[-i for i in range(len(cs))] for _,cs,_ in groups],
           'oldRanker':oldrank,'newRanker':newrank,'oldContext':oldcontext,'newContext':newcontext,
           'oldCombined':[np.array(a)+b for a,b in zip(oldrank,oldcontext)],
           'newCombined':[np.array(a)+b for a,b in zip(newrank,newcontext)]}
    return {'rowsWithAlternatives':len(groups),'expectedAvailable':sum(int(y.sum()>0) for _,_,y in groups),
            'models':{k:{'correctTop1':rank.accuracy(groups,v),'top1':rank.accuracy(groups,v)/len(groups)} for k,v in modes.items()}}

def main():
    selection=json.loads((OUT/'selection.json').read_text());assert selection['selectionFrozenBeforeTest'] and selection['blendGain']==1
    tree=OUT/'ranker'/f"{selection['ranker']}.bin";network=OUT/'neural'/f"{selection['neural']}.bin"
    assert rank.sha(tree)==selection['rankerSha256'] and rank.sha(network)==selection['neuralSha256']
    dest=OUT/'test-report.json';assert not dest.exists(),'test result already exists; do not silently reselect'
    assets=ROOT/'app/src/main/assets/smarttyping/experiments'
    oldtree=ROOT/'tools/typing_experiments/baseline/ru-ranker.bin';oldnetwork=neural.load_model(assets/'ru-context.bin');newnetwork=neural.load_model(network)
    groups=rank.verified_groups(OUT/'verified-observations/test.jsonl','test',allow_test=True)
    result=evaluate(groups,tree,newnetwork,oldtree,oldnetwork)
    manifest=json.loads((OUT/'data/manifest.json').read_text());testtext=OUT/'data/test-text.jsonl'
    assert rank.sha(testtext)==manifest['files']['test-text.jsonl']
    rows=[json.loads(s) for s in testtext.read_text().splitlines()]
    result['characters']=sum(len(r['text']) for r in rows)
    result['characterCrossEntropy']={}
    for name,model in [('old',oldnetwork),('new',newnetwork)]:
        x,y=neural.samples(rows,model.window);result['characterCrossEntropy'][name]=neural.cross_entropy(model,x,y)
    # Previously exposed v1 holdout is regression evidence only, never a new validation split.
    oldrows,_,_=rank.baseline.load_public()
    legacy=[(r,o['generation']['alternatives'],np.array([int(c['text'].lower()==r['expectedSpelling'].lower()) for c in o['generation']['alternatives']])) for r,o in oldrows if r['split']=='holdout' and r['cohort']=='typo' and not r['noAuto'] and o['generation']['alternatives']]
    result['exposedV1Regression']=evaluate(legacy,tree,newnetwork,oldtree,oldnetwork)
    result['selectionSha256']=rank.sha(OUT/'selection.json');result['observationsSha256']=rank.sha(OUT/'verified-observations/test.jsonl')
    result['scope']='Ranking existing alternatives, original remains separate; synthetic Wikipedia typos; no automatic-edit or chat-accuracy claim'
    rank.write(dest,result);print(json.dumps(result))

if __name__=='__main__':main()
