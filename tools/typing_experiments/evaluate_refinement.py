#!/usr/bin/env python3
"""Evaluate frozen selected artifacts, without training or choosing replacements."""
from pathlib import Path
import json
import argparse
import refinement_evaluation_receipt as binding

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'build/typing-refinement'

def evaluate(groups, tree, network, oldtree, oldnetwork):
    import numpy as np
    import rank_refinement as rank
    import neural_refinement as neural
    oldrank=rank.scores(oldtree,groups);newrank=rank.scores(tree,groups)
    oldcontext=[[neural.context_score(oldnetwork,r['prefix'],c['text'],end_of_word=False) for c in cs] for r,cs,_ in groups]
    newcontext=[[neural.context_score(network,r['prefix'],c['text']) for c in cs] for r,cs,_ in groups]
    modes={'generatorFirst':[[-i for i in range(len(cs))] for _,cs,_ in groups],
           'oldRanker':oldrank,'newRanker':newrank,'oldContext':oldcontext,'newContext':newcontext,
           'oldCombined':[np.array(a)+b for a,b in zip(oldrank,oldcontext)],
           'newCombined':[np.array(a)+b for a,b in zip(newrank,newcontext)]}
    return {'rowsWithAlternatives':len(groups),'expectedAvailable':sum(int(y.sum()>0) for _,_,y in groups),
            'models':{k:{'correctTop1':rank.accuracy(groups,v),'top1':rank.accuracy(groups,v)/len(groups)} for k,v in modes.items()}}

def run(source=OUT,historical_reproduction=False,legacy_root=ROOT,legacy_row_limit=None):
    source=Path(source).resolve()
    oldtree=ROOT/'tools/typing_experiments/baseline/ru-ranker.bin'
    oldcontext=ROOT/'app/src/main/assets/smarttyping/experiments/ru-context.bin'
    frozen=binding.freeze(source,historical_reproduction,ROOT,(oldtree,oldcontext),legacy_root,legacy_row_limit)
    dest=source/'test-report.json'
    binding.require(not dest.exists() and not dest.is_symlink(),'EVALUATION_REPORT_EXISTS')
    import numpy as np
    import rank_refinement as rank
    import neural_refinement as neural
    import promote_refinement as promotion
    selection=frozen['selection']
    tree=source/'ranker'/f"{selection['ranker']}.bin";network=source/'neural'/f"{selection['neural']}.bin"
    promotion.validate_tree(tree.read_bytes(),rank.FEATURES)
    assets=ROOT/'app/src/main/assets/smarttyping/experiments'
    oldtree=ROOT/'tools/typing_experiments/baseline/ru-ranker.bin';oldnetwork=neural.load_model(assets/'ru-context.bin');newnetwork=neural.load_model(network)
    groups=rank.verified_groups(source/'verified-observations/test.jsonl','test',allow_test=True)
    result=evaluate(groups,tree,newnetwork,oldtree,oldnetwork)
    manifest=frozen['manifest'];testtext=source/'data/test-text.jsonl'
    rows=[json.loads(s) for s in testtext.read_text().splitlines()]
    result['characters']=sum(len(r['text']) for r in rows)
    result['characterCrossEntropy']={}
    for name,model in [('old',oldnetwork),('new',newnetwork)]:
        x,y=neural.samples(rows,model.window);result['characterCrossEntropy'][name]=neural.cross_entropy(model,x,y)
    # Previously exposed v1 holdout is regression evidence only, never a new validation split.
    oldrows=frozen['legacyRows']
    legacy=[(r,o['generation']['alternatives'],np.array([int(c['text'].lower()==r['expectedSpelling'].lower()) for c in o['generation']['alternatives']])) for r,o in oldrows if r['split']=='holdout' and r['cohort']=='typo' and not r['noAuto'] and o['generation']['alternatives']]
    if legacy_row_limit is not None:legacy=legacy[:legacy_row_limit]
    binding.require(bool(legacy),'EVALUATION_LEGACY_COHORT')
    result['exposedV1Regression']=evaluate(legacy,tree,newnetwork,oldtree,oldnetwork)
    result['selectionSha256']=frozen['receipt']['selectionSha256'];result['observationsSha256']=frozen['receipt']['observationsSha256']
    result['dataManifestSha256']=frozen['receipt']['dataManifestSha256']
    result['independentDataEvaluation']=frozen['receipt']['independentDataEvaluation']
    result['evaluationBinding']=frozen['receipt']
    result['historicalReproduction']=historical_reproduction
    result['scope']='Ranking existing alternatives, original remains separate; synthetic Wikipedia typos; no automatic-edit or chat-accuracy claim'
    binding.verify(frozen)
    result['reportPayloadSha256']=binding.seal(result)
    encoded=json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n'
    with dest.open('x',encoding='utf-8') as report:report.write(encoded)
    print(json.dumps(result));return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,default=OUT)
    parser.add_argument('--historical-reproduction',action='store_true')
    parser.add_argument('--legacy-root',type=Path,default=ROOT)
    parser.add_argument('--legacy-row-limit',type=int,help='Bounded disclosed smoke only; disabled for independent evaluation.')
    args=parser.parse_args();run(args.source_root,args.historical_reproduction,args.legacy_root,args.legacy_row_limit)


if __name__=='__main__':main()
