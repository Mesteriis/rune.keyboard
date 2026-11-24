"""Exclude source-derived public Taiga dev contexts without claiming freshness."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import unicodedata

import control_ledger as control
import holdout_ledger as lexical
import import_taiga_dev_exposure as taiga

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = taiga.LOCK.with_name('context-exclusions-v1.json')
CONTROL = Path(__file__).with_name('control-ledger.json')
LEXICAL = Path(__file__).with_name('holdout-ledger.json')
ENTRY = 'public-taiga-dev-source-contexts-v1'
FIXTURE_SHA = 'ed6136259b203f726b66a1fc4e62ea0f69fe9d180a9bfcda03bc28a2805f285e'
WORD = re.compile('[А-Яа-яЁё]+')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_keys(data):
    lock = json.loads(taiga.LOCK.read_text())
    sentences, count = taiga.sentence_keys(data, lock['sha256'])
    base = lexical.load_ledger(LEXICAL)
    parent = [item for item in base['entries'] if item['id'] == taiga.ENTRY]
    if len(parent) != 1 or parent[0]['rowCount'] != count or parent[0]['keys']['sentence'] != sentences:
        raise ValueError('TAIGA_CONTEXT_PARENT')
    controls, contexts = set(), set()
    tokens = 0
    for line in data.decode('utf-8').splitlines():
        if not line.startswith('# text = '):
            continue
        sentence = unicodedata.normalize('NFC', line.removeprefix('# text = '))
        for match in WORD.finditer(sentence):
            prefix = sentence[max(0, match.start() - 128):match.start()].lstrip()
            word = match.group()
            for left, target in ((prefix, word), (prefix.casefold(), word.casefold())):
                row = dict(language='ru', prefix=left, typed=target, expectedSpelling=target)
                controls.add(control.key_for(row, 'regression'))
                contexts.update(lexical.keys_for([row], 'context'))
            tokens += 1
    if not tokens or not controls or not contexts:
        raise ValueError('TAIGA_CONTEXT_EMPTY')
    return dict(schema=1, sourceSha256=lock['sha256'], sentenceCount=count, tokenOccurrences=tokens,
                variants=2 * tokens, controlKeys=sorted(controls), contextKeys=sorted(contexts))


def fixture():
    raw = FIXTURE.read_bytes()
    if sha(raw) != FIXTURE_SHA:
        raise ValueError('TAIGA_CONTEXT_FIXTURE')
    value = json.loads(raw)
    if (value.get('schema') != 1 or value.get('sourceSha256') != json.loads(taiga.LOCK.read_text())['sha256'] or
            value.get('sentenceCount') != 1260 or type(value.get('tokenOccurrences')) is not int or
            value['tokenOccurrences'] < 1 or value.get('variants') != 2 * value['tokenOccurrences']):
        raise ValueError('TAIGA_CONTEXT_FIXTURE')
    for name in ('controlKeys', 'contextKeys'):
        keys = value.get(name)
        if (not isinstance(keys, list) or not keys or keys != sorted(set(keys)) or len(keys) > value['variants'] or
                any(not isinstance(key, str) or not re.fullmatch('[0-9a-f]{64}', key) for key in keys)):
            raise ValueError('TAIGA_CONTEXT_KEYS')
    return value


def entries(base):
    value = fixture()
    parents = [entry for entry in lexical.validate_ledger(copy.deepcopy(base))['entries'] if entry['id'] == taiga.ENTRY]
    if len(parents) != 1 or parents[0]['rowCount'] != value['sentenceCount']:
        raise ValueError('TAIGA_CONTEXT_PARENT')
    paths = (Path(__file__).resolve(), FIXTURE, taiga.LOCK, Path(taiga.__file__).resolve(),
             Path(control.__file__).resolve(), Path(lexical.__file__).resolve(),
             ROOT / 'tools/typing_experiments/conversation_split_checks.py')
    bindings = {str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in paths}
    first = dict(id=ENTRY, kind='regression', language='ru', rowCount=value['variants'],
                 keys=value['controlKeys'], bindings=bindings,
                 semantics='Source-derived public Taiga within-sentence contexts; not independent qualification.')
    second = dict(id=ENTRY + '-lexical', usage='historical-context-exclusion', rowCount=value['variants'],
                  keys={'context': value['contextKeys']}, missingAxes=[], bindings=bindings, parentEntries=[taiga.ENTRY],
                  notes='Original and casefolded public source contexts; sentence boundaries are not document boundaries.')
    return first, second


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture', type=Path); p.add_argument('--check', action='store_true'); p.add_argument('--output', type=Path)
    args = p.parse_args()
    if args.check:
        if args.capture or args.output: raise ValueError('TAIGA_CONTEXT_SCOPE')
        base = json.loads(LEXICAL.read_bytes()); first, second = entries(base)
        controls = control.load(CONTROL); logical = lexical.validate_ledger(copy.deepcopy(base))
        if ([e for e in controls['entries'] if e['id'] == ENTRY] != [first] or
                [e for e in logical['entries'] if e['id'] == ENTRY + '-lexical'] != [second]):
            raise ValueError('TAIGA_CONTEXT_DRIFT')
        print(json.dumps({'variants': first['rowCount'], 'independentQualification': False})); return
    if args.output is None: raise ValueError('TAIGA_CONTEXT_SCOPE')
    output = args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'): raise ValueError('TAIGA_CONTEXT_OUTPUT')
    if args.capture:
        source, lock, base = args.capture.read_bytes(), taiga.LOCK.read_bytes(), LEXICAL.read_bytes()
        paths = (Path(__file__).resolve(), Path(taiga.__file__).resolve(), Path(control.__file__).resolve(),
                 Path(lexical.__file__).resolve(), ROOT / 'tools/typing_experiments/conversation_split_checks.py')
        helpers = {path: sha(path.read_bytes()) for path in paths}
        value = source_keys(source)
        if (args.capture.read_bytes() != source or taiga.LOCK.read_bytes() != lock or LEXICAL.read_bytes() != base or
                any(sha(path.read_bytes()) != digest for path, digest in helpers.items())):
            raise ValueError('TAIGA_CONTEXT_INPUT_DRIFT')
        output.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')
        print(json.dumps({k: value[k] for k in ('sentenceCount', 'tokenOccurrences', 'variants')})); return
    before_c, before_l = CONTROL.read_bytes(), LEXICAL.read_bytes()
    controls, stored = json.loads(before_c), json.loads(before_l)
    control.validate(controls); logical = lexical.validate_ledger(copy.deepcopy(stored))
    first, second = entries(stored)
    if any(e['id'] == ENTRY for e in controls['entries']) or any(e['id'] == ENTRY + '-lexical' for e in logical['entries']):
        raise ValueError('TAIGA_CONTEXT_EXISTS')
    controls['entries'].append(first); stored['entries'].append(second)
    control.validate(controls); lexical.validate_ledger(copy.deepcopy(stored))
    if CONTROL.read_bytes() != before_c or LEXICAL.read_bytes() != before_l or entries(json.loads(before_l)) != (first, second):
        raise ValueError('TAIGA_CONTEXT_INPUT_DRIFT')
    output.mkdir(parents=True, mode=0o700)
    for name, value in (('control-ledger.json', controls), ('holdout-ledger.json', stored)):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'variants': first['rowCount'], 'independentQualification': False}))


if __name__ == '__main__': main()
