"""Register disclosed phrase stages as context-only regression exclusions."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/typing_experiments'))
import control_ledger as controls
import holdout_ledger as lexical
from phrase_replay_smoke import CASES

ENTRY='ci-disclosed-phrase-replay-v1'
CONTROL=ROOT/'tools/typing_experiments/control-ledger.json'
LEXICAL=ROOT/'tools/typing_experiments/holdout-ledger.json'


def rows():
    result=set()
    for _,typed,expected,_ in CASES:
        original=typed.split(' '); corrected=expected.strip().split(' ')
        if len(original)!=len(corrected) or not 2<=len(original)<=6:raise ValueError('PHRASE_DISCLOSURE_SCOPE')
        for i in range(len(original)):
            for prefix in (' '.join(original[:i]),' '.join(corrected[:i])):
                for word in (original[i],corrected[i]):result.add((prefix,word))
    return [dict(language='ru',prefix=prefix,typed=word,expectedSpelling=word) for prefix,word in sorted(result)]


def expected_entries():
    values=rows()
    paths=[Path(__file__).resolve(),ROOT/'tools/ci/phrase_replay_smoke.py']
    bindings={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    control=dict(id=ENTRY,kind='regression',language='ru',rowCount=len(values),bindings=bindings,
        keys=sorted({controls.key_for(r,'regression') for r in values}),
        semantics='Disclosed phrase-stage contexts in typed and corrected form; not independent quality data.')
    context=dict(id=ENTRY+'-contexts',usage='historical-context-exclusion',rowCount=len(values),bindings=bindings,
        keys={'context':sorted(lexical.keys_for(values,'context'))},missingAxes=[],
        notes='Disclosed phrase-stage target contexts in typed and corrected form; source article and family are not asserted.')
    return control,context


def check():
    a=controls.load(CONTROL);b=lexical.load_ledger(LEXICAL);control,context=expected_entries()
    if [e for e in a['entries'] if e['id']==ENTRY]!=[control] or [e for e in b['entries'] if e['id']==ENTRY+'-contexts']!=[context]:
        raise ValueError('PHRASE_DISCLOSURE_DRIFT')
    return len(rows())


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.check:
        if args.output:raise ValueError('PHRASE_DISCLOSURE_SCOPE')
        print(json.dumps({'stageContexts':check(),'independentQualification':False}));return
    if args.output is None:raise ValueError('PHRASE_DISCLOSURE_SCOPE')
    output=args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('FRESH_PHRASE_DISCLOSURE_OUTPUT')
    raw_a=CONTROL.read_bytes();raw_b=LEXICAL.read_bytes();a=json.loads(raw_a);b=json.loads(raw_b)
    controls.validate(a);logical=lexical.validate_ledger(copy.deepcopy(b));control,context=expected_entries()
    if any(e['id']==ENTRY for e in a['entries']) or any(e['id']==ENTRY+'-contexts' for e in logical['entries']):raise ValueError('PHRASE_DISCLOSURE_EXISTS')
    a['entries'].append(control);b['entries'].append(context);controls.validate(a);lexical.validate_ledger(copy.deepcopy(b))
    if CONTROL.read_bytes()!=raw_a or LEXICAL.read_bytes()!=raw_b:raise ValueError('PHRASE_DISCLOSURE_INPUT_DRIFT')
    output.mkdir(parents=True,mode=0o700)
    for name,value in (('control-ledger.json',a),('holdout-ledger.json',b)):(output/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'stageContexts':len(rows()),'independentQualification':False}))


if __name__=='__main__':main()
