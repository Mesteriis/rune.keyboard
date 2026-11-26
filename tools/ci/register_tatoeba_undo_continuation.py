"""Register new public regression contexts observed after Undo continuation."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/ci'))
import register_tatoeba_phrase_inputs as source
import tatoeba_phrase_replay as replay
import control_ledger as control

RECEIPT=ROOT/'docs/acceptance/2026-11-09-q5-undo-continuation-evidence.json'
ENTRY='tatoeba-undo-continuation-observed-v1'


def entry():
    receipt=json.loads(RECEIPT.read_bytes());keys=receipt.get('unregisteredControlKeys')
    if (receipt.get('schema')!=1 or receipt.get('scope')!='disclosed-undo-continue-diagnostic' or
            receipt.get('independentQualification') is not False or receipt.get('cases')!=123 or
            receipt.get('subsequentWords')!=381 or receipt.get('laterPrefixChanges')!=0 or
            receipt.get('unregisteredContextKeys')!=[] or not isinstance(keys,list) or len(keys)!=10 or
            keys!=sorted(set(keys)) or any(not isinstance(k,str) or len(k)!=64 or any(c not in '0123456789abcdef' for c in k) for k in keys)):
        raise ValueError('UNDO_CONTINUATION_RECEIPT')
    # The receipt retains the historical runner and harness hashes; do not
    # make this registration depend on their current, evolving contents.
    paths=(Path(__file__).resolve(),RECEIPT,ROOT/'tools/ci/tatoeba_phrase_replay.py',
           ROOT/'tools/ci/register_tatoeba_phrase_inputs.py',Path(control.__file__).resolve())
    bindings={str(p.relative_to(ROOT)):replay.digest(p) for p in paths}
    return dict(id=ENTRY,kind='regression',language='ru',rowCount=len(keys),keys=keys,bindings=bindings,
        semantics='Previously unregistered public stage contexts observed after Undo and continuation; not independent qualification.')


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--check',action='store_true');g.add_argument('--register',type=Path)
    args=p.parse_args();old=source.CONTROL.read_bytes();ledger=control.validate(json.loads(old));new=entry()
    if args.check:
        if [x for x in ledger['entries'] if x['id']==ENTRY]!=[new]:raise ValueError('UNDO_CONTINUATION_REGISTRY_DRIFT')
    else:
        out=args.register.resolve()
        if out.exists() or not out.is_relative_to(ROOT/'build'):raise ValueError('UNDO_CONTINUATION_OUTPUT')
        if any(x['id']==ENTRY for x in ledger['entries']):raise ValueError('UNDO_CONTINUATION_EXISTS')
        receipt=json.loads(RECEIPT.read_bytes());bindings=receipt['inputSha256']
        for path in (source.CONTROL,source.LEXICAL):
            if bindings.get(str(path.relative_to(ROOT)))!=replay.digest(path):raise ValueError('UNDO_CONTINUATION_REGISTRY_CHANGED')
        existing={k for item in ledger['entries'] if item['kind']=='regression' for k in item['keys']}
        if set(new['keys']) & existing:raise ValueError('UNDO_CONTINUATION_ALREADY_PRESENT')
        ledger['entries'].append(new);control.validate(ledger)
        if source.CONTROL.read_bytes()!=old or entry()!=new:raise ValueError('UNDO_CONTINUATION_DRIFT')
        out.parent.mkdir(parents=True,exist_ok=True)
        with out.open('x',encoding='utf-8') as stream:json.dump(ledger,stream,ensure_ascii=False,sort_keys=True,indent=2);stream.write('\n')
    print(json.dumps({'controlKeys':len(new['keys']),'independentQualification':False}))


if __name__=='__main__':main()
