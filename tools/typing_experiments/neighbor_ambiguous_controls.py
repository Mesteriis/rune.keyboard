#!/usr/bin/env python3
"""Supplemental abstention controls, constructed after freeze without changing either policy."""
import argparse
from pathlib import Path
import hashlib
import neighbor_recovery as n


def prepare(corpus, replay, output):
    if output.exists(): raise ValueError('FRESH_OUTPUT_REQUIRED')
    dictionary = n.morphology()
    rows = {r['id']:r for r in n.read(corpus/'holdout.jsonl')}
    selected = []
    for observed in n.read(replay/'observations.jsonl'):
        row = rows[observed['id']]
        if row['noAuto']: continue
        candidates = observed['fullTokenGeneration']['neighborRecovery']['alternatives']
        if not candidates: continue
        cost = min(c['editCost'] for c in candidates)
        families = {dictionary.get(c['terminalKey']) for c in candidates
                    if c['editCost'] <= cost + .25}
        families.discard(None); families.discard(0)
        if len(families) < 2: continue
        selected.append(dict(row, id='ambiguous-'+row['id'], prefix='', expected=row['typed'],
                             noAuto=True, group='ambiguous', originId=row['id']))
    selected.sort(key=lambda r:hashlib.sha256(r['id'].encode()).digest())
    if len(selected) < 500: raise ValueError('INSUFFICIENT_AMBIGUOUS_POOL')
    selected = selected[:500]
    output.mkdir(parents=True)
    n.jsonl(output/'holdout.jsonl', selected)
    n.write(output/'manifest.json', dict(schema=1, publicOnly=True, supplemental=True,
        selection='500 hash-ordered public holdout typos with distinct plausible lemma rivals; empty context; keep original',
        generator=n.digest(__file__), sourceCorpus=n.digest(corpus/'manifest.json'),
        sourceReplay=n.digest(replay/'receipt.json'), morphology=n.digest(n.MORPH),
        files={'holdout.jsonl':n.digest(output/'holdout.jsonl')}))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for field in ('corpus','replay','output'):p.add_argument(field,type=Path)
    args=p.parse_args();prepare(args.corpus,args.replay,args.output)
