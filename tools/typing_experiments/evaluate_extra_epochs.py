#!/usr/bin/env python3
"""A fixed additional-epoch candidate passes all gates or is retained as an experiment."""
import json
from pathlib import Path
import numpy as np
import neural_refinement as neural
import rank_refinement as rank

ROOT=rank.ROOT
OUT=ROOT/'build/typing-extra-epochs'

def compare(groups, ranker, before, after):
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

def main():
    output=OUT/'evaluation.json'
    if output.exists():raise ValueError('EVALUATION_ALREADY_REVEALED')
    directory=OUT/'training';selection_path=directory/'selection.json'
    selection=json.loads(selection_path.read_text())
    if not selection['selectionFrozenBeforeTest'] or selection['testAccess']:
        raise ValueError('FROZEN_DEV_SELECTION_REQUIRED')
    for name,key in [('plan.json','planSha256'),('metrics.json','metricsSha256'),('dev-report.json','devReportSha256'),('dev-scores.json','devScoresSha256')]:
        if rank.sha(directory/name)!=selection[key]:raise ValueError('SELECTION_BINDING')
    selected=Path(selection['selectedPath']);original=directory/'original.bin'
    ranker=ROOT/'app/src/main/assets/smarttyping/experiments/ru-ranker.bin'
    for path,key in [(selected,'selectedSha256'),(original,'originalSha256'),(ranker,'rankerSha256')]:
        if rank.sha(path)!=selection[key]:raise ValueError('MODEL_IDENTITY')
    before=neural.load_model(original);after=neural.load_model(selected)
    if (before.window,before.hidden,after.window,after.hidden)!=(48,48,48,48):raise ValueError('UNCHANGED_ARCHITECTURE_REQUIRED')
    groups=rank.verified_groups(OUT/'observations/test.jsonl','test',allow_test=True)
    fresh=compare(groups,ranker,before,after)
    previous=rank.verified_groups(ROOT/'build/typing-refinement/verified-observations/test.jsonl','test',allow_test=True)
    previous=compare(previous,ranker,before,after)
    oldrows,_,_=rank.baseline.load_public()
    legacy=[]
    for row,observation in oldrows:
        candidates=observation['generation']['alternatives']
        if row['split']=='holdout' and row['cohort']=='typo' and not row['noAuto'] and candidates:
            labels=np.array([int(c['text'].lower()==row['expectedSpelling'].lower()) for c in candidates])
            legacy.append((row,candidates,labels))
    legacy=compare(legacy,ranker,before,after)
    manifest=json.loads((OUT/'data/manifest.json').read_text());path=OUT/'data/test-text.jsonl'
    if rank.sha(path)!=manifest['files']['test-text.jsonl']:raise ValueError('FRESH_TEXT_IDENTITY')
    text=[json.loads(line) for line in path.read_text().splitlines()]
    x,y=neural.samples(text,48)
    ce={'before':neural.cross_entropy(before,x,y),'after':neural.cross_entropy(after,x,y),'characters':len(y)}
    dev=json.loads((directory/'dev-report.json').read_text())['models']
    accepted=accepts(selection['devTop1Before'],selection['devTop1After'],dev['original']['devCE'],dev[selection['selected']]['devCE'],fresh,[previous,legacy])
    result={'schemaVersion':1,'selected':selection['selected'],'selectedSha256':selection['selectedSha256'],
        'originalSha256':selection['originalSha256'],'rankerSha256':selection['rankerSha256'],
        'selectionSha256':rank.sha(selection_path),'freshManifestSha256':rank.sha(OUT/'data/manifest.json'),
        'freshObservationsSha256':rank.sha(OUT/'observations/test.jsonl'),'fresh':fresh,'exposedPrevious':previous,'exposedLegacy':legacy,
        'freshCharacterCrossEntropy':ce,'accepted':accepted,'gate':'Dev improvement, strict fresh combined top1 gain, neither exposed combined count lower; no reselection',
        'scope':'Synthetic public Wikipedia alternatives only; no private chats, automatic corrections or touch accuracy measured',
        'evaluationScriptSha256':rank.sha(Path(__file__))}
    rank.write(output,result);print(json.dumps(result))

if __name__=='__main__':main()
