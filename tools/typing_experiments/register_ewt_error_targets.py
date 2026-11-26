"""Quarantine public-vocabulary target forms seen in the disclosed EWT experiment."""
import argparse
import copy
import json
from pathlib import Path

import english_ewt_error_model as model
import english_family_keys as family
import ewt_lemma_exclusions as parent
import holdout_ledger as lexical
import import_english_ewt_exposure as ewt

ROOT=Path(__file__).resolve().parents[2]
LEDGER=ROOT/'tools/typing_experiments/holdout-ledger.json'
FIXTURE=ROOT/'tools/typing_experiments/english-ewt-error-model-v1.json'
FIXTURE_SHA='42dbf472f8a9109413b8cf8ba3a21459436ffcfa8739bf7accc2f17d611482c7'
ENTRY='public-ewt-annotated-correction-vocabulary-exclusion-v1'


def receipt(raw):
    if model.sha(raw)!=FIXTURE_SHA:raise ValueError('EWT_TARGET_RECEIPT_DRIFT')
    value=json.loads(raw);keys=value.get('targetSurfaceKeys')
    if (value.get('scope')!='disclosed-ewt-annotation-experiment-not-qualification' or
            value.get('sourceLockSha256')!=model.LOCK_SHA or value.get('vocabularySha256')!=model.VOCAB_SHA or
            value.get('analyzerSha256')!=model.sha(Path(model.__file__).read_bytes()) or
            value.get('extractorSha256')!=model.sha(Path(ewt.__file__).read_bytes()) or
            value.get('familyKeySha256')!=model.sha(Path(family.__file__).read_bytes()) or
            value.get('results',{}).get('independentQualification') is not False or
            value.get('results',{}).get('sourceLabelsQualified') is not False or
            not isinstance(keys,list) or len(keys)!=425 or keys!=sorted(set(keys)) or
            any(not isinstance(key,str) or not parent.HASH.fullmatch(key) for key in keys)):
        raise ValueError('EWT_TARGET_RECEIPT_SCHEMA')
    if model.sha(model.VOCAB.read_bytes())!=model.VOCAB_SHA or model.sha(ewt.LOCK.read_bytes())!=model.LOCK_SHA:
        raise ValueError('EWT_TARGET_SOURCE_DRIFT')
    return value


def entry(ledger,raw):
    parent.parent(ledger);value=receipt(raw)
    paths=(Path(__file__).resolve(),Path(model.__file__).resolve(),Path(family.__file__).resolve(),
           Path(ewt.__file__).resolve(),Path(parent.__file__).resolve(),Path(lexical.__file__).resolve(),
           ROOT/'tools/typing_experiments/source_identities.py',ewt.LOCK,model.VOCAB,FIXTURE)
    bindings={str(path.relative_to(ROOT)):model.sha(path.read_bytes()) for path in paths}
    if bindings[str(FIXTURE.relative_to(ROOT))]!=model.sha(raw):raise ValueError('EWT_TARGET_INPUT_DRIFT')
    return dict(id=ENTRY,usage='historical-family-exclusion',keys={'family':value['targetSurfaceKeys']},missingAxes=[],
        bindings=bindings,rowCount=value['results']['trainSingleEditRows']+sum(value['sourceCounts'][p+':singleEdit'] for p in ('dev','test')),
        parentEntrySha256=parent.PARENT_SHA,
        notes='Exact public-vocabulary corrected forms exposed by EWT annotated-error experiment; no inflection or family completeness claim.')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');p.add_argument('--output',type=Path)
    args=p.parse_args()
    if args.check == (args.output is not None):raise ValueError('EWT_TARGET_SCOPE')
    raw=LEDGER.read_bytes();stored=json.loads(raw);expected=entry(stored,FIXTURE.read_bytes())
    if args.check:
        values=[e for e in lexical.validate_ledger(copy.deepcopy(stored))['entries'] if e['id']==ENTRY]
        if values!=[expected]:raise ValueError('EWT_TARGET_LEDGER_DRIFT')
    else:
        output=args.output.resolve()
        if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('EWT_TARGET_OUTPUT')
        if any(e['id']==ENTRY for e in stored['entries']):raise ValueError('EWT_TARGET_EXISTS')
        stored['entries'].append(expected);lexical.validate_ledger(copy.deepcopy(stored))
        if LEDGER.read_bytes()!=raw or entry(json.loads(raw),FIXTURE.read_bytes())!=expected:raise ValueError('EWT_TARGET_INPUT_DRIFT')
        with output.open('x',encoding='utf-8') as f:json.dump(stored,f,ensure_ascii=False,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps({'targets':len(expected['keys']['family']),'independentQualification':False}))


if __name__=='__main__':main()
