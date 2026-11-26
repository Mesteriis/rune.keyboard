#!/usr/bin/env python3
"""Register the already-screened A4 source shard in both exclusion ledgers."""
import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path

import quarantine_a4_frequency_source as source
import import_a4_review_exposure as reviewed

ROOT=Path(__file__).resolve().parents[2]
MANIFEST=reviewed.FOLDER/'wikipedia-0011-source-exclusion-manifest.json'
MANIFEST_SHA='02f99a89d4f5e164e87c5d84667b7f495aaa0bcfee95a1f080844261b09fe4b3'
CONTROL=reviewed.CONTROL; LEXICAL=reviewed.LEXICAL; ENTRY=source.ENTRY


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def manifest():
    if sha(MANIFEST)!=MANIFEST_SHA:raise ValueError('A4_SOURCE_FROZEN_MANIFEST')
    value=json.loads(MANIFEST.read_text()); lock=json.loads(source.source.LOCK.read_text())
    shards=[x for x in lock['shards'] if x['name']==source.source.SHARD]
    dependencies=(Path(reviewed.control.__file__).resolve(),Path(reviewed.lexical.__file__).resolve(),
                  ROOT/'tools/typing_experiments/source_identities.py',
                  ROOT/'tools/typing_experiments/conversation_split_checks.py')
    expected_dependencies={str(path.relative_to(ROOT)):sha(path) for path in dependencies}
    if (value.get('articles')!=92622 or value.get('sourceDecoderAttested') is not False or
            value.get('independentlyQualified') is not False or len(shards)!=1 or
            value.get('sourceSha256')!=shards[0]['sha256'] or
            value.get('sourceLockSha256')!=sha(source.source.LOCK) or
            value.get('helperSha256')!=sha(source.__file__) or
            value.get('frequencyHelperSha256')!=sha(source.source.__file__) or
            value.get('dependencySha256')!=expected_dependencies):
        raise ValueError('A4_SOURCE_MANIFEST_BINDING')
    return value


def entries(left,right):
    meta=manifest()
    for keys,name in ((left,'lexicalKeysSha256'),(right,'controlKeysSha256')):
        if len(keys)!=92622 or keys!=sorted(set(keys)) or source.digest(keys)!=meta[name]:
            raise ValueError('A4_SOURCE_KEYS')
    review_control,review_lexical=reviewed.entries()
    if (not set(review_control['articleKeys'])<=set(right) or
            not set(review_lexical['keys']['article'])<=set(left)):
        raise ValueError('A4_SOURCE_REVIEW_SUBSET')
    paths=(MANIFEST,Path(__file__).resolve(),Path(source.__file__).resolve(),
           Path(source.source.__file__).resolve(),source.source.LOCK,
           reviewed.SAMPLE,reviewed.REVIEW,Path(reviewed.__file__).resolve(),Path(reviewed.sample.__file__).resolve(),
           Path(reviewed.control.__file__).resolve(),Path(reviewed.lexical.__file__).resolve(),
           ROOT/'tools/typing_experiments/source_identities.py',
           ROOT/'tools/typing_experiments/conversation_split_checks.py')
    bindings={str(p.relative_to(ROOT)):sha(p) for p in paths}
    c=dict(id=ENTRY,kind='source',language='ru',rowCount=92622,keys=[],articleKeys=right,bindings=bindings,
           semantics='Entire public Wikipedia shard screened in aggregate; excluded from fresh controls.')
    l=dict(id=ENTRY,usage='historical-exclusion',rowCount=92622,keys={'article':left},
           missingAxes=['family','sentence','context'],bindings=bindings,
           notes='Entire public Wikipedia shard screened in aggregate; article-only quarantine, not complete coverage.')
    return c,l


def packed(keys):
    raw=b''.join(bytes.fromhex(k) for k in keys)
    return {'encoding':reviewed.lexical.PACKED_ENCODING,'count':len(keys),
            'sha256':hashlib.sha256(raw).hexdigest(),'data':base64.b64encode(raw).decode('ascii')}


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--check',action='store_true');g.add_argument('--keys',type=Path)
    p.add_argument('--output',type=Path);args=p.parse_args()
    c_raw,l_raw=CONTROL.read_bytes(),LEXICAL.read_bytes();controls,stored=json.loads(c_raw),json.loads(l_raw)
    reviewed.control.validate(controls);logical=reviewed.lexical.validate_ledger(copy.deepcopy(stored))
    ce=[e for e in controls['entries'] if e['id']==ENTRY];le=[e for e in logical['entries'] if e['id']==ENTRY]
    if args.check:
        if args.output or len(ce)!=1 or len(le)!=1:raise ValueError('A4_SOURCE_CHECK_SCOPE')
        first,second=entries(le[0]['keys']['article'],ce[0]['articleKeys'])
        if ce!=[first] or le!=[second]:raise ValueError('A4_SOURCE_LEDGER_DRIFT')
        print(json.dumps({'articles':92622,'independentlyQualified':False}));return
    if args.output is None or ce or le:raise ValueError('A4_SOURCE_IMPORT_SCOPE')
    out=args.output.resolve()
    if out.exists() or not out.is_relative_to(ROOT/'build'):raise ValueError('A4_SOURCE_OUTPUT')
    left_path=args.keys/'lexical-keys.json';right_path=args.keys/'control-keys.json'
    left_raw,right_raw=left_path.read_bytes(),right_path.read_bytes()
    left,right=json.loads(left_raw),json.loads(right_raw)
    first,second=entries(left,right); controls['entries'].append(first)
    stored['entries'].append(dict(second,keys={'article':packed(left)}))
    reviewed.control.validate(controls);reviewed.lexical.validate_ledger(copy.deepcopy(stored))
    if (CONTROL.read_bytes()!=c_raw or LEXICAL.read_bytes()!=l_raw or
            left_path.read_bytes()!=left_raw or right_path.read_bytes()!=right_raw or
            entries(left,right)!=(first,second)):
        raise ValueError('A4_SOURCE_INPUT_DRIFT')
    out.mkdir(parents=True,mode=0o700)
    for name,value in (('control-ledger.json',controls),('holdout-ledger.json',stored)):
        (out/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'articles':92622,'independentlyQualified':False}))


if __name__=='__main__':main()
