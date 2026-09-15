#!/usr/bin/env python3
"""Synthetic spelling recovery from held-out authored text; not human typo labels."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from telegram_style import StyleModel, _normalized, _segments, _json_bytes, _sha, _validate_output

WORD = re.compile(r'[а-яё]{5,12}\Z')
NAME_TAGS = {'Name','Surn','Patr','Geox','Orgn','Trad'}


def require(condition,code):
    if not condition:raise ValueError(code)


def read_bytes(path):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 64*1024*1024,'DATASET_FILE')
    data=path.read_bytes()
    require(len(data)<=64*1024*1024,'DATASET_FILE')
    return data


def texts(data):
    rows=[]
    for line in data.decode('utf-8').splitlines():
        if not line.strip():continue
        row=json.loads(line)
        require(isinstance(row,dict) and set(row)=={'text'} and isinstance(row['text'],str)
                and 0<len(row['text'])<=16384,'DATASET_ROW')
        rows.append(row['text'])
    require(0<len(rows)<=250000,'DATASET_ROWS')
    return rows


def verify_dataset(directory):
    receipt=json.loads(read_bytes(directory/'receipt.json'))
    require(isinstance(receipt,dict) and receipt.get('schemaVersion')==1
            and receipt.get('validationEligible') is True,'VALIDATION_REQUIRED')
    training_groups=receipt.get('trainChatHashes');validation_groups=receipt.get('validationChatHashes')
    require(isinstance(training_groups,list) and isinstance(validation_groups,list)
            and training_groups and validation_groups
            and all(isinstance(v,str) for v in training_groups+validation_groups)
            and not set(training_groups).intersection(validation_groups),'CHAT_SPLIT_OVERLAP')
    bound=receipt.get('artifactSha256');require(isinstance(bound,dict),'DATASET_BINDINGS')
    data={name:read_bytes(directory/name) for name in ('train.jsonl','validation.jsonl','model.json')}
    require(all(bound.get(name)==_sha(value) for name,value in data.items()),'DATASET_CHANGED')
    train=texts(data['train.jsonl']);validation=texts(data['validation.jsonl'])
    require(not {_normalized(t) for t in train}.intersection(_normalized(t) for t in validation),'TEXT_SPLIT_OVERLAP')
    model=json.loads(data['model.json']);StyleModel(model)
    normalized=sorted(set('\n'.join(_normalized(line) for line in t.splitlines()).strip() for t in train))
    hashes=sorted(_sha(t.encode()) for t in normalized)
    require(hashes==model['messageHashes'] and _sha(_json_bytes(normalized))==model['trainingSha256']
            and receipt.get('trainingSha256')==model['trainingSha256'],'TRAINING_IDENTITY')
    return validation,{name:_sha(value) for name,value in data.items()}


def corrupt(word,lexicon):
    variants={word[:i]+word[i+1]+word[i]+word[i+2:] for i in range(len(word)-1) if word[i]!=word[i+1]}
    variants.update(word[:i]+word[i+1:] for i in range(len(word)))
    for candidate in sorted(variants,key=lambda w:hashlib.sha256(w.encode()).digest()):
        if candidate!=word and not lexicon.analyses(candidate):return candidate
    return None


def synthetic_rows(messages,lexicon,limit):
    require(type(limit) is int and 1<=limit<=2000,'TARGET_LIMIT')
    choices={}
    for text in messages:
        require(isinstance(text,str) and len(text)<=16384,'MESSAGE_TYPE')
        for segment in _segments(text):
            words=segment.split()
            for i,word in enumerate(words):
                # Restrict references to observed lowercase dictionary forms; names and guesses are excluded.
                if not WORD.fullmatch(word):continue
                analyses=lexicon.analyses(word)
                if not analyses or any(a.grammemes.intersection(NAME_TAGS) for a in analyses):continue
                prefix=' '.join(words[max(0,i-3):i])
                if len(prefix)>256:continue
                previous=choices.get(word)
                if previous is None or _sha(prefix.encode())<_sha(previous.encode()):choices[word]=prefix
    rows=[]
    for word in sorted(choices,key=lambda w:_sha(w.encode())):
        typo=corrupt(word,lexicon)
        if typo is None:continue
        index=len(rows)//2
        common=dict(prefix=choices[word],split='holdout',language='ru',noAuto=False)
        rows.append(dict(common,id=f'personal-{index:04d}-correct',typed=word,cohort='correct'))
        rows.append(dict(common,id=f'personal-{index:04d}-typo',typed=typo,cohort='typo',expectedSpelling=word))
        if index+1==limit:break
    return rows


def prepare(dataset_dir:Path,output:Path,limit:int=400,*,lexicon=None):
    directory=dataset_dir.resolve(strict=True)
    destination=_validate_output(output)
    helper_paths=[Path(__file__).resolve(),Path(__file__).with_name('telegram_style.py'),Path(__file__).with_name('ranker.py')]
    source_hashes={p.name:_sha(p.read_bytes()) for p in helper_paths}
    validation,bound=verify_dataset(directory)
    if lexicon is None:
        from ranker import PymorphyLexicon
        lexicon=PymorphyLexicon()
    rows=synthetic_rows(validation,lexicon,limit)
    require(rows,'NO_SYNTHETIC_TARGETS')
    report=dict(schemaVersion=1,scope='personal-heldout-synthetic-recovery',rows=len(rows),distinctTargets=len(rows)//2,
        syntheticRecoveryNotHumanTypoAccuracy=True,naturalTyposNotGold=True,
        syntheticMechanism='one-character-deletion-or-adjacent-transposition; unknown-corruption; deterministic-sha256-order',
        thresholdsFitted=False,sourceArtifacts=bound,datasetReceiptSha256=_sha(read_bytes(directory/'receipt.json')),
        generatorSha256=source_hashes['personal_holdout.py'],sourceBindings=source_hashes,dictionary=lexicon.receipt() if hasattr(lexicon,'receipt') else None)
    # Recheck source bytes before writing results; no private text appears in the report.
    require(verify_dataset(directory)[1]==bound,'DATASET_CHANGED_DURING_PREPARATION')
    require({p.name:_sha(p.read_bytes()) for p in helper_paths}==source_hashes,'SOURCE_CHANGED_DURING_PREPARATION')
    destination.mkdir(parents=True,mode=0o700)
    encoded=b''.join(_json_bytes(row) for row in rows)
    report['rowsSha256']=_sha(encoded)
    for name,data in (('rows.jsonl',encoded),('receipt.json',_json_bytes(report))):
        descriptor=os.open(destination/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(descriptor,'wb') as stream:stream.write(data)
    return {k:report[k] for k in ('scope','rows','distinctTargets','syntheticRecoveryNotHumanTypoAccuracy')}


def main():
    os.umask(0o077)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--limit',type=int,default=400)
    args=parser.parse_args()
    try:print(json.dumps(prepare(args.dataset_dir,args.output,args.limit)))
    except (ValueError,OSError,TypeError,KeyError):
        print('PERSONAL_HOLDOUT_FAILED',file=sys.stderr);return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
