"""Train a small offline pairwise ranker on disclosed EWT product candidates.

The output is aggregate development evidence, never a product model or
qualification. Incomplete searches remain incomplete; no auto gate is changed.
"""
import argparse
from collections import Counter
import json
import math
import os
from pathlib import Path

import ewt_product_replay as replay
import register_ewt_product_candidates as candidates
import register_ewt_product_contexts as contexts

ROOT=Path(__file__).resolve().parents[2]
EPOCHS=(0,25,100)
FEATURES=('editCost','frequencyRank','unitDistance','lengthDifference','repeatedCharacterEdits','repetitionBonus')
COMPLETIONS={'COMPLETE','PROTECTED','VALID_WORD','STATES_EXHAUSTED','VERIFIED_EXHAUSTED','CANCELLED','UNAVAILABLE','READER_FAILURE'}


def features(candidate):
    values=[]
    for key in FEATURES:
        value=candidate.get(key)
        if type(value) not in (int,float) or not math.isfinite(value) or value<0:
            raise ValueError('EWT_RANK_FEATURE')
        values.append(float(value))
    edit,rank,unit,length,repeated,bonus=values
    if not 1<=rank<=2147483647 or edit>20 or unit>32 or length>32 or repeated>32 or bonus>10:
        raise ValueError('EWT_RANK_FEATURE')
    return (-edit/4,-math.log1p(rank)/22,-unit/4,-length/4,-repeated/4,bonus)


def build_groups(rows,labels,observed):
    if not len(rows)==len(labels)==len(observed):raise ValueError('EWT_RANK_ALIGNMENT')
    targets={part:{l['expected'].casefold() for l in labels if l.get('kind')=='annotated' and l.get('part')==part}
             for part in ('train','dev','test')}
    groups={p:[] for p in ('train','dev','test')};counts={p:Counter() for p in groups}
    for row,label,obs in zip(rows,labels,observed,strict=True):
        if label.get('id')!=row.get('id') or any(row[k]!=obs.get(k) for k in ('language','split','prefix','typed')):
            raise ValueError('EWT_RANK_ALIGNMENT')
        if label.get('kind')!='annotated':continue
        part=label.get('part');target=label.get('expected')
        if part not in groups or not isinstance(target,str) or not target:raise ValueError('EWT_RANK_LABEL')
        if row['split']!={'train':'train','dev':'calibration','test':'holdout'}[part]:raise ValueError('EWT_RANK_ALIGNMENT')
        target=target.casefold();stats=counts[part];stats['rows']+=1
        gen=obs.get('fullTokenGeneration');view=obs.get('candidateView')
        if not isinstance(gen,dict) or gen.get('completion') not in COMPLETIONS or not isinstance(gen.get('alternatives'),list) or not isinstance(view,dict) or not isinstance(view.get('candidates'),list):
            raise ValueError('EWT_RANK_GENERATION')
        if any(not isinstance(x,dict) for x in view['candidates']):raise ValueError('EWT_RANK_CANDIDATE')
        visible=[x for x in view['candidates'] if x.get('role')!='ORIGINAL']
        if any(not isinstance(x.get('text'),str) or not x['text'] for x in visible):raise ValueError('EWT_RANK_CANDIDATE')
        positions=[i for i,x in enumerate(visible) if x['text'].casefold()==target]
        stats['allTargetVisible']+=bool(positions);stats['allTargetVisibleFirst']+=positions==[0]
        if (part=='dev' and target in targets['train']) or (part=='test' and target in targets['train']|targets['dev']):
            stats['seenTargetExcluded']+=1;continue
        if any(not isinstance(x,dict) for x in gen['alternatives']):raise ValueError('EWT_RANK_CANDIDATE')
        values=[x for x in gen['alternatives'] if x.get('language')=='en']
        if any(not isinstance(x.get('text'),str) or not x['text'] for x in values):raise ValueError('EWT_RANK_CANDIDATE')
        matches=[i for i,x in enumerate(values) if x['text'].casefold()==target]
        if len(matches)!=1:stats['targetAbsentOrAmbiguous']+=1;continue
        stats['targetInPool']+=1
        if len(values)<2:stats['singleCandidate']+=1;continue
        stats['competingCandidates']+=1;stats['completion:'+str(gen.get('completion'))]+=1
        groups[part].append((tuple(features(x) for x in values),matches[0]))
    return groups,{p:dict(sorted(c.items())) for p,c in counts.items()}


def train(groups,epochs):
    if epochs not in EPOCHS[1:] or not groups:raise ValueError('EWT_RANK_TRAIN')
    pairs=[]
    for vectors,winner in groups:
        if not 0<=winner<len(vectors) or len(vectors)<2:raise ValueError('EWT_RANK_TRAIN')
        pairs.extend(tuple(a-b for a,b in zip(vectors[winner],other,strict=True))
                     for i,other in enumerate(vectors) if i!=winner)
    weights=[0.0]*len(FEATURES)
    for epoch in range(epochs):
        gradient=[0.0]*len(weights)
        for pair in pairs:
            score=sum(w*x for w,x in zip(weights,pair,strict=True))
            scale=1/(1+math.exp(max(-40,min(40,score))))
            for i,x in enumerate(pair):gradient[i]+=scale*x
        rate=0.4/(1+epoch/50)
        for i in range(len(weights)):
            weights[i]+=rate*(gradient[i]/len(pairs)-0.01*weights[i])
    return tuple(weights)


def measure(groups,weights):
    correct=0
    for vectors,winner in groups:
        if weights is None:ranked=0
        else:ranked=max(range(len(vectors)),key=lambda i:(sum(w*x for w,x in zip(weights,vectors[i],strict=True)),-i))
        correct+=ranked==winner
    return dict(groups=len(groups),top1=correct)


def experiment(groups):
    if any(not groups[p] for p in ('train','dev','test')):raise ValueError('EWT_RANK_EMPTY_PARTITION')
    choices={0:None,25:train(groups['train'],25),100:train(groups['train'],100)}
    dev={str(e):measure(groups['dev'],w) for e,w in choices.items()}
    # A tie keeps the earlier/simpler baseline; the test set is never used here.
    chosen=min(EPOCHS,key=lambda e:(-dev[str(e)]['top1'],e))
    return dict(development=dev,chosenEpochs=chosen,testBaseline=measure(groups['test'],None),
        testSelected=measure(groups['test'],choices[chosen]),
        learnedWeights={str(e):[round(x,9) for x in weights] for e,weights in choices.items() if weights is not None},
        trainGroups=len(groups['train']),sourceLabelsQualified=False,independentQualification=False,productBehaviorChanged=False)


def run(data,run):
    ledger_raw=candidates.LEDGER.read_bytes();ledger=candidates.control.validate(json.loads(ledger_raw))
    for module in (contexts,candidates):
        expected=module.entry()
        if [e for e in ledger['entries'] if e['id']==module.ENTRY]!=[expected]:raise ValueError('EWT_RANK_EXCLUSIONS')
    summary=replay.summarize(data,run)
    source=json.loads(contexts.FIXTURE.read_bytes());candidate_fixture=json.loads(candidates.FIXTURE.read_bytes())
    paths=(data/'inputs.jsonl',data/'labels.jsonl',run/'projection.jsonl');raw=[p.read_bytes() for p in paths]
    if (replay.model.sha(raw[0])!=source['inputSha256'] or replay.model.sha(raw[1])!=source['labelSha256'] or
        replay.model.sha(raw[2])!=candidate_fixture['projectionSha256'] or candidate_fixture['projectionSha256']!=summary['projectionSha256']):
        raise ValueError('EWT_RANK_SOURCE_DRIFT')
    rows,labels,observed=([json.loads(x) for x in data_.splitlines()] for data_ in raw)
    groups,counts=build_groups(rows,labels,observed);result=experiment(groups)
    if candidates.LEDGER.read_bytes()!=ledger_raw or any(p.read_bytes()!=value for p,value in zip(paths,raw,strict=True)):
        raise ValueError('EWT_RANK_INPUT_DRIFT')
    return dict(schemaVersion=1,scope='disclosed-ewt-pairwise-development-not-qualification',features=list(FEATURES),
        counts=counts,results=result,sourceFixtureSha256=replay.model.sha(contexts.FIXTURE.read_bytes()),
        candidateFixtureSha256=replay.model.sha(candidates.FIXTURE.read_bytes()),projectionSha256=summary['projectionSha256'],
        registrySha256=replay.model.sha(ledger_raw),analyzerSha256=replay.model.sha(Path(__file__).read_bytes()))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('data','replay','output'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();os.umask(0o077);output=args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('EWT_RANK_OUTPUT')
    result=run(args.data,args.replay)
    with output.open('x',encoding='utf-8') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps({'counts':result['counts'],'results':result['results']},sort_keys=True))


if __name__=='__main__':main()
