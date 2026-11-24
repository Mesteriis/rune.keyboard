#!/usr/bin/env python3
"""Verify durable exclusions of archived public refinement data, without scoring."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from holdout_ledger import keys_for,load_ledger
from import_word_history_families import derive

ROOT=Path(__file__).resolve().parents[2]
EXPECTED={'train':5000,'dev':1000,'test':1500}
SPLITS={'train':'calibration','dev':'diagnostic','test':'holdout'}


def audit(ledger,partitions,lexicon,bindings):
    if set(partitions)!=set(EXPECTED):raise ValueError('REFINEMENT_COVERAGE_PARTITIONS')
    entries=ledger['entries'];articles={key for e in entries for key in e['keys'].get('article',[])}
    contexts={key for e in entries for key in e['keys'].get('context',[])}
    all_families={key for e in entries for key in e['keys'].get('family',[])}
    training_families={key for e in entries if e['usage'] in ('supervised','prepared-training-quarantine') for key in e['keys'].get('family',[])}
    surfaces={key for e in entries for key in e.get('unsupportedSurfaceKeys',[])}
    counts={};all_ids=set()
    for part,rows in partitions.items():
        if (len(rows)!=EXPECTED[part] or any(r.get('partition')!=part or r.get('split')!=SPLITS[part] for r in rows)):
            raise ValueError('REFINEMENT_COVERAGE_SCOPE')
        ids={r.get('id') for r in rows}
        if len(ids)!=len(rows) or all_ids & ids:raise ValueError('REFINEMENT_COVERAGE_IDS')
        all_ids.update(ids)
        families,unsupported,derived=derive(rows,lexicon,articles)
        source_articles=keys_for([{'article':r['articleId']} for r in rows],'article')
        source_contexts=keys_for(rows,'context')
        allowed=training_families if part=='train' else all_families
        missing=dict(article=len(source_articles-articles),context=len(source_contexts-contexts),
            family=len(set(families)-allowed),unsupportedSurface=len(set(unsupported)-surfaces))
        if any(missing.values()):raise ValueError('REFINEMENT_COVERAGE_GAP:'+part)
        counts[part]=dict(rows=len(rows),articleKeys=len(source_articles),contextKeys=len(source_contexts),
            familyKeys=len(families),unsupportedSurfaces=len(unsupported),resolvedRows=derived.get('resolvedRows',0),
            unsupportedRows=derived.get('unsupportedRows',0),familyScope='training-quarantine' if part=='train' else 'all-history',missing=missing)
    return dict(purpose='PUBLIC_REFINEMENT_DURABLE_EXCLUSION_AUDIT_NOT_QUALIFICATION',counts=counts,
        dictionary=lexicon.receipt(),bindings=bindings,modelCalls=0,trainingConsumptionEstablished=False,
        fullSourceSentencesEstablished=False,independentQualification=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--ledger',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():p.error('output already exists')
    old=sys.path[:]
    try:
        sys.path[:0]=[str(ROOT/'tools/ci'),str(ROOT/'tools/morphology')]
        import historical_data_fixtures as fixtures
        from ranker import PymorphyLexicon
    finally:sys.path[:]=old
    files=[ROOT/'tools/ci/historical-data-v1'/name for name in ('manifest.json','files.tar.gz','articles.jsonl','NOTICE.md')]
    files += [ROOT/name for name in ('tools/ci/historical_data_fixtures.py','tools/model/rune-text-0.2/source-lock.json',
        'tools/typing_experiments/frozen_source_identity.py','tools/typing_experiments/frozen_sources/manifest.json',
        'tools/morphology/ranker.py','tools/typing_experiments/holdout_ledger.py','tools/typing_experiments/source_identities.py',
        'tools/typing_experiments/import_word_history_families.py','tools/typing_experiments/audit_refinement_coverage.py')]
    def digest(path):
        with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
    bindings={str(path.relative_to(ROOT)):digest(path) for path in files};ledger_raw=a.ledger.read_bytes();ledger=load_ledger(a.ledger)
    payloads=fixtures.verify();parts={part:[json.loads(line) for line in payloads[f'typing-refinement/data/{part}-rows.jsonl'].splitlines()] for part in EXPECTED}
    receipt=audit(ledger,parts,PymorphyLexicon(cache_size=16384),bindings)
    if a.ledger.read_bytes()!=ledger_raw or any(digest(ROOT/name)!=h for name,h in bindings.items()):raise ValueError('REFINEMENT_COVERAGE_INPUT_DRIFT')
    receipt['ledgerSha256']=hashlib.sha256(ledger_raw).hexdigest()
    a.output.write_text(json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps(receipt['counts']))

if __name__=='__main__':main()
