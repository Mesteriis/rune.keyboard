#!/usr/bin/env python3
"""A fixed additional-epoch candidate passes all gates or is retained as an experiment."""
import json
from pathlib import Path
import argparse
import extra_epoch_evaluation_receipt as binding

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'build/typing-extra-epochs'

def compare(groups, ranker, before, after):
    import numpy as np
    import neural_refinement as neural
    import rank_refinement as rank
    tree_scores=rank.scores(ranker,groups)
    result={'rowsWithAlternatives':len(groups),'expectedAvailable':sum(int(y.sum()>0) for _,_,y in groups),'models':{}}
    for name,network in [('before',before),('after',after)]:
        context=[[neural.context_score(network,r['prefix'],c['text']) for c in cs] for r,cs,_ in groups]
        combined=[np.array(a)+b for a,b in zip(tree_scores,context)]
        result['models'][name]={'combinedCorrectTop1':rank.accuracy(groups,combined),
            'contextCorrectTop1':rank.accuracy(groups,context)}
    return result

def accepts(dev_before,dev_after,ce_before,ce_after,fresh,regressions):
    """No second checkpoint selection after these results become visible."""
    improved_dev=dev_after>dev_before or (dev_after==dev_before and ce_after<ce_before)
    strict_fresh=fresh['models']['after']['combinedCorrectTop1']>fresh['models']['before']['combinedCorrectTop1']
    no_regression=all(r['models']['after']['combinedCorrectTop1']>=r['models']['before']['combinedCorrectTop1'] for r in regressions)
    return improved_dev and strict_fresh and no_regression

def run(source=OUT,historical_reproduction=False,legacy_root=ROOT,regression_row_limit=None):
    source=Path(source).resolve()
    frozen=binding.freeze(source,historical_reproduction,ROOT,legacy_root,regression_row_limit)
    output=source/'evaluation.json'
    binding.require(not output.exists() and not output.is_symlink(),'EVALUATION_ALREADY_REVEALED')
    import numpy as np
    import neural_refinement as neural
    import rank_refinement as rank
    import promote_refinement as promotion
    directory=source/'training';selection_path=directory/'selection.json';selection=frozen['selection']
    selected=frozen['selected'];original=frozen['original'];ranker=frozen['ranker']
    promotion.validate_tree(ranker.read_bytes(),rank.FEATURES)
    before=neural.load_model(original);after=neural.load_model(selected)
    if (before.window,before.hidden,after.window,after.hidden)!=(48,48,48,48):raise ValueError('UNCHANGED_ARCHITECTURE_REQUIRED')
    groups=rank.verified_groups(source/'observations/test.jsonl','test',allow_test=True)
    fresh=compare(groups,ranker,before,after)
    previous=rank.verified_groups(frozen['previous']/'verified-observations/test.jsonl','test',allow_test=True)
    if regression_row_limit is not None:previous=previous[:regression_row_limit]
    previous=compare(previous,ranker,before,after)
    oldrows=frozen['legacyRows']
    legacy=[]
    for row,observation in oldrows:
        candidates=observation['generation']['alternatives']
        if row['split']=='holdout' and row['cohort']=='typo' and not row['noAuto'] and candidates:
            labels=np.array([int(c['text'].lower()==row['expectedSpelling'].lower()) for c in candidates])
            legacy.append((row,candidates,labels))
    if regression_row_limit is not None:legacy=legacy[:regression_row_limit]
    binding.require(bool(legacy),'EVALUATION_LEGACY_COHORT')
    legacy=compare(legacy,ranker,before,after)
    manifest=json.loads((source/'data/manifest.json').read_text());path=source/'data/test-text.jsonl'
    if rank.sha(path)!=manifest['files']['test-text.jsonl']:raise ValueError('FRESH_TEXT_IDENTITY')
    text=[json.loads(line) for line in path.read_text().splitlines()]
    x,y=neural.samples(text,48)
    ce={'before':neural.cross_entropy(before,x,y),'after':neural.cross_entropy(after,x,y),'characters':len(y)}
    dev=json.loads((directory/'dev-report.json').read_text())['models']
    accepted=accepts(selection['devTop1Before'],selection['devTop1After'],dev['original']['devCE'],dev[selection['selected']]['devCE'],fresh,[previous,legacy])
    result={'schemaVersion':1,'selected':selection['selected'],'selectedSha256':selection['selectedSha256'],
        'originalSha256':selection['originalSha256'],'rankerSha256':selection['rankerSha256'],
        'selectionSha256':rank.sha(selection_path),'freshManifestSha256':rank.sha(source/'data/manifest.json'),
        'freshObservationsSha256':rank.sha(source/'observations/test.jsonl'),'fresh':fresh,'exposedPrevious':previous,'exposedLegacy':legacy,
        'freshCharacterCrossEntropy':ce,'observedGatePassed':accepted,'gate':'Dev improvement, strict fresh combined top1 gain, neither exposed combined count lower; no reselection',
        'scope':'Synthetic public Wikipedia alternatives only; no private chats, automatic corrections or touch accuracy measured',
        'evaluationScriptSha256':rank.sha(Path(__file__))}
    binding.finish_report(frozen,result,accepted)
    encoded=json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n'
    with output.open('x',encoding='utf-8') as report:report.write(encoded)
    print(json.dumps(result));return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,default=OUT)
    parser.add_argument('--historical-reproduction',action='store_true')
    parser.add_argument('--legacy-root',type=Path,default=ROOT)
    parser.add_argument('--regression-row-limit',type=int,help='Explicit historical smoke only.')
    args=parser.parse_args();run(args.source_root,args.historical_reproduction,args.legacy_root,args.regression_row_limit)


if __name__=='__main__':main()
