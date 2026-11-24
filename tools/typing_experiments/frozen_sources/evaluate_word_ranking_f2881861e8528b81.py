#!/usr/bin/env python3
"""Evaluate one dev-selected candidate model; no model selection on test results."""
from pathlib import Path
import json
import numpy as np
import neural_refinement as neural
import rank_refinement as rank
from evaluate_extra_epochs import compare

ROOT=rank.ROOT
OUT=ROOT/'build/typing-word-ranking'

def typo_groups(groups):
    return [(r,cs,y) for r,cs,y in groups if r['cohort']=='typo' and not r['noAuto']]

def counts(result):
    return tuple(result['models'][name]['combinedCorrectTop1'] for name in ('before','after'))

def accepts(fresh,single,hard,regressions):
    before,after=counts(fresh)
    single_before,single_after=counts(single)
    hard_before,hard_after=counts(hard)
    return after>before and hard_after>hard_before and single_after>=single_before and all(counts(r)[1]>=counts(r)[0] for r in regressions)

def report_cohorts(groups,tree,before,after):
    typos=typo_groups(groups)
    return {'all':compare(typos,tree,before,after),
            'single':compare([g for g in typos if g[0]['errorCount']==1],tree,before,after),
            'hard':compare([g for g in typos if g[0]['errorCount']>=2],tree,before,after),
            'double':compare([g for g in typos if g[0]['errorCount']==2],tree,before,after),
            'triple':compare([g for g in typos if g[0]['errorCount']==3],tree,before,after)}

def main():
    output=OUT/'evaluation.json'
    if output.exists():raise ValueError('EVALUATION_ALREADY_REVEALED')
    directory=OUT/'training';selection_path=directory/'selection.json'
    selection=json.loads(selection_path.read_text())
    if not selection['selectionFrozenBeforeTest'] or selection['testAccess']:raise ValueError('FROZEN_DEV_SELECTION_REQUIRED')
    for name,key in [('plan.json','planSha256'),('metrics.json','metricsSha256'),('dev-report.json','devReportSha256'),('dev-scores.json','devScoresSha256')]:
        if rank.sha(directory/name)!=selection[key]:raise ValueError('SELECTION_BINDING')
    selected=Path(selection['selectedPath']);original=directory/'original.bin';tree=ROOT/'app/src/main/assets/smarttyping/experiments/ru-ranker.bin'
    for path,key in [(selected,'selectedSha256'),(original,'originalSha256'),(tree,'rankerSha256')]:
        if rank.sha(path)!=selection[key]:raise ValueError('MODEL_IDENTITY')
    before=neural.load_model(original);after=neural.load_model(selected)
    if (before.window,before.hidden,after.window,after.hidden)!=(48,48,48,48):raise ValueError('FIXED_ARCHITECTURE_REQUIRED')
    groups=rank.verified_groups(OUT/'observations/test.jsonl','test',allow_test=True)
    fresh=report_cohorts(groups,tree,before,after)
    manifest=json.loads((OUT/'data/manifest.json').read_text())
    rows=[json.loads(s)['row'] for s in (OUT/'observations/test.jsonl').read_text().splitlines()]
    for key,errors in [('all',(1,2,3)),('single',(1,)),('hard',(2,3)),('double',(2,)),('triple',(3,))]:
        fresh[key]['totalTypoRows']=sum(r['errorCount'] in errors for r in rows)
    controls=[r for r in rows if r['cohort']=='correct']
    if any(r['typed']!=r['expectedSpelling'] or not r['noAuto'] or r['errorCount']!=0 for r in controls):raise ValueError('CORRECT_CONTROL_MUTATED')
    old_results={}
    for name,path in [('previous',ROOT/'build/typing-refinement/verified-observations/test.jsonl'),('extraEpochs',ROOT/'build/typing-extra-epochs/observations/test.jsonl')]:
        old_results[name]=compare(typo_groups(rank.verified_groups(path,'test',allow_test=True)),tree,before,after)
    oldrows,_,_=rank.baseline.load_public();legacy=[]
    for row,observation in oldrows:
        cs=observation['generation']['alternatives']
        if row['split']=='holdout' and row['cohort']=='typo' and not row['noAuto'] and cs:
            legacy.append((row,cs,np.array([int(c['text'].lower()==row['expectedSpelling'].lower()) for c in cs])))
    old_results['legacy']=compare(legacy,tree,before,after)
    text_path=OUT/'data/test-text.jsonl'
    if rank.sha(text_path)!=manifest['files'][text_path.name]:raise ValueError('TEST_TEXT_IDENTITY')
    x,y=neural.samples([json.loads(s) for s in text_path.read_text().splitlines()],48)
    ce={'before':neural.cross_entropy(before,x,y),'after':neural.cross_entropy(after,x,y),'characters':len(y)}
    result={'schemaVersion':1,'selected':selection['selected'],'selectedSha256':selection['selectedSha256'],
        'originalSha256':selection['originalSha256'],'rankerSha256':selection['rankerSha256'],
        'selectionSha256':rank.sha(selection_path),'freshManifestSha256':rank.sha(OUT/'data/manifest.json'),
        'freshObservationsSha256':rank.sha(OUT/'observations/test.jsonl'),
        'fresh':fresh,'correctControls':{'rows':len(controls),'typedEqualsExpected':True,'trainingAndTypoDenominator':'excluded','scope':'data-integrity control; not a learned false-correction metric'},
        'exposedRegressions':old_results,'freshCharacterCrossEntropy':ce,
        'accepted':accepts(fresh['all'],fresh['single'],fresh['hard'],list(old_results.values())),
        'gate':'Fresh overall and hard cohorts improve strictly, fresh singles and all exposed combined counts do not decrease; no reselection',
        'scope':'Public synthetic manual alternatives; missing/absent candidates remain failures; no auto-edit or chat-accuracy claim',
        'evaluationScriptSha256':rank.sha(Path(__file__))}
    rank.write(output,result);print(json.dumps(result))

if __name__=='__main__':main()
