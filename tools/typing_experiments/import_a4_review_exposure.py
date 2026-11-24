#!/usr/bin/env python3
"""Quarantine reviewed public articles in both ledgers; never certify freshness."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

import a4_abbreviation_review_sample as sample
import control_ledger as control
import holdout_ledger as lexical

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / 'tools/typing_experiments/a4_controls'
SAMPLE = FOLDER / 'wikipedia-0011-review-sample.json'
REVIEW = FOLDER / 'wikipedia-0011-meaning-review.json'
CONTROL = ROOT / 'tools/typing_experiments/control-ledger.json'
LEXICAL = ROOT / 'tools/typing_experiments/holdout-ledger.json'
ENTRY = 'public-a4-wikipedia-meaning-review-v1'
SAMPLE_SHA = '2ae92996095bd6f8644f80de97858bdaece31caa50336a96585c5522684db1ca'
REVIEW_SHA = '393a22c912104c52edb6fb7c1c47f6dccb0acec321d4d4983a0fd4c293e18833'


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def entries():
    if sha(SAMPLE) != SAMPLE_SHA or sha(REVIEW) != REVIEW_SHA:
        raise ValueError('A4_REVIEW_FROZEN_IDENTITY')
    value = json.loads(SAMPLE.read_text()); review = json.loads(REVIEW.read_text())
    lock = json.loads(sample.base.LOCK.read_text())
    shards = [item for item in lock['shards'] if item['name'] == sample.base.SHARD]
    if (value.get('independentlyQualified') is not False or review.get('independentlyQualified') is not False or
            review.get('sampleSha256') != SAMPLE_SHA or value.get('helperSha256') != sha(sample.__file__) or
            value.get('frequencyHelperSha256') != sha(sample.base.__file__) or
            value.get('sourceLockSha256') != sha(sample.base.LOCK) or
            value.get('controlsSha256') != sha(sample.base.CONTROLS) or
            len(shards) != 1 or value.get('sourceSha256') != shards[0]['sha256'] or
            value.get('seed') != sample.SEED or value.get('sourceRows') != 92622):
        raise ValueError('A4_REVIEW_BINDINGS')
    records, labels = value['records'], review['labels']
    if len(records) != 46 or [item['index'] for item in labels] != list(range(46)):
        raise ValueError('A4_REVIEW_COVERAGE')
    rows = [{'article': row['article'], 'language': 'ru'} for row in records]
    a = sorted(lexical.keys_for(rows, 'article')); b = sorted({control.article_key(row) for row in rows})
    if len(a) != 46 or len(b) != 46: raise ValueError('A4_REVIEW_ARTICLES')
    paths = (SAMPLE, REVIEW, Path(__file__).resolve(), Path(sample.__file__).resolve(),
             Path(sample.base.__file__).resolve(), sample.base.LOCK, sample.base.CONTROLS,
             Path(control.__file__).resolve(), Path(lexical.__file__).resolve())
    bindings = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    c = dict(id=ENTRY, kind='source', language='ru', rowCount=46, keys=[], articleKeys=b,
             bindings=bindings, semantics='Public article exposure from a single-model meaning review; not qualification.')
    l = dict(id=ENTRY, usage='historical-exclusion', rowCount=46, keys={'article': a},
             missingAxes=['family', 'sentence', 'context'], bindings=bindings,
             notes='Article-only quarantine of reviewed public sources; no claim of full context or family coverage.')
    return c, l


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true'); group.add_argument('--output', type=Path)
    args=parser.parse_args(); c_raw, l_raw = CONTROL.read_bytes(), LEXICAL.read_bytes()
    controls, stored = json.loads(c_raw), json.loads(l_raw)
    control.validate(controls); logical = lexical.validate_ledger(copy.deepcopy(stored))
    first, second = entries()
    c_existing=[e for e in controls['entries'] if e['id']==ENTRY]
    l_existing=[e for e in logical['entries'] if e['id']==ENTRY]
    if args.check:
        if c_existing != [first] or l_existing != [second]: raise ValueError('A4_REVIEW_LEDGER_DRIFT')
        print(json.dumps({'articles':46,'independentlyQualified':False})); return
    output=args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build') or c_existing or l_existing:
        raise ValueError('A4_REVIEW_OUTPUT_OR_DUPLICATE')
    controls['entries'].append(first); stored['entries'].append(second)
    control.validate(controls); lexical.validate_ledger(copy.deepcopy(stored))
    if CONTROL.read_bytes()!=c_raw or LEXICAL.read_bytes()!=l_raw or entries()!=(first,second):
        raise ValueError('A4_REVIEW_INPUT_DRIFT')
    output.mkdir(parents=True,mode=0o700)
    for name,value in (('control-ledger.json',controls),('holdout-ledger.json',stored)):
        (output/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'articles':46,'independentlyQualified':False}))


if __name__ == '__main__': main()
