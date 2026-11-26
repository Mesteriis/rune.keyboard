"""Register new public outputs of a disclosed packed-lexicon experiment."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/typing_experiments'))
import control_ledger as control
import holdout_ledger as lexical

ENTRY='ci-wordrank-packed-output-v1'
FIXTURE=ROOT/'tools/typing_experiments/wordrank-packed-disclosure-v1/contexts.jsonl'
RECEIPT=ROOT/'docs/acceptance/2026-10-29-q5-packed-multiedit-comparison.json'
CONTROL=ROOT/'tools/typing_experiments/control-ledger.json'
LEXICAL=ROOT/'tools/typing_experiments/holdout-ledger.json'


def sha(data):return hashlib.sha256(data).hexdigest()


def inputs():
    raw=FIXTURE.read_bytes();receipt=json.loads(RECEIPT.read_bytes());rows=[json.loads(x) for x in raw.splitlines()]
    canonical=''.join(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for v in rows).encode()
    if (not rows or raw!=canonical or receipt.get('scope')!='disclosed-historical-packed-candidate-comparison' or
        receipt.get('independentQualification') is not False or receipt.get('candidateQualificationValid') is not False or
        receipt.get('missingDisclosures')!=len(rows) or receipt.get('missingDisclosureSha256')!=sha(raw) or
        len({(r.get('article'),r.get('prefix'),r.get('typed')) for r in rows})!=len(rows) or
        any(r.get('language')!='ru' or r.get('typed')!=r.get('expectedSpelling') for r in rows)):
        raise ValueError('PACKED_DISCLOSURE_IDENTITY')
    paths=[Path(__file__).resolve(),FIXTURE,FIXTURE.with_name('NOTICE.md'),RECEIPT,
           ROOT/'tools/typing_experiments/compare_packed_wordrank.py',ROOT/'tools/ci/historical-model-fixtures-v1/manifest.json']
    return rows,{str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in paths}


def entries():
    rows,bindings=inputs()
    first=dict(id=ENTRY,kind='regression',language='ru',rowCount=len(rows),bindings=bindings,
        keys=sorted({control.key_for(r,'regression') for r in rows}),
        surfaceKeys=sorted({control.surface_key('ru',r['typed']) for r in rows}),
        articleKeys=sorted({control.article_key(r) for r in rows}),
        semantics='Additional outputs observed in a disclosed packed-lexicon experiment; not independent quality data.')
    second=dict(id=ENTRY+'-contexts',usage='historical-context-exclusion',rowCount=len(rows),bindings=bindings,
        keys={'context':sorted(lexical.keys_for(rows,'context'))},missingAxes=[],
        notes='Additional disclosed public packed-experiment output contexts; no canonical family claim.')
    return first,second


def check():
    a=control.load(CONTROL);b=lexical.load_ledger(LEXICAL);first,second=entries()
    if [e for e in a['entries'] if e['id']==ENTRY]!=[first] or [e for e in b['entries'] if e['id']==ENTRY+'-contexts']!=[second]:
        raise ValueError('PACKED_DISCLOSURE_DRIFT')
    return len(inputs()[0])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args()
    if a.check:
        if a.output:raise ValueError('PACKED_DISCLOSURE_SCOPE')
        print(json.dumps({'contexts':check(),'independentQualification':False}));return
    if a.output is None:raise ValueError('PACKED_DISCLOSURE_SCOPE')
    output=a.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('PACKED_DISCLOSURE_OUTPUT')
    raw_a=CONTROL.read_bytes();raw_b=LEXICAL.read_bytes();first,second=entries();bound=first['bindings']
    controls=json.loads(raw_a);stored=json.loads(raw_b);control.validate(controls);logical=lexical.validate_ledger(copy.deepcopy(stored))
    if any(e['id']==ENTRY for e in controls['entries']) or any(e['id']==ENTRY+'-contexts' for e in logical['entries']):raise ValueError('PACKED_DISCLOSURE_EXISTS')
    controls['entries'].append(first);stored['entries'].append(second);control.validate(controls);lexical.validate_ledger(copy.deepcopy(stored))
    if CONTROL.read_bytes()!=raw_a or LEXICAL.read_bytes()!=raw_b or inputs()[1]!=bound:raise ValueError('PACKED_DISCLOSURE_DRIFT')
    output.mkdir(parents=True,mode=0o700)
    for name,value in (('control-ledger.json',controls),('holdout-ledger.json',stored)):
        (output/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'contexts':len(inputs()[0]),'independentQualification':False}))


if __name__=='__main__':main()
