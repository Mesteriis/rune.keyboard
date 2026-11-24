#!/usr/bin/env python3
"""Deterministic public Russian chat-shaped regression corpus; never qualification."""
import argparse
import base64
import bz2
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from holdout_ledger import keys_for,load_ledger
from import_tatoeba_history import CC0_LOCK_SHA,sentence_hash
from recover_legacy_families import sha

ROOT=Path(__file__).resolve().parents[2]
URL='https://downloads.tatoeba.org/exports/per_language/rus/rus_sentences_CC0.tsv.bz2'
TOKEN=re.compile(r'[а-яё]+\Z')


def variants(word):
    """One deterministic candidate per orthographic operation, not prevalence."""
    result=[]
    for kind,letters in [('vowel_oa','оа'),('vowel_ei','еи')]:
        for index,char in enumerate(word):
            if char in letters:
                result.append((kind,word[:index]+letters[1-letters.index(char)]+word[index+1:]));break
    for source,target in [('ться','тся'),('тся','ться')]:
        if word.endswith(source):result.append(('reflexive_suffix',word[:-len(source)]+target));break
    for index,char in enumerate(word):
        if char in 'бвгджзйклмнпрстфхцчшщ':
            result.append(('double_consonant',word[:index]+char+word[index:]));break
    for index,char in enumerate(word):
        if char in 'ьъ' and len(word)>1:
            result.append(('remove_sign',word[:index]+word[index+1:]));break
    return result


def generate(lines,excluded_articles):
    rows=[];seen=set();counts=Counter();eligible=unregistered=0
    for line in lines:
        fields=line.rstrip('\n').split('\t')
        if len(fields)!=4 or fields[1]!='rus' or not fields[0].isascii() or not fields[0].isdecimal():raise ValueError('CHAT_SOURCE_ROW')
        identity=fields[0]
        if identity in seen:raise ValueError('CHAT_SOURCE_DUPLICATE')
        seen.add(identity)
        original=unicodedata.normalize('NFC',fields[2]);text=original.casefold().strip().rstrip('.!?').strip()
        words=text.split()
        if not 2<=len(words)<=6 or any(not TOKEN.fullmatch(w) for w in words):continue
        eligible+=1
        source=dict(article='tatoeba:'+identity,sourceRepository='tatoeba',language='ru',sentenceHash=sentence_hash(original))
        if keys_for([source],'article')-excluded_articles:
            unregistered+=1;continue
        prefix=' '.join(words[:-1]);word=words[-1]
        common=source|dict(prefix=prefix,split='holdout',clusterId='tatoeba:'+identity,register='chat-shaped-lowercase',
                           purpose='DISCLOSED_REGRESSION_NOT_QUALIFICATION')
        cases=[('control',word,'correct',True)]+[(kind,typed,'typo',False) for kind,typed in variants(word)]
        for kind,typed,cohort,no_auto in cases:
            rows.append(common|dict(id=f'chat-regression-{identity}-{kind}',typed=typed,expectedSpelling=word,
                                    cohort=cohort,noAuto=no_auto,edit_kind=kind))
            counts[kind]+=1
    if not rows:raise ValueError('CHAT_SOURCE_EMPTY')
    return rows,dict(eligibleSentences=eligible,unregisteredExcluded=unregistered,rows=len(rows),editCounts=dict(sorted(counts.items())))


def run(source,lock_path,ledger_path,output):
    source,lock_path,ledger_path,output=map(Path,(source,lock_path,ledger_path,output))
    if output.exists() or not output.resolve().is_relative_to(ROOT/'build'):raise ValueError('CHAT_OUTPUT')
    lock_raw=lock_path.read_bytes();ledger_raw=ledger_path.read_bytes()
    if hashlib.sha256(lock_raw).hexdigest()!=CC0_LOCK_SHA:raise ValueError('CHAT_LOCK_IDENTITY')
    lock=json.loads(lock_raw);source_digest=sha(source)
    if lock.get('url')!=URL or lock.get('license')!='CC0-1.0' or lock.get('compressedSha256')!=source_digest:raise ValueError('CHAT_SOURCE_IDENTITY')
    ledger=load_ledger(ledger_path)
    if ledger_path.read_bytes()!=ledger_raw:raise ValueError('CHAT_LEDGER_DRIFT')
    excluded={value for entry in ledger['entries'] for value in entry['keys'].get('article',[])}
    with bz2.open(source,'rt',encoding='utf-8') as stream:rows,counts=generate(stream,excluded)
    if sha(source)!=source_digest or lock_path.read_bytes()!=lock_raw or ledger_path.read_bytes()!=ledger_raw:raise ValueError('CHAT_INPUT_DRIFT')
    payload=''.join(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for row in rows).encode()
    def encoded(value):return base64.b64encode(value.encode()).decode()
    inputs=''.join('\t'.join((str(i),encoded(row['id']),'holdout','ru',encoded(row['prefix']),encoded(row['typed'])))+'\n'
                   for i,row in enumerate(rows)).encode()
    manifest=dict(schema=1,purpose='DISCLOSED_REGRESSION_NOT_QUALIFICATION',language='ru',sourceUrl=URL,license='CC0-1.0',
        sourceSha256=source_digest,sourceLockSha256=CC0_LOCK_SHA,ledgerSha256=hashlib.sha256(ledger_raw).hexdigest(),
        generatorSha256=sha(Path(__file__)),rowsSha256=hashlib.sha256(payload).hexdigest(),
        inputsSha256=hashlib.sha256(inputs).hexdigest(),counts=counts,
        editDistribution='one candidate per applicable operation, not measured typo frequency',
        labelsCaveat='Source controls are not independently proofread and may contain errors; synthetic edits can be real words. Neither proves user intent.',
        controlGroundTruth='unverified source spelling; cohort correct denotes unchanged source control only',
        sourceCaveat='Tatoeba has prior training and evaluation exposure; not independent holdout.',
        modelCalls=0,independentQualification=False)
    output.mkdir(parents=True);(output/'rows.jsonl').write_bytes(payload);(output/'inputs.tsv').write_bytes(inputs)
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source','lock','ledger','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();manifest=run(args.source,args.lock,args.ledger,args.output)
    print(json.dumps(manifest['counts'],ensure_ascii=False))

if __name__=='__main__':main()
