#!/usr/bin/env python3
"""Exclude dictionary families from the disclosed additional-epoch test."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

from holdout_ledger import load_ledger,validate_ledger
from import_word_history_families import derive

ROOT=Path(__file__).resolve().parents[2]
ENTRY='public-extra-epochs-family-exclusions-v1'
PARENT='public-extra-epochs-data-history-v1'


def build(base,rows,lexicon,bindings):
    result=copy.deepcopy(validate_ledger(base));entries={e['id']:e for e in result['entries']}
    if ENTRY in entries:raise ValueError('EPOCH_FAMILY_ALREADY_IMPORTED')
    if PARENT not in entries:raise ValueError('EPOCH_FAMILY_PARENT')
    if any(r.get('partition')!='test' or r.get('split')!='holdout' for r in rows):raise ValueError('EPOCH_FAMILY_SCOPE')
    families,unsupported,counts=derive(rows,lexicon,set(entries[PARENT]['keys'].get('article',[])))
    if not families:raise ValueError('EPOCH_FAMILY_EMPTY')
    blocked={key for e in result['entries'] for key in e['keys'].get('family',[])}
    prior_surfaces={key for e in result['entries'] for key in e.get('unsupportedSurfaceKeys',[])}
    receipt=dict(purpose='PUBLIC_EXTRA_EPOCH_TEST_FAMILY_EXCLUSIONS_NOT_QUALIFICATION',counts=counts,
        distinctFamilyKeys=len(families),newFamilyKeys=len(set(families)-blocked),
        unsupportedSurfaceKeys=len(unsupported),newUnsupportedSurfaceKeys=len(set(unsupported)-prior_surfaces),
        dictionary=lexicon.receipt(),bindings=bindings,modelCalls=0,supervisedTrainingClaim=False)
    digest=hashlib.sha256(json.dumps(receipt,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    entry=dict(id=ENTRY,usage='historical-family-exclusion',keys={'family':families},missingAxes=[],bindings=bindings,
        parentEntries=[PARENT],recoveryReceiptSha256=digest,
        notes='All dictionary-only target analyses of the previously disclosed additional-epoch test. Not supervised training or fresh qualification.')
    if unsupported:entry['unsupportedSurfaceKeys']=unsupported
    result['entries'].append(entry)
    return validate_ledger(result),receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():parser.error('output already exists')
    old_path=sys.path[:]
    try:
        sys.path[:0]=[str(ROOT/'tools/ci'),str(ROOT/'tools/morphology')]
        import historical_data_fixtures as fixtures
        from ranker import PymorphyLexicon
    finally:sys.path[:]=old_path
    data=ROOT/'tools/ci/historical-data-v1'
    paths=[data/name for name in ('manifest.json','files.tar.gz','articles.jsonl','NOTICE.md')]
    paths += [ROOT/name for name in ('tools/ci/historical_data_fixtures.py','tools/model/rune-text-0.2/source-lock.json',
        'tools/typing_experiments/frozen_source_identity.py','tools/typing_experiments/frozen_sources/manifest.json',
        'tools/morphology/ranker.py','tools/typing_experiments/holdout_ledger.py','tools/typing_experiments/source_identities.py',
        'tools/typing_experiments/import_word_history_families.py','tools/typing_experiments/import_epoch_history_families.py')]
    def sha(path):
        with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
    bindings={str(path.relative_to(ROOT)):sha(path) for path in paths};base_raw=args.base.read_bytes();base=load_ledger(args.base)
    payloads=fixtures.verify();rows=[json.loads(line) for line in payloads['typing-extra-epochs/data/test-rows.jsonl'].splitlines()]
    if len(rows)!=1500:raise ValueError('EPOCH_FAMILY_COUNT')
    ledger,receipt=build(base,rows,PymorphyLexicon(cache_size=16384),bindings)
    if args.base.read_bytes()!=base_raw or any(sha(ROOT/path)!=digest for path,digest in bindings.items()):raise ValueError('EPOCH_FAMILY_INPUT_DRIFT')
    args.output.mkdir(parents=True,exist_ok=False)
    for name,value in (('ledger.json',ledger),('receipt.json',receipt)):
        (args.output/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:receipt[k] for k in ('counts','distinctFamilyKeys','newFamilyKeys','unsupportedSurfaceKeys')}))

if __name__=='__main__':main()
