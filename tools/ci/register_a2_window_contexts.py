"""Quarantine synthetic candidate contexts disclosed by A2 cache probes."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/typing_experiments'))
import control_ledger as control
from recover_legacy_families import sha

LEDGER=ROOT/'tools/typing_experiments/control-ledger.json'
# The original registration remains bound by the historical Spanish control fixture.
ENTRY='a2-bounded-prefix-native-probe-v2'
ANDROID=ROOT/'runtime-llama/src/androidTest/java/io/github/mesteriis/rune/runtime/llama/LlamaRealModelInstrumentedTest.kt'
WINDOW_TEST=ROOT/'app/src/test/java/io/github/mesteriis/rune/keyboard/smarttyping/session/ModelPrefixWindowTest.kt'
HOST=ROOT/'tools/eval/smart-typing-0.3/a2_cache_probe.cpp'


def entry():
    android=ANDROID.read_text();window=WINDOW_TEST.read_text();host=HOST.read_text()
    # Fail closed if either probe's exact synthetic requests stop matching.
    for marker in ('words(17, 39)', 'words(17, 40)', 'words(34, 56)', '"hello", "helllo"'):
        if marker not in android:raise ValueError('A2_WINDOW_ANDROID_SCOPE')
    for marker in ('words(17, 39)', 'words(17, 40)', 'words(34, 56)', 'words(0, 56)'):
        if marker not in window:raise ValueError('A2_WINDOW_COMPONENT_SCOPE')
    for marker in ('words(17, 39)', 'words(17, 40)', 'words(34, 56)', '{0, "hello"}, {1, "helllo"}'):
        if marker not in host:raise ValueError('A2_WINDOW_HOST_SCOPE')
    rows=[]
    for first,last in ((17,39),(17,40),(34,56)):
        prefix=''.join(f'word{i:02d} ' for i in range(first,last+1))
        rows.extend(dict(language='en',prefix=prefix,typed=word) for word in ('hello','helllo'))
    paths=(Path(__file__).resolve(),ANDROID,WINDOW_TEST,HOST)
    return dict(id=ENTRY,kind='regression',language='en',rowCount=len(rows),
        bindings={str(p.relative_to(ROOT)):sha(p) for p in paths},
        keys=sorted({control.key_for(row,'regression') for row in rows}),
        semantics='Disclosed synthetic bounded-prefix model contexts; not independent qualification.')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');p.add_argument('--output',type=Path)
    args=p.parse_args()
    if args.check==(args.output is not None):raise ValueError('A2_WINDOW_SCOPE')
    old=LEDGER.read_bytes();ledger=control.validate(json.loads(old));expected=entry()
    if args.check:
        if [e for e in ledger['entries'] if e['id']==ENTRY]!=[expected]:raise ValueError('A2_WINDOW_LEDGER_DRIFT')
    else:
        out=args.output.resolve()
        if out.exists() or not out.is_relative_to(ROOT/'build'):raise ValueError('A2_WINDOW_OUTPUT')
        if any(e['id']==ENTRY for e in ledger['entries']):raise ValueError('A2_WINDOW_EXISTS')
        ledger['entries'].append(expected);control.validate(ledger)
        if LEDGER.read_bytes()!=old or entry()!=expected:raise ValueError('A2_WINDOW_INPUT_DRIFT')
        with out.open('x',encoding='utf-8') as f:json.dump(ledger,f,sort_keys=True,indent=2,ensure_ascii=False);f.write('\n')
    print(json.dumps({'contexts':expected['rowCount'],'independentQualification':False}))


if __name__=='__main__':main()
