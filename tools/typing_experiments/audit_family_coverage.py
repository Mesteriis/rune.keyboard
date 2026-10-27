"""Distinguish lexical dictionary gaps from exact protected-control construction."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

from holdout_ledger import load_ledger
from recover_legacy_families import sha

ROOT=Path(__file__).resolve().parents[2]
WORD=re.compile('[а-яё]{1,32}',re.IGNORECASE)


def classify_rows(rows,lexicon):
    counts=Counter();unresolved=[];protected=[];ids=set()
    for row in rows:
        if not isinstance(row.get('id'),str) or row['id'] in ids:raise ValueError('COVERAGE_ROW_IDENTITY')
        ids.add(row['id']);target=row.get('expectedSpelling')
        if target is None and row.get('cohort')=='correct':target=row.get('typed')
        if not isinstance(target,str) or not target:raise ValueError('COVERAGE_TARGET')
        if row.get('cohort')=='protected':
            word=row.get('word')
            if (row.get('group')!='protected' or row.get('noAuto') is not True
                    or not isinstance(word,str) or not WORD.fullmatch(word)
                    or row.get('typed')!=target or target!='@'+word):
                raise ValueError('COVERAGE_PROTECTED_CONSTRUCTION')
            category='protected-nonlexical-control';protected.append(row['id'])
        elif lexicon.analyses(target):category='dictionary-supported-lexical'
        else:
            category='unresolved-lexical' if WORD.fullmatch(target) else 'unresolved-nonlexical'
            unresolved.append(dict(id=row['id'],category=category))
        counts[category]+=1
    return dict(rows=len(rows),counts=dict(sorted(counts.items())),unresolved=unresolved,protectedControlIds=protected)


def source_path(entry):
    name=entry['id']
    if re.fullmatch('public-spelling-v(?:[7-9]|1[0-2])',name) or name=='public-legacy-spelling-v6':suffix='/rows.jsonl'
    elif name in ('public-ranker-history-train','public-ranker-history-dev','public-ranker-history-test'):
        suffix='/'+name.removeprefix('public-ranker-history-')+'-rows.jsonl'
    elif name.startswith('public-joint-history-') and not name.endswith('-families'):suffix='.jsonl'
    else:return None
    paths=[p for p in entry['bindings'] if p.endswith(suffix)]
    if len(paths)!=1:raise ValueError('COVERAGE_SOURCE_BINDING')
    return paths[0]


def audit(root,ledger,lexicon):
    result={};bindings={}
    for entry in ledger['entries']:
        path=source_path(entry)
        if path is None:continue
        if sha(Path(root)/path)!=entry['bindings'][path]:raise ValueError('COVERAGE_CORPUS_IDENTITY')
        bindings[path]=entry['bindings'][path]
        rows=[json.loads(line) for line in (Path(root)/path).read_text().splitlines()]
        if len(rows)!=entry['rowCount']:raise ValueError('COVERAGE_CORPUS_COUNT')
        result[entry['id']]=classify_rows(rows,lexicon)
    if not result:raise ValueError('COVERAGE_NO_SOURCES')
    totals=Counter()
    for value in result.values():totals.update(value['counts'])
    return dict(purpose='PUBLIC_FAMILY_COVERAGE_CLASSIFICATION_NOT_LEMMA_RECOVERY',
        sources=result,bindings=bindings,totals=dict(sorted(totals.items())),dictionary=lexicon.receipt(),
        sourceBindings={p:sha(Path(root)/p) for p in ('tools/typing_experiments/audit_family_coverage.py','tools/morphology/ranker.py')},
        modelCalls=0,ledgerChanged=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('output already exists')
    sys.path.insert(0,str(ROOT/'tools/morphology'))
    from ranker import PymorphyLexicon
    receipt=audit(ROOT,load_ledger(args.ledger),PymorphyLexicon(cache_size=16384))
    receipt['ledgerSha256']=sha(args.ledger)
    with args.output.open('x') as stream:stream.write(json.dumps(receipt,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
    print(json.dumps(receipt['totals']))


if __name__=='__main__':main()
