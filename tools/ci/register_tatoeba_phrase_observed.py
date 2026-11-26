"""Quarantine observed contexts from the disclosed full-session replay."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/ci'))
import register_tatoeba_phrase_inputs as source
import tatoeba_phrase_replay as replay
from authored_phrase_replay import evaluate
import control_ledger as control
import holdout_ledger as lexical

BASE = ROOT / 'tools/typing_experiments/chat_regression'
FIXTURE = BASE / 'tatoeba-full-phrase-observed-v1.json'
RECEIPT = BASE / 'tatoeba-full-phrase-replay-v1.json'
ENTRY = 'tatoeba-full-phrase-observed-v1'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load_fixture():
    value = json.loads(FIXTURE.read_bytes()); receipt = json.loads(RECEIPT.read_bytes())
    if (value.get('schema') != 1 or value.get('receiptSha256') != sha(RECEIPT.read_bytes()) or
            value.get('resultSha256') != receipt.get('resultSha256') or
            receipt.get('scope') != 'disclosed-tatoeba-full-session-diagnostic' or
            receipt.get('independentQualification') is not False or receipt.get('observedContextsRegistered') is not False):
        raise ValueError('TATOEBA_OBSERVED_FIXTURE')
    for name in ('controlKeys', 'contextKeys'):
        keys = value.get(name)
        if (not isinstance(keys, list) or keys != sorted(set(keys)) or
                any(not isinstance(k, str) or len(k) != 64 or any(c not in '0123456789abcdef' for c in k) for k in keys)):
            raise ValueError('TATOEBA_OBSERVED_KEYS')
    return value


def extract(run_dir):
    receipt_raw = (run_dir / 'receipt.json').read_bytes(); receipt = json.loads(receipt_raw)
    raw = (run_dir / 'run-1.jsonl').read_bytes()
    if (raw != (run_dir / 'run-2.jsonl').read_bytes() or sha(raw) != receipt.get('resultSha256') or
            receipt.get('scope') != 'disclosed-tatoeba-full-session-diagnostic' or
            receipt.get('observedContextsRegistered') is not False or receipt.get('independentQualification') is not False):
        raise ValueError('TATOEBA_OBSERVED_REPLAY')
    bindings = receipt.get('inputSha256')
    if not isinstance(bindings, dict): raise ValueError('TATOEBA_OBSERVED_BINDINGS')
    for name, expected in bindings.items():
        if not isinstance(name, str) or Path(name).is_absolute() or '..' in Path(name).parts or '\\' in name:
            raise ValueError('TATOEBA_OBSERVED_BINDING_PATH')
        if not name.startswith('external/') and (not (ROOT/name).is_file() or replay.digest(ROOT/name) != expected):
            raise ValueError('TATOEBA_OBSERVED_DRIFT')
    a = control.load(source.CONTROL); b = lexical.load_ledger(source.LEXICAL)
    cases = source.cases(b); rows = [json.loads(line) for line in raw.splitlines()]
    if evaluate(cases, rows) != receipt.get('metrics'):
        raise ValueError('TATOEBA_OBSERVED_METRICS')
    known_c = {key for entry in a['entries'] if entry['kind'] == 'regression' for key in entry['keys']}
    known_l = {key for entry in b['entries'] for key in entry['keys'].get('context', [])}
    controls = set(); contexts = set(); variants = 0
    for row in rows:
        for stage in row['phraseStages']:
            before = stage['before']; word = stage['typed']; after = stage['after']
            if not after.endswith(' '): raise ValueError('TATOEBA_OBSERVED_BOUNDARY')
            actual = after[:-1].split(' ')
            if not actual or not actual[-1]: raise ValueError('TATOEBA_OBSERVED_BOUNDARY')
            for prefix, token in ((before[:-len(word)].strip(), word), (' '.join(actual[:-1]), actual[-1])):
                value = dict(language='ru', prefix=prefix, typed=token, expectedSpelling=token)
                controls.add(control.key_for(value, 'regression'))
                contexts.update(lexical.keys_for([value], 'context')); variants += 1
    return dict(schema=1, receiptSha256=sha(receipt_raw), resultSha256=sha(raw), variants=variants,
                controlKeys=sorted(controls-known_c), contextKeys=sorted(contexts-known_l)), receipt_raw


def entries():
    fixture = load_fixture()
    paths = (Path(__file__).resolve(), FIXTURE, RECEIPT, Path(source.__file__).resolve(),
             Path(replay.__file__).resolve(), ROOT/'tools/ci/authored_phrase_replay.py',
             Path(control.__file__).resolve(), Path(lexical.__file__).resolve())
    bindings = {str(p.relative_to(ROOT)): replay.digest(p) for p in paths}
    c = dict(id=ENTRY, kind='regression', language='ru', rowCount=fixture['variants'], bindings=bindings,
             keys=fixture['controlKeys'], semantics='Observed public full-session stage contexts; not independent qualification.')
    l = dict(id=ENTRY+'-contexts', usage='historical-context-exclusion', rowCount=fixture['variants'],
             bindings=bindings, keys={'context': fixture['contextKeys']}, missingAxes=[],
             notes='Observed public full-session stage contexts; not an independent holdout.')
    return c, l


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--extract', type=Path); modes.add_argument('--register', type=Path); modes.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.extract:
        out = args.extract.resolve()
        if not out.is_relative_to(ROOT/'build') or out.exists(): raise ValueError('TATOEBA_OBSERVED_OUTPUT')
        value, receipt = extract(ROOT/'build/ci-tatoeba-full-phrase')
        out.mkdir(parents=True, mode=0o700)
        (out/FIXTURE.name).write_text(json.dumps(value, sort_keys=True, indent=2)+'\n')
        (out/RECEIPT.name).write_bytes(receipt)
        print(json.dumps({'variants':value['variants'], 'newControlKeys':len(value['controlKeys']), 'newContextKeys':len(value['contextKeys'])})); return
    old_a=source.CONTROL.read_bytes(); old_b=source.LEXICAL.read_bytes()
    a=control.validate(json.loads(old_a)); b=json.loads(old_b); expanded=lexical.validate_ledger(copy.deepcopy(b))
    first,second=entries()
    if args.check:
        if [e for e in a['entries'] if e['id']==ENTRY] != [first] or [e for e in expanded['entries'] if e['id']==ENTRY+'-contexts'] != [second]:
            raise ValueError('TATOEBA_OBSERVED_REGISTRY_DRIFT')
    else:
        out=args.register.resolve()
        if out.exists() or not out.is_relative_to(ROOT/'build'): raise ValueError('TATOEBA_OBSERVED_OUTPUT')
        if any(e['id']==ENTRY for e in a['entries']) or any(e['id']==ENTRY+'-contexts' for e in expanded['entries']):
            raise ValueError('TATOEBA_OBSERVED_EXISTS')
        a['entries'].append(first); b['entries'].append(second)
        control.validate(a); lexical.validate_ledger(copy.deepcopy(b))
        if old_a != source.CONTROL.read_bytes() or old_b != source.LEXICAL.read_bytes() or (first,second) != entries():
            raise ValueError('TATOEBA_OBSERVED_DRIFT')
        out.mkdir(parents=True, mode=0o700)
        for name,value in (('control-ledger.json',a),('holdout-ledger.json',b)):
            (out/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'newControlKeys':len(first['keys']), 'newContextKeys':len(second['keys']['context']), 'independentQualification':False}))


if __name__ == '__main__': main()
