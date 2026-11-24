"""Quarantine public contexts exposed by the historical word-ranking replay."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/typing_experiments'),str(ROOT/'tools/ci')]
import control_ledger as control
import holdout_ledger as lexical
import historical_model_fixtures as fixtures

ENTRY='ci-wordrank-multiedit-replay-v1'
CONTROL=ROOT/'tools/typing_experiments/control-ledger.json'
LEXICAL=ROOT/'tools/typing_experiments/holdout-ledger.json'
FIXTURE=ROOT/'tools/typing_experiments/wordrank-replay-disclosure-v1/contexts.jsonl'
RECEIPT=ROOT/'docs/acceptance/2026-10-29-q5-multiedit-distance.json'
PROJECTION=ROOT/'docs/acceptance/2026-10-29-q5-multiedit-projection.json'
ARCHIVE='build/typing-word-ranking/data/test-rows.jsonl'


def sha(raw):return hashlib.sha256(raw).hexdigest()


def capture(rows, observations):
    values=set();seen=set()
    for row,obs in zip(rows,observations,strict=True):
        article=row.get('articleId');typed=row.get('typed');target=row.get('expectedSpelling');prefix=row.get('prefix')
        if (not isinstance(article,str) or not article.isascii() or not article.isdecimal() or
            not isinstance(typed,str) or not re.fullmatch('[а-яё]+',typed,re.I) or
            not isinstance(target,str) or not re.fullmatch('[а-яё]+',target,re.I) or
            not isinstance(prefix,str) or not isinstance(row.get('id'),str) or not row['id'] or
            row.get('language')!='ru' or row.get('partition')!='test' or row.get('id') in seen or row.get('id')!=obs.get('id') or
            obs.get('language')!='ru' or obs.get('status')!='COMPLETE' or obs.get('typed')!=typed or obs.get('prefix')!=prefix):
            raise ValueError('WORD_DISCLOSURE_IDENTITY')
        seen.add(row['id']);before=obs.get('beforeBoundary',{}).get('text');after=obs.get('afterBoundary',{}).get('text')
        if not isinstance(before,str) or not before.endswith(typed) or not isinstance(after,str):
            raise ValueError('WORD_DISCLOSURE_EDITOR')
        actual_prefix=before[:-len(typed)]
        if not after.startswith(actual_prefix) or not after.endswith(' '):raise ValueError('WORD_DISCLOSURE_BOUNDARY')
        actual=after[len(actual_prefix):-1]
        if not re.fullmatch('[а-яё]+',actual,re.I):raise ValueError('WORD_DISCLOSURE_OUTPUT')
        for context,token in ((prefix,typed),(prefix,target),(actual_prefix,typed),(actual_prefix,target),(actual_prefix,actual)):
            values.add((article,context.strip(),token))
    if not seen or not values:raise ValueError('WORD_DISCLOSURE_EMPTY')
    return [dict(language='ru',article=article,prefix=prefix,typed=token,expectedSpelling=token)
            for article,prefix,token in sorted(values)]


def payload(values):
    return ''.join(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for v in values).encode()


def bindings():
    paths=[Path(__file__).resolve(),FIXTURE,FIXTURE.with_name('NOTICE.md'),RECEIPT,PROJECTION]
    paths += [fixtures.DATA/name for name in ('manifest.json','files.tar.gz','articles.jsonl','NOTICE.md')]
    return {str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in paths}


def entries(values):
    bound=bindings()
    first=dict(id=ENTRY,kind='regression',language='ru',rowCount=len(values),bindings=bound,
        keys=sorted({control.key_for(r,'regression') for r in values}),
        surfaceKeys=sorted({control.surface_key('ru',r['typed']) for r in values}),
        articleKeys=sorted({control.article_key(r) for r in values}),
        semantics='Disclosed historical public word-ranking replay inputs, synthetic targets and observed outputs; not independent quality data.')
    second=dict(id=ENTRY+'-contexts',usage='historical-context-exclusion',rowCount=len(values),bindings=bound,
        keys={'context':sorted(lexical.keys_for(values,'context'))},missingAxes=[],
        notes='Previously disclosed public word-ranking test contexts and observed replay surfaces; no canonical family claim.')
    return first,second


def load_fixture():
    raw=FIXTURE.read_bytes();values=[json.loads(line) for line in raw.splitlines()]
    if not values or raw!=payload(values) or len({(v['article'],v['prefix'],v['typed']) for v in values})!=len(values):
        raise ValueError('WORD_DISCLOSURE_FIXTURE')
    if values!=sorted(values,key=lambda v:(v['article'],v['prefix'],v['typed'])):raise ValueError('WORD_DISCLOSURE_ORDER')
    return values


def check():
    a=control.load(CONTROL);b=lexical.load_ledger(LEXICAL);first,second=entries(load_fixture())
    if [e for e in a['entries'] if e['id']==ENTRY]!=[first] or [e for e in b['entries'] if e['id']==ENTRY+'-contexts']!=[second]:
        raise ValueError('WORD_DISCLOSURE_DRIFT')
    return len(load_fixture())


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true')
    p.add_argument('--capture',action='store_true');p.add_argument('--rows',type=Path);p.add_argument('--observations',type=Path)
    p.add_argument('--output',type=Path);a=p.parse_args()
    if a.check:
        if a.capture or a.output or a.rows or a.observations:raise ValueError('WORD_DISCLOSURE_ARGS')
        print(json.dumps({'contexts':check(),'independentQualification':False}));return
    if a.output is None:raise ValueError('WORD_DISCLOSURE_ARGS')
    output=a.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('WORD_DISCLOSURE_OUTPUT')
    if a.capture:
        if not a.rows or not a.observations:raise ValueError('WORD_DISCLOSURE_ARGS')
        raw=a.rows.read_bytes();observed=a.observations.read_bytes();receipt=json.loads(RECEIPT.read_text())
        _,archive=fixtures.verify()
        if (raw!=archive[ARCHIVE] or sha(raw)!=receipt['rowsSha256'] or
            sha(observed)!=receipt['observationsSha256']):raise ValueError('WORD_DISCLOSURE_BINDING')
        values=capture((json.loads(x) for x in raw.splitlines()),(json.loads(x) for x in observed.splitlines()))
        if a.rows.read_bytes()!=raw or a.observations.read_bytes()!=observed:raise ValueError('WORD_DISCLOSURE_INPUT_DRIFT')
        output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(payload(values))
        print(json.dumps({'contexts':len(values)}));return
    if a.rows or a.observations:raise ValueError('WORD_DISCLOSURE_ARGS')
    raw_a=CONTROL.read_bytes();raw_b=LEXICAL.read_bytes();bound=bindings();a=json.loads(raw_a);b=json.loads(raw_b)
    control.validate(a);logical=lexical.validate_ledger(copy.deepcopy(b));first,second=entries(load_fixture())
    if any(e['id']==ENTRY for e in a['entries']) or any(e['id']==ENTRY+'-contexts' for e in logical['entries']):raise ValueError('WORD_DISCLOSURE_EXISTS')
    a['entries'].append(first);b['entries'].append(second);control.validate(a);lexical.validate_ledger(copy.deepcopy(b))
    if CONTROL.read_bytes()!=raw_a or LEXICAL.read_bytes()!=raw_b or bindings()!=bound or first['bindings']!=bound:
        raise ValueError('WORD_DISCLOSURE_INPUT_DRIFT')
    output.mkdir(parents=True,mode=0o700)
    for name,value in (('control-ledger.json',a),('holdout-ledger.json',b)):
        (output/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'contexts':len(load_fixture()),'independentQualification':False}))


if __name__=='__main__':main()
