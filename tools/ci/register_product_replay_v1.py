#!/usr/bin/env python3
"""Bind permanent regression disclosures to both existing public exclusion registries."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

from generate_product_replay_v1 import ROOT, DATA, build
sys.path.insert(0,str(ROOT/'tools/typing_experiments'))
import control_ledger as controls
import holdout_ledger as lexical
from source_identities import unsupported_surface_key

CONTROL_PATH = ROOT/'tools/typing_experiments/control-ledger.json'
LEXICAL_PATH = ROOT/'tools/typing_experiments/holdout-ledger.json'
ENTRY = 'ci-product-replay-v1'


def expected_entries():
    for name, data in build().items():
        if (DATA/name).read_bytes()!=data:raise ValueError('REGRESSION_INPUT_DRIFT:'+name)
    rows=[json.loads(line) for line in (DATA/'inputs.jsonl').read_text().splitlines()]
    origins=[json.loads(line) for line in (DATA/'origins.jsonl').read_text().splitlines()]
    paths=[DATA/name for name in ('inputs.jsonl','origins.jsonl','manifest.json','source-lock.json','NOTICE.md')]
    bindings={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    generator=ROOT/'tools/ci/generate_product_replay_v1.py'
    bindings[str(generator.relative_to(ROOT))]=hashlib.sha256(generator.read_bytes()).hexdigest()
    result=[]
    for language in controls.LANGUAGES:
        selected=[row for row in rows if row['language']==language]
        surfaces={row['typed'] for row in selected}
        surfaces.update(word['word'] for origin in origins if origin['language']==language
                        for word in [origin['target'],*origin['context']])
        result.append(dict(id=ENTRY+'-'+language,kind='regression',language=language,rowCount=len(selected),
            bindings=bindings,keys=sorted({controls.key_for(row,'regression') for row in selected}),
            surfaceKeys=sorted({controls.surface_key(language,word) for word in surfaces}),
            semantics='Disclosed regression inputs; no correctness, protected-word or lemma labels.'))
    ru=[dict(row,expectedSpelling=row['typed']) for row in rows if row['language']=='ru']
    surfaces={row['typed'] for row in ru}
    surfaces.update(word['word'] for origin in origins if origin['language']=='ru' for word in [origin['target'],*origin['context']])
    entry=dict(id=ENTRY+'-ru-contexts',usage='historical-exclusion',bindings=bindings,
        keys={'context':sorted(lexical.keys_for(ru,'context'))},missingAxes=['article','sentence','family'],
        unsupportedSurfaceKeys=sorted({key for word in surfaces if (key:=unsupported_surface_key(word)) is not None}),
        semantics='Exact public surfaces and contexts only; no canonical family or natural sentence claimed.')
    return result,entry


def updated(control,lex):
    result=copy.deepcopy(controls.validate(control));other=copy.deepcopy(lexical.validate_ledger(lex))
    entries,entry=expected_entries()
    if any(e['id'].startswith(ENTRY) for e in result['entries']+other['entries']):raise ValueError('REGRESSION_ALREADY_REGISTERED')
    result['entries'].extend(entries);other['entries'].append(entry)
    other['coverage']['pending'].append('Q7 v1 regression words have durable surface/context exclusions; canonical RU family closure is still unproven.')
    return controls.validate(result),lexical.validate_ledger(other)


def check():
    control=controls.load(CONTROL_PATH);lex=lexical.load_ledger(LEXICAL_PATH)
    entries,entry=expected_entries()
    actual=[e for e in control['entries'] if e['id'].startswith(ENTRY)]
    if actual!=entries or [e for e in lex['entries'] if e['id'].startswith(ENTRY)]!=[entry]:raise ValueError('REGRESSION_EXCLUSION_DRIFT')
    if control['coverageComplete'] or lex['coverage']['complete']:raise ValueError('REGRESSION_NOT_GLOBAL_COVERAGE')
    print('Q7 disclosures bound: three language surface/context entries and RU context quarantine')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true');parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.check==(args.output is not None):parser.error('choose --check or a fresh --output')
    if args.check:check();return
    control,lex=updated(controls.load(CONTROL_PATH),lexical.load_ledger(LEXICAL_PATH))
    args.output.mkdir(parents=True,exist_ok=False)
    for name,data in [('control-ledger.json',control),('holdout-ledger.json',lex)]:
        (args.output/name).write_text(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2)+'\n')


if __name__=='__main__':main()
