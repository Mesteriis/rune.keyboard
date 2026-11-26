"""Reproduce partial EWT lemma exclusions against a pinned public vocabulary.

Source text, document IDs and token-level observations are never emitted.
Exact annotated lemmas are not a complete English morphology or qualification.
"""
import argparse
import collections
import copy
import hashlib
import json
from pathlib import Path
import re

import english_family_keys as family
import holdout_ledger as lexical
import import_english_ewt_exposure as ewt

ROOT=Path(__file__).resolve().parents[2]
VOCAB=ROOT/'tools/ci/product-replay-v1/sources/en_50k.txt'
VOCAB_SHA='5351ff405b1126ef555791dd4d9798a48e3e9a501a9fc481a9da957752cfb458'
LOCK_SHA='380668545aa5b37008eea1708bd9da9375fb1825d3f1b5ee76a6a469accc4709'
PARENT='public-ud-english-ewt-2.18-exposure'
PARENT_SHA='9f822a736cbea64a2f856f15653dfe9c2dd89c091d253c16b038f21738475748'
ENTRY='public-ud-english-ewt-2.18-vocabulary-lemma-exclusion-v1'
LEDGER=ROOT/'tools/typing_experiments/holdout-ledger.json'
FIXTURE=ROOT/'tools/typing_experiments/ewt-lemma-exclusions-v1.json'
HASH=re.compile(r'[0-9a-f]{64}\Z')
POS=frozenset('ADJ ADP ADV AUX CCONJ DET INTJ NOUN NUM PART PRON PROPN PUNCT SCONJ SYM VERB X'.split())


def sha(data):return hashlib.sha256(data).hexdigest()


def parent(ledger):
    values=[e for e in lexical.validate_ledger(copy.deepcopy(ledger))['entries'] if e['id']==PARENT]
    if len(values)!=1 or sha(json.dumps(values[0],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())!=PARENT_SHA:
        raise ValueError('EWT_LEMMA_PARENT')
    return values[0]


def extract(data,lock,vocab,ledger):
    if sha(vocab)!=VOCAB_SHA or sha(lock)!=LOCK_SHA:raise ValueError('EWT_LEMMA_SOURCE_DRIFT')
    hashes=json.loads(lock)['files']
    rows=ewt.rows_from_sources(data,hashes)
    expected=parent(ledger)
    if len(rows)!=expected['rowCount'] or any(sorted(lexical.keys_for(rows,k))!=expected['keys'][k] for k in ('article','sentence')):
        raise ValueError('EWT_LEMMA_PARENT_COVERAGE')
    words=set()
    for line in vocab.decode('utf-8').splitlines():
        try:words.add(family.key_for(line.rsplit(' ',1)[0]))
        except ValueError:continue
    counts=collections.Counter(); unsupported=collections.Counter(); keys=set()
    for name in sorted(data):
        for line in data[name].decode('utf-8').splitlines():
            if not line or line.startswith('#'):continue
            fields=line.split('\t')
            if len(fields)!=10:raise ValueError('EWT_LEMMA_TOKEN_SCHEMA')
            token=fields[0]
            if re.fullmatch(r'[1-9][0-9]*',token) is None:
                if re.fullmatch(r'[1-9][0-9]*(?:-[1-9][0-9]*|\.[1-9][0-9]*)',token) is None:
                    raise ValueError('EWT_LEMMA_TOKEN_ID')
                counts['nonIntegerRows']+=1;continue
            if fields[3] not in POS:raise ValueError('EWT_LEMMA_TOKEN_SCHEMA')
            counts['integerTokenRows']+=1
            try:key=family.key_for(fields[2])
            except ValueError:
                counts['unsupportedShapeRows']+=1;unsupported[fields[3]]+=1;continue
            counts['recognizedRows']+=1
            if key in words:counts['matchedVocabularyRows']+=1;keys.add(key)
            else:counts['outsideVocabularyRows']+=1
    return dict(schema='ewt-public-vocabulary-lemmas-v1',sourceLockSha256=sha(lock),vocabularySha256=sha(vocab),
        parentEntrySha256=PARENT_SHA,counts=dict(sorted(counts.items())),unsupportedByPos=dict(sorted(unsupported.items())),
        keys=sorted(keys),independentQualification=False,familyCoverageComplete=False)


def fixture(raw):
    value=json.loads(raw)
    if (value.get('schema')!='ewt-public-vocabulary-lemmas-v1' or value.get('sourceLockSha256')!=LOCK_SHA
        or value.get('vocabularySha256')!=VOCAB_SHA or value.get('parentEntrySha256')!=PARENT_SHA
        or value.get('independentQualification') is not False or value.get('familyCoverageComplete') is not False
        or not isinstance(value.get('keys'),list) or len(value['keys'])!=10485
        or sorted(set(value['keys']))!=value['keys'] or any(not isinstance(k,str) or not HASH.fullmatch(k) for k in value['keys'])
        or value.get('counts')!={'integerTokenRows':254820,'matchedVocabularyRows':212277,'nonIntegerRows':3370,
             'outsideVocabularyRows':4587,'recognizedRows':216864,'unsupportedShapeRows':37956}
        or sum(value.get('unsupportedByPos',{}).values())!=37956):
        raise ValueError('EWT_LEMMA_FIXTURE')
    return value


def entry(ledger,raw):
    parent(ledger);value=fixture(raw)
    paths=(Path(__file__).resolve(),Path(family.__file__).resolve(),Path(lexical.__file__).resolve(),
           Path(ewt.__file__).resolve(),ROOT/'tools/typing_experiments/source_identities.py',ewt.LOCK,VOCAB,FIXTURE)
    bindings={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in paths}
    if bindings[str(FIXTURE.relative_to(ROOT))]!=sha(raw):raise ValueError('EWT_LEMMA_FIXTURE_DRIFT')
    return dict(id=ENTRY,usage='historical-family-exclusion',keys={'family':value['keys']},missingAxes=[],
        bindings=bindings,rowCount=value['counts']['matchedVocabularyRows'],parentEntrySha256=PARENT_SHA,
        notes='Partial exact annotated EWT lemma exclusions intersected with pinned public vocabulary; not full families or independent qualification.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-directory',type=Path);p.add_argument('--generate',type=Path)
    p.add_argument('--register',type=Path);p.add_argument('--check',action='store_true')
    args=p.parse_args()
    if sum((args.generate is not None,args.register is not None,args.check))!=1:raise ValueError('EWT_LEMMA_SCOPE')
    ledger_raw=LEDGER.read_bytes();ledger=json.loads(ledger_raw)
    if args.generate:
        if args.source_directory is None:raise ValueError('EWT_LEMMA_SCOPE')
        lock=ewt.LOCK.read_bytes();hashes=json.loads(lock)['files']
        result=extract({name:(args.source_directory/name).read_bytes() for name in hashes},lock,VOCAB.read_bytes(),ledger)
        raw=(json.dumps(result,sort_keys=True,indent=2)+'\n').encode()
        if LEDGER.read_bytes()!=ledger_raw:raise ValueError('EWT_LEMMA_INPUT_DRIFT')
        with args.generate.open('xb') as f:f.write(raw)
        print(json.dumps({'keys':len(result['keys']),'counts':result['counts']}));return
    if args.source_directory:raise ValueError('EWT_LEMMA_SCOPE')
    expected=entry(ledger,FIXTURE.read_bytes())
    if args.check:
        found=[e for e in lexical.validate_ledger(ledger)['entries'] if e['id']==ENTRY]
        if found!=[expected]:raise ValueError('EWT_LEMMA_LEDGER_DRIFT')
        print(json.dumps({'keys':len(expected['keys']['family']),'independentQualification':False}));return
    output=args.register.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('EWT_LEMMA_OUTPUT')
    if any(e['id']==ENTRY for e in ledger['entries']):raise ValueError('EWT_LEMMA_EXISTS')
    one={key:copy.deepcopy(value) for key,value in ledger.items() if key!='entries'}
    one['entries']=[expected]
    # Preserve existing stored entries and compact only the new list.
    ledger['entries'].append(lexical.pack_ledger(one)['entries'][0]);lexical.validate_ledger(copy.deepcopy(ledger))
    if LEDGER.read_bytes()!=ledger_raw or entry(json.loads(ledger_raw),FIXTURE.read_bytes())!=expected:raise ValueError('EWT_LEMMA_INPUT_DRIFT')
    with output.open('x',encoding='utf-8') as f:json.dump(ledger,f,ensure_ascii=False,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps({'keys':len(expected['keys']['family']),'independentQualification':False}))


if __name__=='__main__':main()
