#!/usr/bin/env python3
"""Evaluate one dev-selected candidate model; no model selection on test results."""
from pathlib import Path
import json
import argparse
import word_evaluation_receipt as binding
from evaluate_extra_epochs import compare

ROOT=Path(__file__).resolve().parents[2]
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

def run(source=OUT,historical_reproduction=False,legacy_root=ROOT,regression_row_limit=None):
    source=Path(source).resolve()
    frozen=binding.freeze(source,historical_reproduction,ROOT,legacy_root,regression_row_limit)
    output=source/'evaluation.json'
    binding.require(not output.exists() and not output.is_symlink(),'EVALUATION_ALREADY_REVEALED')
    import numpy as np
    import neural_refinement as neural
    import rank_refinement as rank
    import promote_refinement as promotion
    selection_path=source/'training/selection.json';selection=frozen['selection']
    selected=frozen['selected'];original=frozen['original'];tree=frozen['ranker']
    promotion.validate_tree(tree.read_bytes(),rank.FEATURES)
    before=neural.load_model(original);after=neural.load_model(selected)
    if (before.window,before.hidden,after.window,after.hidden)!=(48,48,48,48):raise ValueError('FIXED_ARCHITECTURE_REQUIRED')
    groups=rank.verified_groups(source/'observations/test.jsonl','test',allow_test=True)
    fresh=report_cohorts(groups,tree,before,after)
    manifest=json.loads((source/'data/manifest.json').read_text())
    rows=frozen['rows']
    for key,errors in [('all',(1,2,3)),('single',(1,)),('hard',(2,3)),('double',(2,)),('triple',(3,))]:
        fresh[key]['totalTypoRows']=sum(r['errorCount'] in errors for r in rows)
    controls=[r for r in rows if r['cohort']=='correct']
    if any(r['typed']!=r['expectedSpelling'] or not r['noAuto'] or r['errorCount']!=0 for r in controls):raise ValueError('CORRECT_CONTROL_MUTATED')
    old_results={}
    for name,path in [('previous',frozen['previous']/'verified-observations/test.jsonl'),('extraEpochs',frozen['extra']/'observations/test.jsonl')]:
        regression=typo_groups(rank.verified_groups(path,'test',allow_test=True))
        if regression_row_limit is not None:regression=regression[:regression_row_limit]
        old_results[name]=compare(regression,tree,before,after)
    oldrows=frozen['legacyRows'];legacy=[]
    for row,observation in oldrows:
        cs=observation['generation']['alternatives']
        if row['split']=='holdout' and row['cohort']=='typo' and not row['noAuto'] and cs:
            legacy.append((row,cs,np.array([int(c['text'].lower()==row['expectedSpelling'].lower()) for c in cs])))
    if regression_row_limit is not None:legacy=legacy[:regression_row_limit]
    binding.require(bool(legacy),'EVALUATION_LEGACY_COHORT')
    old_results['legacy']=compare(legacy,tree,before,after)
    text_path=source/'data/test-text.jsonl'
    if rank.sha(text_path)!=manifest['files'][text_path.name]:raise ValueError('TEST_TEXT_IDENTITY')
    x,y=neural.samples([json.loads(s) for s in text_path.read_text().splitlines()],48)
    ce={'before':neural.cross_entropy(before,x,y),'after':neural.cross_entropy(after,x,y),'characters':len(y)}
    result={'schemaVersion':1,'selected':selection['selected'],'selectedSha256':selection['selectedSha256'],
        'originalSha256':selection['originalSha256'],'rankerSha256':selection['rankerSha256'],
        'selectionSha256':rank.sha(selection_path),'freshManifestSha256':rank.sha(source/'data/manifest.json'),
        'freshObservationsSha256':rank.sha(source/'observations/test.jsonl'),
        'fresh':fresh,'correctControls':{'rows':len(controls),'typedEqualsExpected':True,'trainingAndTypoDenominator':'excluded','scope':'data-integrity control; not a learned false-correction metric'},
        'exposedRegressions':old_results,'freshCharacterCrossEntropy':ce,
        'observedGatePassed':accepts(fresh['all'],fresh['single'],fresh['hard'],list(old_results.values())),
        'gate':'Fresh overall and hard cohorts improve strictly, fresh singles and all exposed combined counts do not decrease; no reselection',
        'scope':'Public synthetic manual alternatives; missing/absent candidates remain failures; no auto-edit or chat-accuracy claim',
        'evaluationScriptSha256':rank.sha(Path(__file__))}
    binding.finish_report(frozen,result,result['observedGatePassed'])
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
