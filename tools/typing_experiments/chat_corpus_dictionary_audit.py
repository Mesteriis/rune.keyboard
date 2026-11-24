#!/usr/bin/env python3
"""Count dictionary coverage of source controls without guessing correctness."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

from typing_quality_slices import evaluate,read

ROOT=Path(__file__).resolve().parents[2]


def audit(rows,observations,lexicon):
    evaluate(rows,observations)
    counts=Counter()
    for row,obs in zip(rows,observations,strict=True):
        if row.get('edit_kind')!='control':continue
        if row.get('cohort')!='correct' or row.get('noAuto') is not True or row.get('typed')!=row.get('expectedSpelling'):
            raise ValueError('CHAT_DICTIONARY_CONTROL')
        known=bool(lexicon.analyses(row['typed']));status='dictionary_known' if known else 'dictionary_unknown'
        changed=obs['boundaryChangedBeyondInsertedSpace'];counts[status+'_changed' if changed else status+'_unchanged']+=1
        if changed:
            case=obs['afterBoundary']['text'].casefold()==(obs['beforeBoundary']['text']+' ').casefold()
            counts[status+'_case_only' if case else status+'_other_change']+=1
    if not counts:raise ValueError('CHAT_DICTIONARY_EMPTY')
    return dict(purpose='DICTIONARY_COVERAGE_NOT_GROUND_TRUTH',counts=dict(sorted(counts.items())),
        caveat='Dictionary absence is not evidence that a word is incorrect; no intent is inferred.',modelCalls=0)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('rows','observations','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('output already exists')
    sys.path.insert(0,str(ROOT/'tools/morphology'));from ranker import PymorphyLexicon
    lexicon=PymorphyLexicon(cache_size=16384);result=audit(read(args.rows),read(args.observations),lexicon)
    result['dictionary']=lexicon.receipt()
    result['inputs']={name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in [('rows',args.rows),('observations',args.observations)]}
    result['sources']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),ROOT/'tools/morphology/ranker.py')}
    args.output.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps(result['counts']))

if __name__=='__main__':main()
