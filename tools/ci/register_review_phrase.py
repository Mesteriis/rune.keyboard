"""Register the disclosed public review phrase stages as regression contexts."""
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
import phrase_replay_review_screen as screen

ENTRY='ci-reviewed-chat-phrase-v1'
CONTROL=ROOT/'tools/typing_experiments/control-ledger.json'
LEXICAL=ROOT/'tools/typing_experiments/holdout-ledger.json'


def rows():
    result=set()
    for case,phrase in screen.inputs():
        words=phrase.split()
        for i,word in enumerate(words):
            targets={word,case['baseline']} if i==len(words)-1 else {word}
            prefixes={' '.join(words[:i])}
            # The disclosed run changed initial "мэри" to "Мэри" in two
            # phrases. Control identities preserve case, so keep both paths.
            if words[0]=='мэри':
                if i==0:targets.add('Мэри')
                else:prefixes.add(' '.join(['Мэри',*words[1:i]]))
            for prefix in prefixes:
                for target in targets:result.add((prefix,target))
    return [dict(language='ru',prefix=prefix,typed=word,expectedSpelling=word) for prefix,word in sorted(result)]


def entries():
    values=rows()
    paths=(Path(__file__).resolve(),Path(screen.__file__).resolve(),screen.SOURCE,screen.LOCK,screen.REVIEW,Path(screen.corpus.__file__).resolve())
    bindings={str(p.relative_to(ROOT)):screen.digest(p) for p in paths}
    first=dict(id=ENTRY,kind='regression',language='ru',rowCount=len(values),bindings=bindings,
        keys=sorted({control.key_for(r,'regression') for r in values}),
        semantics='Disclosed public reviewed phrase contexts, with baseline final-word outputs; not independent quality data.')
    second=dict(id=ENTRY+'-contexts',usage='historical-context-exclusion',rowCount=len(values),bindings=bindings,
        keys={'context':sorted(lexical.keys_for(values,'context'))},missingAxes=[],
        notes='Disclosed public phrase-stage contexts and baseline final-word outputs; no new family or source identity claimed.')
    return first,second


def check():
    a=control.load(CONTROL);b=lexical.load_ledger(LEXICAL);first,second=entries()
    if [e for e in a['entries'] if e['id']==ENTRY]!=[first] or [e for e in b['entries'] if e['id']==ENTRY+'-contexts']!=[second]:
        raise ValueError('REVIEW_PHRASE_DISCLOSURE_DRIFT')
    return len(rows())


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');p.add_argument('--output',type=Path);args=p.parse_args()
    if args.check:
        if args.output:raise ValueError('REVIEW_PHRASE_SCOPE')
        print(json.dumps({'contexts':check(),'independentQualification':False}));return
    if args.output is None:raise ValueError('REVIEW_PHRASE_SCOPE')
    out=args.output.resolve()
    if out.exists() or not out.is_relative_to(ROOT/'build'):raise ValueError('REVIEW_PHRASE_OUTPUT')
    raw_a=CONTROL.read_bytes();raw_b=LEXICAL.read_bytes();a=json.loads(raw_a);b=json.loads(raw_b)
    control.validate(a);logical=lexical.validate_ledger(copy.deepcopy(b));first,second=entries()
    if any(e['id']==ENTRY for e in a['entries']) or any(e['id']==ENTRY+'-contexts' for e in logical['entries']):raise ValueError('REVIEW_PHRASE_EXISTS')
    a['entries'].append(first);b['entries'].append(second);control.validate(a);lexical.validate_ledger(copy.deepcopy(b))
    if CONTROL.read_bytes()!=raw_a or LEXICAL.read_bytes()!=raw_b:raise ValueError('REVIEW_PHRASE_INPUT_DRIFT')
    out.mkdir(parents=True,mode=0o700)
    for name,value in (('control-ledger.json',a),('holdout-ledger.json',b)):(out/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'contexts':len(rows()),'independentQualification':False}))


if __name__=='__main__':main()
