#!/usr/bin/env python3
"""Durable disclosure of the already-versioned original multilingual spelling regression."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/typing_experiments'))
import control_ledger as controls
import holdout_ledger as lexical
from source_identities import unsupported_surface_key

CORPUS=ROOT/'tools/eval/smart-typing-0.3'
FILES=('spelling-en.jsonl','spelling-ru.jsonl','spelling-es.jsonl','protected-tokens.jsonl')
ENTRY='ci-original-spelling-v2'
CONTROL_PATH=ROOT/'tools/typing_experiments/control-ledger.json'
LEXICAL_PATH=ROOT/'tools/typing_experiments/holdout-ledger.json'


def expected_entries():
    manifest=json.loads((CORPUS/'manifest.json').read_text())
    paths=[CORPUS/'manifest.json',*[CORPUS/name for name in FILES]]
    bindings={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    rows=[]
    for name in FILES:
        path=CORPUS/name
        if bindings[str(path.relative_to(ROOT))]!=manifest['files'][name]:raise ValueError('ORIGINAL_REPLAY_INPUT_DRIFT')
        rows.extend(json.loads(line) for line in path.read_text().splitlines())
    if len(rows)!=12000 or len({r['id'] for r in rows})!=12000:raise ValueError('ORIGINAL_REPLAY_SCOPE')
    entries=[];ru_surfaces=set()
    for language in controls.LANGUAGES:
        selected=[r for r in rows if r['language']==language]
        if len(selected)!=4000 or any(r['task']!='spelling' for r in selected):raise ValueError('ORIGINAL_REPLAY_LANGUAGE')
        surfaces={r['typed'] for r in selected}
        surfaces.update(token for r in selected for token in r['prefix'].split())
        surfaces.update(value.strip() for r in selected for value in r.get('candidates',[]) if value.strip())
        entries.append(dict(id=ENTRY+'-'+language,kind='regression',language=language,rowCount=len(selected),
            bindings=bindings,keys=sorted({controls.key_for(r,'regression') for r in selected}),
            surfaceKeys=sorted({controls.surface_key(language,word) for word in surfaces}),
            semantics='Original already-disclosed authored regression; labels are not sent to the controller.'))
        if language=='ru':ru_surfaces=surfaces
    ru=[dict(r,expectedSpelling=r['typed']) for r in rows if r['language']=='ru']
    entry=dict(id=ENTRY+'-ru-contexts',usage='historical-exclusion',bindings=bindings,
        keys={'context':sorted(lexical.keys_for(ru,'context'))},missingAxes=['article','sentence','family'],
        unsupportedSurfaceKeys=sorted({k for word in ru_surfaces if (k:=unsupported_surface_key(word)) is not None}),
        semantics='Exact context/surface disclosure only; no new canonical family claim.')
    return entries,entry


def updated(control,lex):
    result=copy.deepcopy(controls.validate(control));other=copy.deepcopy(lexical.validate_ledger(lex))
    entries,entry=expected_entries()
    if any(e['id'].startswith(ENTRY) for e in result['entries']+other['entries']):raise ValueError('ORIGINAL_REPLAY_ALREADY_REGISTERED')
    result['entries'].extend(entries);other['entries'].append(entry)
    other['coverage']['pending'].append('Original multilingual spelling regression has surface/context exclusions; remaining canonical family provenance is unproven.')
    return controls.validate(result),lexical.validate_ledger(other)


def check():
    c=controls.load(CONTROL_PATH);l=lexical.load_ledger(LEXICAL_PATH);entries,entry=expected_entries()
    if [e for e in c['entries'] if e['id'].startswith(ENTRY)]!=entries or [e for e in l['entries'] if e['id'].startswith(ENTRY)]!=[entry]:
        raise ValueError('ORIGINAL_REPLAY_EXCLUSION_DRIFT')
    print('Original 12000 spelling rows have durable multilingual context/surface exclusions')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true');parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.check==(args.output is not None):parser.error('choose --check or fresh --output')
    if args.check:check();return
    c,l=updated(controls.load(CONTROL_PATH),lexical.load_ledger(LEXICAL_PATH))
    args.output.mkdir(parents=True,exist_ok=False)
    for name,data in [('control-ledger.json',c),('holdout-ledger.json',l)]:
        (args.output/name).write_text(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2)+'\n')


if __name__=='__main__':main()
