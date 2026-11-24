#!/usr/bin/env python3
"""Conservatively quarantine public historical word-ranking target families."""
import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import sys

from holdout_ledger import keys_for,load_ledger,validate_ledger
from source_identities import unsupported_surface_key

ROOT=Path(__file__).resolve().parents[2]
ENTRY='public-word-ranking-family-quarantine-v1'
PARENTS=('public-word-ranking-data-articles-v1','public-word-ranking-contexts-v1')


def derive(rows,lexicon,article_keys):
    if not rows:raise ValueError('WORD_FAMILY_EMPTY')
    ids=set();families=set();unsupported=set();counts=Counter()
    for row in rows:
        identity=row.get('id');target=row.get('expectedSpelling');cohort=row.get('cohort');part=row.get('partition')
        if not isinstance(identity,str) or not identity or identity in ids:raise ValueError('WORD_FAMILY_ROW_ID')
        ids.add(identity)
        if (row.get('language')!='ru' or part not in ('train','dev','test') or not isinstance(target,str) or not target
                or cohort not in ('correct','typo') or type(row.get('noAuto')) is not bool
                or row['noAuto']!=(cohort=='correct') or (cohort=='correct' and row.get('typed')!=target)):
            raise ValueError('WORD_FAMILY_ROW_SCOPE')
        if keys_for([dict(article=row.get('articleId'))],'article')-article_keys:raise ValueError('WORD_FAMILY_ARTICLE')
        analyses=lexicon.analyses(target)
        if analyses:
            families.update(keys_for([dict(families=sorted({a.lemma for a in analyses}))],'family'))
            counts['resolvedRows']+=1
        else:
            surface=unsupported_surface_key(target)
            if surface is None:raise ValueError('WORD_FAMILY_NONLEXICAL')
            unsupported.add(surface);counts['unsupportedRows']+=1
        counts['rows']+=1;counts[part+'Rows']+=1
    return sorted(families),sorted(unsupported),dict(sorted(counts.items()))


def build(base,rows,lexicon,bindings):
    result=copy.deepcopy(validate_ledger(base));entries={e['id']:e for e in result['entries']}
    if ENTRY in entries:raise ValueError('WORD_FAMILY_ALREADY_IMPORTED')
    if any(parent not in entries for parent in PARENTS):raise ValueError('WORD_FAMILY_PARENTS')
    parent=entries[PARENTS[0]]
    families,unsupported,counts=derive(rows,lexicon,set(parent['keys'].get('article',[])))
    if not families:raise ValueError('WORD_FAMILY_EMPTY')
    previously_blocked={key for e in result['entries'] if e['usage'] in ('supervised','prepared-training-quarantine') for key in e['keys'].get('family',[])}
    prior_surfaces={key for e in result['entries'] for key in e.get('unsupportedSurfaceKeys',[])}
    receipt=dict(purpose='PUBLIC_WORD_RANKING_FAMILY_QUARANTINE_NOT_QUALIFICATION',counts=counts,
        distinctFamilyKeys=len(families),newFamilyKeys=len(set(families)-previously_blocked),
        unsupportedSurfaceKeys=len(unsupported),newUnsupportedSurfaceKeys=len(set(unsupported)-prior_surfaces),
        dictionary=lexicon.receipt(),bindings=bindings,modelCalls=0,trainingConsumptionEstablished=False)
    receipt_hash=hashlib.sha256(json.dumps(receipt,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    entry=dict(id=ENTRY,usage='prepared-training-quarantine',keys={'family':families},missingAxes=[],bindings=bindings,
        parentEntries=list(PARENTS),recoveryReceiptSha256=receipt_hash,
        notes='All dictionary analyses of public historical targets are conservatively quarantined. Unknown surfaces are exact exclusions, not inferred lemmas.')
    if unsupported:entry['unsupportedSurfaceKeys']=unsupported
    result['entries'].append(entry)
    return validate_ledger(result),receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():parser.error('output already exists')
    old_path=sys.path[:]
    try:
        sys.path[:0]=[str(ROOT/'tools/ci'),str(ROOT/'tools/morphology')]
        import historical_model_fixtures as fixtures
        from ranker import PymorphyLexicon
    finally:sys.path[:]=old_path
    data=ROOT/'tools/ci/historical-model-fixtures-v1'
    source_paths=[data/name for name in ('manifest.json','files.tar.gz','articles.jsonl','NOTICE.md')]
    source_paths += [ROOT/name for name in ('tools/ci/historical_model_fixtures.py','tools/ci/historical_model_sources.py',
        'tools/ci/historical_data_fixtures.py','tools/ci/historical-model-sources-v1/manifest.json',
        'tools/ci/historical-data-v1/manifest.json','tools/typing_experiments/frozen_source_identity.py',
        'tools/morphology/ranker.py','tools/typing_experiments/holdout_ledger.py','tools/typing_experiments/source_identities.py',
        'tools/typing_experiments/import_word_history_families.py')]
    def sha(path):
        with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
    bindings={str(p.relative_to(ROOT)):sha(p) for p in source_paths};base_raw=args.base.read_bytes();base=load_ledger(args.base)
    _,payloads=fixtures.verify()
    rows=[json.loads(line) for line in payloads['build/typing-word-ranking/data/all-rows.jsonl'].splitlines()]
    ledger,receipt=build(base,rows,PymorphyLexicon(cache_size=16384),bindings)
    if args.base.read_bytes()!=base_raw or any(sha(ROOT/path)!=digest for path,digest in bindings.items()):raise ValueError('WORD_FAMILY_INPUT_DRIFT')
    args.output.mkdir(parents=True,exist_ok=False)
    for name,value in (('ledger.json',ledger),('receipt.json',receipt)):
        (args.output/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({key:receipt[key] for key in ('counts','distinctFamilyKeys','newFamilyKeys','unsupportedSurfaceKeys','newUnsupportedSurfaceKeys')}))

if __name__=='__main__':main()
