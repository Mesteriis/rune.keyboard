#!/usr/bin/env python3
"""Freeze selection on dev only, before evaluate_refinement.py opens the test split."""
import json
import numpy as np
import rank_refinement as rank
ROOT=rank.ROOT/'build/typing-refinement'
def main():
    output=ROOT/'selection.json'
    if output.exists(): raise ValueError('SELECTION_ALREADY_FROZEN')
    groups=rank.verified_groups(ROOT/'verified-observations/dev.jsonl','dev')
    trees=json.loads((ROOT/'ranker/dev-scores.json').read_text())
    tree_report=json.loads((ROOT/'ranker/dev-report.json').read_text())
    networks=json.loads((ROOT/'neural/dev-scores.json').read_text())
    assert trees['rowIds']==[r['id'] for r,_,_ in groups]
    assert networks['observationsSha256']==rank.sha(ROOT/'verified-observations/dev.jsonl')
    chosen_tree=tree_report['selected'];chosen_network=networks['selected']
    if chosen_tree=='shipped' or chosen_network=='shipped':raise ValueError('NO_REFINEMENT_SELECTED')
    by_id={row['id']:row for row in networks['rows']}
    neural=[]
    for row,candidates,_ in groups:
        observed=by_id[row['id']]
        assert observed['candidates']==[c['text'] for c in candidates]
        neural.append(observed['scores'][chosen_network])
    metrics=[]
    for gain in [0,.25,.5,1]:
        values=[np.array(a)+gain*np.array(b) for a,b in zip(trees['scores'][chosen_tree],neural)]
        metrics.append({'gain':gain,'correctTop1':rank.accuracy(groups,values)})
    chosen=max(metrics,key=lambda x:(x['correctTop1'],-x['gain']))
    rank.write(output,{'ranker':chosen_tree,'rankerSha256':rank.sha(ROOT/'ranker'/f'{chosen_tree}.bin'),
        'neural':chosen_network,'neuralSha256':rank.sha(ROOT/'neural'/f'{chosen_network}.bin'),
        'blendGain':chosen['gain'],'devBlend':metrics,'selectionFrozenBeforeTest':True,
        'scriptSha256':rank.sha(rank.__file__)})
if __name__=='__main__':main()
