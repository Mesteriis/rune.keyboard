"""Quarantine exact public English Tatoeba token surfaces, not inferred lemmas.

The source is disclosed CC0 text. Hashes are unsalted and reversible. This
registration does not certify morphology, labels or independent qualification.
"""
import argparse
import bz2
import copy
import hashlib
import json
from pathlib import Path
import re
import unicodedata

import control_ledger as control
import english_family_keys as english
import ewt_surface_exclusions_v1 as ewt
import holdout_ledger as ledger
import import_english_tatoeba_screen as source

ROOT = Path(__file__).resolve().parents[2]
LEDGER = Path(__file__).with_name('holdout-ledger.json')
SOURCE = ROOT / source.SOURCE
LOCK = SOURCE.with_name('tatoeba-source-lock.json')
LOCK_SHA = '7c9116c827c492d2513410224f6cf8414591788ecbfbb9c050242b8bd1e5e910'
ENTRY = 'public-tatoeba-english-a1-exact-surface-exclusions-v1'
TOKEN = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)*")
JOINERS = "_'’‐‑–—-"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def joins(char):
    return bool(char) and (char.isalnum() or char in JOINERS or unicodedata.category(char).startswith('M'))


def extract(raw, lock_raw):
    if sha(raw) != source.DIGEST or sha(lock_raw) != LOCK_SHA:
        raise ValueError('EN_TATOEBA_SURFACE_SOURCE_IDENTITY')
    lock = json.loads(lock_raw)
    if lock.get('compressedSha256') != source.DIGEST or lock.get('license') != 'CC0-1.0':
        raise ValueError('EN_TATOEBA_SURFACE_LOCK')
    verified = source.rows_from_bytes(raw)
    keys = set(); rows = 0; context = None
    for line in bz2.decompress(raw).decode('utf-8').splitlines():
        sentence = line.split('\t')[2]
        for match in TOKEN.finditer(sentence):
            if joins(sentence[match.start()-1:match.start()] if match.start() else '') or joins(sentence[match.end():match.end()+1]):
                continue
            try:
                english.key_for(match.group())  # Shape check only; no lemma is inferred.
            except ValueError:
                continue
            keys.add(control.surface_key('en', match.group())); rows += 1
            if context is None and sentence[:match.start()].strip():
                value = dict(prefix=sentence[:match.start()], typed=match.group(), expectedSpelling=match.group())
                context = next(iter(ledger.keys_for([value], 'context')))
    if context is None:
        raise ValueError('EN_TATOEBA_SURFACE_EMPTY')
    return keys, rows, context, verified


def entry(value, raw, lock_raw):
    checked = ledger.validate_ledger(copy.deepcopy(value))
    parent = [e for e in checked['entries'] if e['id'] == source.ENTRY]
    if (len(parent) != 1 or parent[0].get('usage') != 'historical-source-exclusion' or
            parent[0].get('sourceRepository') != 'tatoeba' or parent[0].get('rowCount') != 41513 or
            parent[0].get('bindings', {}).get(source.SOURCE) != source.DIGEST):
        raise ValueError('EN_TATOEBA_SURFACE_PARENT')
    keys, rows, context, verified = extract(raw, lock_raw)
    if any(set(parent[0]['keys'][axis]) != ledger.keys_for(verified, axis) for axis in ('article','sentence')):
        raise ValueError('EN_TATOEBA_SURFACE_PARENT_DRIFT')
    extra = sorted(keys - ewt.load())
    paths = (Path(__file__).resolve(), SOURCE, LOCK, Path(source.__file__).resolve(),
             Path(control.__file__).resolve(), Path(english.__file__).resolve(),
             Path(ledger.__file__).resolve(), Path(ewt.__file__).resolve(), ewt.FIXTURE,
             ewt.ewt.LOCK, ROOT/'tools/typing_experiments/source_identities.py',
             ROOT/'tools/typing_experiments/conversation_split_checks.py')
    bindings = {str(path.relative_to(ROOT)):sha(path.read_bytes()) for path in paths}
    return dict(id=ENTRY,usage='historical-context-exclusion',keys={'context':[context]},missingAxes=[],
        unsupportedSurfaceKeys=extra,bindings=bindings,rowCount=rows,sourceRows=len(verified),
        parentEntries=[source.ENTRY],sourceRepository='tatoeba',
        notes='Exact public token surfaces outside the EWT surface fixture; one source-attested context only. No labels, inferred families or independent qualification.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--check',action='store_true'); modes.add_argument('--register',type=Path)
    args = parser.parse_args()
    original = LEDGER.read_bytes(); source_raw = SOURCE.read_bytes(); lock_raw = LOCK.read_bytes()
    value = json.loads(original); expected = entry(value, source_raw, lock_raw)
    if (LEDGER.read_bytes() != original or SOURCE.read_bytes() != source_raw or LOCK.read_bytes() != lock_raw or
            entry(json.loads(original), source_raw, lock_raw) != expected):
        raise ValueError('EN_TATOEBA_SURFACE_INPUT_DRIFT')
    if args.check:
        if [e for e in ledger.validate_ledger(value)['entries'] if e['id'] == ENTRY] != [expected]:
            raise ValueError('EN_TATOEBA_SURFACE_LEDGER_DRIFT')
    else:
        output = args.register.resolve()
        if output.exists() or not output.is_relative_to(ROOT/'build'):
            raise ValueError('EN_TATOEBA_SURFACE_OUTPUT')
        if any(e['id'] == ENTRY for e in value['entries']):
            raise ValueError('EN_TATOEBA_SURFACE_EXISTS')
        value['entries'].append(expected); ledger.validate_ledger(copy.deepcopy(value))
        with output.open('x',encoding='utf-8') as stream:
            json.dump(value,stream,ensure_ascii=False,sort_keys=True,indent=2);stream.write('\n')
    print(json.dumps({'newSurfaceKeys':len(expected['unsupportedSurfaceKeys']),
                      'sourceRows':expected['sourceRows'],'tokenRows':expected['rowCount'],
                      'independentQualification':False},sort_keys=True))


if __name__ == '__main__':
    main()
