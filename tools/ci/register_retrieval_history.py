"""Register a hash-verified public historical retrieval corpus without build/."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/typing_experiments'))
import control_ledger as control
import holdout_ledger as lexical

FIXTURE=ROOT/'tools/typing_experiments/retrieval-history-v1'
CONTROL=ROOT/'tools/typing_experiments/control-ledger.json'
LEXICAL=ROOT/'tools/typing_experiments/holdout-ledger.json'
ENTRY='historical-retrieval-public-v1'
ROWS_SHA='cdc09d6b5885e0d6a01757c05b814d7efe97f7aaefb8932287dbaa673811098c'
HASH=re.compile('[0-9a-f]{64}\\Z')


def sha(raw):return hashlib.sha256(raw).hexdigest()


def inputs():
    files={name:(FIXTURE/name).read_bytes() for name in ('rows.jsonl','articles.jsonl','source-keys.json','receipt.json','source-lock.json','NOTICE.md')}
    receipt=json.loads(files['receipt.json']);keys=json.loads(files['source-keys.json']);lock=json.loads(files['source-lock.json'])
    rows=[json.loads(line) for line in files['rows.jsonl'].splitlines()];articles=[json.loads(line) for line in files['articles.jsonl'].splitlines()]
    if (receipt.get('scope')!='disclosed-historical-retrieval-not-qualification' or receipt.get('independentQualification') is not False or
        sha(files['rows.jsonl'])!=ROWS_SHA or receipt.get('rowsSha256')!=ROWS_SHA or receipt.get('articlesSha256')!=sha(files['articles.jsonl']) or
        receipt.get('keysSha256')!=sha(files['source-keys.json']) or receipt.get('sourceLockSha256')!=sha(files['source-lock.json']) or
        receipt.get('sourceSha256')!=lock['wikipediaContext']['files']['ru-0007.parquet']['sha256'] or
        receipt.get('counts',{}).get('rows')!=1800 or len(rows)!=1800 or len(articles)!=341 or receipt.get('sourceArticles')!=341 or
        receipt.get('dictionary',{}).get('dictionaryOnly') is not True):raise ValueError('RETRIEVAL_FIXTURE_IDENTITY')
    expected_axes={'articleKeys','sentenceKeys','contextKeys','familyKeys','unsupportedSurfaceKeys','controlKeys','surfaceKeys','controlArticleKeys'}
    if not isinstance(keys,dict) or set(keys)!=expected_axes:raise ValueError('RETRIEVAL_FIXTURE_KEYS')
    for axis,values in keys.items():
        if (not isinstance(values,list) or values!=sorted(set(values)) or
            any(not isinstance(x,str) or not HASH.fullmatch(x) for x in values) or (not values and axis!='unsupportedSurfaceKeys')):
            raise ValueError('RETRIEVAL_FIXTURE_KEYS')
    if len({r.get('id') for r in rows})!=len(rows):raise ValueError('RETRIEVAL_FIXTURE_ROWS')
    proposals=[r|{'article':r.get('articleId')} for r in rows]
    if (set(keys['articleKeys'])!=lexical.keys_for(proposals,'article') or set(keys['contextKeys'])!=lexical.keys_for(proposals,'context') or
        set(keys['controlArticleKeys'])!={control.article_key(r) for r in proposals} or
        set(keys['controlKeys'])!={control.key_for(r|{'typed':t},'regression') for r in proposals for t in (r['typed'],r['expectedSpelling'])} or
        set(keys['surfaceKeys'])!={control.surface_key('ru',t) for r in proposals for t in (r['typed'],r['expectedSpelling'])}):
        raise ValueError('RETRIEVAL_FIXTURE_PROJECTION')
    article_ids={r['articleId'] for r in rows}
    if (len(article_ids)!=len(articles) or {a.get('articleId') for a in articles}!=article_ids or
        any(not isinstance(a.get('title'),str) or not a['title'] or a.get('historyUrl')!=
            'https://ru.wikipedia.org/w/index.php?curid='+a['articleId']+'&action=history' for a in articles)):
        raise ValueError('RETRIEVAL_FIXTURE_ATTRIBUTION')
    paths=[Path(__file__).resolve(),*[FIXTURE/name for name in files]]
    for name,digest in receipt.get('helperSha256',{}).items():
        if not isinstance(name,str) or not isinstance(digest,str) or not HASH.fullmatch(digest):raise ValueError('RETRIEVAL_FIXTURE_HELPERS')
        path=FIXTURE/'sources'/(digest+'.txt')
        if sha(path.read_bytes())!=digest:raise ValueError('RETRIEVAL_FIXTURE_HELPERS')
        paths.append(path)
    if len(receipt.get('helperSha256',{}))!=10:raise ValueError('RETRIEVAL_FIXTURE_HELPERS')
    return rows,keys,{str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in paths}


def entries():
    rows,k,b=inputs()
    source=dict(id=ENTRY+'-source',usage='historical-source-exclusion',rowCount=len(rows),bindings=b,
        keys={'article':k['articleKeys'],'sentence':k['sentenceKeys']},missingAxes=[],
        notes='Public source articles, bounded target windows and selector segments; not verified linguistic sentences.')
    contexts=dict(id=ENTRY+'-contexts',usage='historical-context-exclusion',rowCount=len(rows),bindings=b,
        keys={'context':k['contextKeys']},missingAxes=[],parentEntries=[source['id']],
        notes='Disclosed historical retrieval target contexts; not independent qualification.')
    family=dict(id=ENTRY+'-families',usage='prepared-training-quarantine',rowCount=len(rows),bindings=b,
        keys={'family':k['familyKeys']},missingAxes=[],parentEntries=[source['id'],contexts['id']],
        notes='All dictionary-only analyses of original targets; no inference for unsupported words.')
    if k['unsupportedSurfaceKeys']:family['unsupportedSurfaceKeys']=k['unsupportedSurfaceKeys']
    controls=dict(id=ENTRY,kind='regression',language='ru',rowCount=len(rows)*2,bindings=b,
        keys=k['controlKeys'],surfaceKeys=k['surfaceKeys'],articleKeys=k['controlArticleKeys'],
        semantics='Disclosed historical retrieval typed and target surfaces and source articles; no quality or freshness claim.')
    return controls,[source,contexts,family]


def check():
    first,added=entries();a=control.load(CONTROL);b=lexical.load_ledger(LEXICAL)
    if [e for e in a['entries'] if e['id']==ENTRY]!=[first]:raise ValueError('RETRIEVAL_REGISTRY_DRIFT')
    for expected in added:
        if [e for e in b['entries'] if e['id']==expected['id']]!=[expected]:raise ValueError('RETRIEVAL_REGISTRY_DRIFT')
    return len(inputs()[0])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args()
    if a.check:
        if a.output:raise ValueError('RETRIEVAL_REGISTRY_SCOPE')
        print(json.dumps({'rows':check(),'independentQualification':False}));return
    if a.output is None:raise ValueError('RETRIEVAL_REGISTRY_SCOPE')
    output=a.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('RETRIEVAL_REGISTRY_OUTPUT')
    old_a=CONTROL.read_bytes();old_b=LEXICAL.read_bytes();first,added=entries();bound=first['bindings']
    controls=json.loads(old_a);stored=json.loads(old_b);control.validate(controls);logical=lexical.validate_ledger(copy.deepcopy(stored))
    if any(e['id']==ENTRY for e in controls['entries']) or any(e['id'] in {x['id'] for x in added} for e in logical['entries']):raise ValueError('RETRIEVAL_REGISTRY_EXISTS')
    controls['entries'].append(first);stored['entries'].extend(added);control.validate(controls);lexical.validate_ledger(copy.deepcopy(stored))
    if CONTROL.read_bytes()!=old_a or LEXICAL.read_bytes()!=old_b or inputs()[2]!=bound:raise ValueError('RETRIEVAL_REGISTRY_DRIFT')
    output.mkdir(parents=True,mode=0o700)
    for name,value in (('control-ledger.json',controls),('holdout-ledger.json',stored)):
        (output/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'rows':1800,'independentQualification':False}))


if __name__=='__main__':main()
