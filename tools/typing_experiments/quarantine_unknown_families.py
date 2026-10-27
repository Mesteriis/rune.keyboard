"""Exclude unsupported public word surfaces without inventing canonical families."""
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import sys

from audit_family_coverage import source_path
from holdout_ledger import load_ledger,validate_ledger
from recover_legacy_families import sha
from source_identities import unsupported_surface_key

ROOT=Path(__file__).resolve().parents[2]


def classify(rows,lexicon,predict_methods):
    keys=set();details=[];counts=Counter()
    for row in rows:
        if row.get('cohort')=='protected' or row.get('group')=='protected':
            word=row.get('word');expected=row.get('expectedSpelling',row.get('typed'))
            if (not isinstance(word,str) or row.get('group')!='protected' or row.get('cohort') not in ('correct','protected')
                    or row.get('noAuto') is not True or expected!='@'+word or row.get('typed')!=expected):
                raise ValueError('QUARANTINE_PROTECTED_CONSTRUCTION')
            continue
        target=row.get('expectedSpelling')
        if target is None and row.get('cohort')=='correct':target=row.get('typed')
        if not isinstance(target,str) or not target:raise ValueError('QUARANTINE_TARGET')
        if lexicon.analyses(target):continue
        key=unsupported_surface_key(target)
        if key is None:raise ValueError('QUARANTINE_NONLEXICAL')
        methods=sorted(set(predict_methods(target)))
        if methods and set(methods)=={'DictionaryAnalyzer'}:raise ValueError('QUARANTINE_DICTIONARY_DISAGREEMENT')
        status='PREDICTION_ONLY' if methods else 'NO_ANALYSIS'
        keys.add(key);counts[status]+=1;details.append(dict(id=row['id'],surfaceKey=key,status=status,predictiveMethods=methods))
    return sorted(keys),details,dict(counts)


def build(root,base,lexicon,predict_methods):
    root=Path(root);result=copy.deepcopy(validate_ledger(base))
    if any('unsupportedSurfaceKeys' in e for e in result['entries']):raise ValueError('QUARANTINE_ALREADY_REGISTERED')
    counts={};bindings={}
    for entry in result['entries']:
        if entry['id'] in {'public-early-ru-'+c for c in ('qualification-v2','compact-v3','compact-v4')}:
            paths=[p for p in entry['bindings'] if p.endswith('/spelling-ru.jsonl')]
            if len(paths)!=1:raise ValueError('QUARANTINE_SOURCE_BINDING')
            path=paths[0]
        else:path=source_path(entry)
        if path is None:continue
        if sha(root/path)!=entry['bindings'][path]:raise ValueError('QUARANTINE_CORPUS_IDENTITY')
        rows=[json.loads(line) for line in (root/path).read_text().splitlines()]
        if len(rows)!=entry['rowCount']:raise ValueError('QUARANTINE_ROW_COUNT')
        keys,details,statuses=classify(rows,lexicon,predict_methods)
        if keys:entry['unsupportedSurfaceKeys']=keys
        counts[entry['id']]=dict(rows=len(rows),unsupportedRows=len(details),distinctSurfaces=len(keys),statuses=statuses,details=details)
        bindings[path]=entry['bindings'][path]
    receipt=dict(purpose='PUBLIC_UNSUPPORTED_TARGET_QUARANTINE_NOT_LEMMA_RECOVERY',counts=counts,bindings=bindings,
        dictionary=lexicon.receipt(),modelCalls=0,predictiveLemmasImported=False,canonicalFamilyGapsCleared=False,
        unsupportedRows=sum(c['unsupportedRows'] for c in counts.values()),
        distinctSurfaces=len({k for e in result['entries'] for k in e.get('unsupportedSurfaceKeys',[])}),
        sourceBindings={p:sha(root/p) for p in ('tools/typing_experiments/quarantine_unknown_families.py',
          'tools/typing_experiments/source_identities.py','tools/morphology/ranker.py','tools/typing_experiments/audit_family_coverage.py')})
    return validate_ledger(result),receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():parser.error('output already exists')
    sys.path.insert(0,str(ROOT/'tools/morphology'));from ranker import PymorphyLexicon
    import pymorphy3
    lexicon=PymorphyLexicon(cache_size=16384);lexicon.receipt() # Validate pins before diagnostic predictor construction.
    predictor=pymorphy3.MorphAnalyzer()
    def methods(word):return {type(item[0]).__name__ for parsed in predictor.parse(word) for item in parsed.methods_stack}
    ledger,receipt=build(ROOT,load_ledger(args.base),lexicon,methods)
    args.output.mkdir(parents=True,exist_ok=False)
    for name,value in (('ledger.json',ledger),('receipt.json',receipt)):(args.output/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:receipt[k] for k in ('unsupportedRows','distinctSurfaces','predictiveLemmasImported','canonicalFamilyGapsCleared')}))


if __name__=='__main__':main()
