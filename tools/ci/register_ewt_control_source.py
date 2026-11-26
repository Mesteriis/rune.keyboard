"""Mirror disclosed EWT document exclusions into the control registry."""
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

ENTRY='historical-english-ewt-control-source-v1'
PARENT='public-ud-english-ewt-2.18-exposure'
CONTROL=ROOT/'tools/typing_experiments/control-ledger.json'
LEXICAL=ROOT/'tools/typing_experiments/holdout-ledger.json'
FIXTURE=ROOT/'tools/typing_experiments/ewt-control-source-v1'
CONTROL_SHA='461a8977336cd2836f746565e7bb6fdd71ce0591c237dc78f6c65c1d72cbe470'
PARENT_SHA='9f822a736cbea64a2f856f15653dfe9c2dd89c091d253c16b038f21738475748'


def sha(raw):return hashlib.sha256(raw).hexdigest()


def entry(ledger):
    ledger=lexical.validate_ledger(copy.deepcopy(ledger))
    parents=[item for item in ledger['entries'] if item['id']==PARENT]
    if len(parents)!=1:raise ValueError('EWT_CONTROL_PARENT')
    parent=parents[0]
    if (parent.get('usage')!='historical-source-exclusion' or parent.get('sourceRepository')!='ud-english-ewt' or
        parent.get('rowCount')!=16622 or parent.get('missingAxes')!=[] or
        set(parent.get('keys',{}))!={'article','sentence'} or len(parent['keys']['article'])!=1174 or
        len(parent['keys']['sentence'])!=15483):raise ValueError('EWT_CONTROL_PARENT_SCOPE')
    expected={
        'tools/typing_experiments/holdout_ledger.py':'0f555bd379d62d49b1fff74e6f2051619c11dcbda61fb3c692afd1c21258c56e',
        'tools/typing_experiments/import_english_ewt_exposure.py':'83cb95bf172eb163fe7828c4059a7e7fbb61e3a4fe3624fe7f01fcf5fac1f965',
        'tools/typing_experiments/public_sources/ud-ewt-2.18/source-lock.json':'380668545aa5b37008eea1708bd9da9375fb1825d3f1b5ee76a6a469accc4709',
        'tools/typing_experiments/source_identities.py':'f4e8c95415c180702f15a291fc32462ac4e2bd95046706bf60f98a04b40c98c4'}
    historical='tools/typing_experiments/holdout_ledger.py'
    old_ledger=FIXTURE/'sources'/(expected[historical]+'.txt')
    if (parent.get('bindings')!=expected or sha(old_ledger.read_bytes())!=expected[historical] or
        any(sha((ROOT/name).read_bytes())!=digest for name,digest in expected.items() if name!=historical)):
        raise ValueError('EWT_CONTROL_SOURCE_DRIFT')
    frozen=FIXTURE/'sources'/(CONTROL_SHA+'.txt')
    if sha(frozen.read_bytes())!=CONTROL_SHA:raise ValueError('EWT_CONTROL_HELPER_DRIFT')
    paths=[Path(__file__).resolve(),FIXTURE/'NOTICE.md',frozen,old_ledger,
           *(ROOT/name for name in expected if name!=historical)]
    bindings={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in paths}
    parent_raw=json.dumps(parent,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    if sha(parent_raw)!=PARENT_SHA:raise ValueError('EWT_CONTROL_PARENT_IDENTITY')
    return dict(id=ENTRY,kind='source',language='en',rowCount=parent['rowCount'],bindings=bindings,
        keys=[],articleKeys=parent['keys']['article'],parentEntrySha256=sha(parent_raw),
        semantics='All disclosed EWT document keys; no source text and no independent qualification.')


def check():
    expected=entry(json.loads(LEXICAL.read_bytes()));ledger=control.load(CONTROL)
    if [e for e in ledger['entries'] if e['id']==ENTRY]!=[expected]:raise ValueError('EWT_CONTROL_DRIFT')
    return len(expected['articleKeys'])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');p.add_argument('--output',type=Path)
    args=p.parse_args()
    if args.check:
        if args.output:raise ValueError('EWT_CONTROL_SCOPE')
        print(json.dumps({'documents':check(),'independentQualification':False}));return
    if args.output is None:raise ValueError('EWT_CONTROL_SCOPE')
    output=args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('EWT_CONTROL_OUTPUT')
    old_a,old_b=CONTROL.read_bytes(),LEXICAL.read_bytes();source=entry(json.loads(old_b))
    ledger=control.validate(json.loads(old_a))
    if any(e['id']==ENTRY for e in ledger['entries']):raise ValueError('EWT_CONTROL_EXISTS')
    ledger['entries'].append(source);control.validate(ledger)
    if CONTROL.read_bytes()!=old_a or LEXICAL.read_bytes()!=old_b or entry(json.loads(old_b))!=source:
        raise ValueError('EWT_CONTROL_INPUT_DRIFT')
    output.mkdir(parents=True,mode=0o700)
    (output/'control-ledger.json').write_text(json.dumps(ledger,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'documents':len(source['articleKeys']),'independentQualification':False}))


if __name__=='__main__':main()
