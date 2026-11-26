#!/usr/bin/env python3
"""Create a verified compact ledger copy without changing the input."""
import argparse
import hashlib
import json
from pathlib import Path

from holdout_ledger import pack_ledger, validate_ledger

ROOT=Path(__file__).resolve().parents[2]


def run(source,output,minimum=1000):
    source=Path(source);output=Path(output)
    if source.is_symlink() or output.is_symlink() or output.exists() or not output.resolve().is_relative_to(ROOT/'build'):
        raise ValueError('COMPACT_PATH')
    raw=source.read_bytes();before=hashlib.sha256(raw).hexdigest()
    original=validate_ledger(json.loads(raw))
    packed=pack_ledger(original,minimum)
    encoded=(json.dumps(packed,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
    if validate_ledger(json.loads(encoded))!=original:raise ValueError('COMPACT_LOGICAL_DRIFT')
    if hashlib.sha256(source.read_bytes()).hexdigest()!=before:raise ValueError('COMPACT_INPUT_DRIFT')
    with output.open('xb') as target:target.write(encoded)
    return dict(inputSha256=before,outputSha256=hashlib.sha256(encoded).hexdigest(),
                inputBytes=len(raw),outputBytes=len(encoded),entries=len(original['entries']),logicalEntriesUnchanged=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--minimum',type=int,default=1000);args=parser.parse_args()
    print(json.dumps(run(args.input,args.output,args.minimum),sort_keys=True))


if __name__=='__main__':main()
