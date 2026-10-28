#!/usr/bin/env python3
"""Public RU neighbour recovery preparation, label-isolated replay and separate release gate.

Only generated public text enters the host replay. Training, calibration and holdout
use different Wikipedia shards and disjoint morphology lemma IDs. No personal logs.
"""
from __future__ import annotations
import argparse
import base64
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import random
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import prepare_external_spelling_holdout as common

GROUPS = ('adjacent2', 'adjacent3', 'mixed2', 'mixed3')
ROWS = ('йцукенгшщзхъ', 'фывапролджэ', 'ячсмитьбю')
SEED = 'neighbor-recovery-v1-20260926'
MORPH = ROOT / 'app/src/main/assets/smarttyping/lexicon/ru.morph'
FREQUENCY = ROOT / 'build/smart-typing-0.3/corpus-inputs/ru_50k.txt'
CONTEXT = ROOT / 'app/src/main/assets/smarttyping/experiments/ru-ranking-context.bin'

def digest(path): return common.sha256(Path(path))
def write(path, value): Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)+'\n')
def read(path): return [json.loads(line) for line in Path(path).read_text().splitlines() if line]
def jsonl(path, rows): Path(path).write_text(''.join(json.dumps(r, ensure_ascii=False, sort_keys=True)+'\n' for r in rows))
def adjacent(a, b):
    positions = {c: (2*x+y, y) for y, row in enumerate(ROWS) for x, c in enumerate(row)}
    if a not in positions or b not in positions: return False
    ax, ay = positions[a]; bx, by = positions[b]
    return (ay == by and abs(ax-bx) == 2) or (abs(ay-by) == 1 and abs(ax-bx) <= 1)

def distance(a, b):
    def subs(x, y):
        if len(x) != len(y): return 100
        return sum(0 if l == r else 1 if adjacent(l,r) else 100 for l,r in zip(x,y))
    best = subs(a,b)
    if len(a) == len(b)+1:
        best = min(best, *(1+subs(a[:i]+a[i+1:], b) for i in range(len(a))))
    if len(b) == len(a)+1:
        best = min(best, *(1+subs(a, b[:i]+b[i+1:]) for i in range(len(b))))
    if len(a) == len(b):
        for i in range(len(a)-1):
            if a[i] == b[i+1] and a[i+1] == b[i]:
                best = min(best, 1+subs(a[:i]+a[i+2:], b[:i]+b[i+2:]))
    return best

def morphology():
    data = MORPH.read_bytes()
    if digest(MORPH) != 'c1707864a8fbc805aa98bc8307be99f2c9904eec5cc27d26a5220e001d88d28b': raise ValueError('MORPH_IDENTITY')
    if data[:8] != b'RUNEMRF1' or hashlib.sha256(data[:-32]).digest() != data[-32:]: raise ValueError('MORPH_FORMAT')
    width, count, blocks, start = struct.unpack_from('<IIII', data, 8)
    result = {}; offset = start; previous = b''
    for i in range(count):
        if i % width == 0: previous = b''
        prefix, size, lemma = struct.unpack_from('<BBI', data, offset)
        value = previous[:prefix]+data[offset+6:offset+6+size]
        result[value.decode()] = lemma
        offset += 6+size; previous = value
    if offset != len(data)-32: raise ValueError('MORPH_LENGTH')
    return result

def typo(word, group, salt, dictionary):
    count = int(group[-1]); structural = group.startswith('mixed')
    rng = random.Random(hashlib.sha256((SEED+salt+word+group).encode()).digest())
    for attempt in range(80):
        letters = list(word)
        if structural:
            i = rng.randrange(len(letters)-1)
            op = attempt % 3
            if op == 0: del letters[i]
            elif op == 1: letters.insert(i, rng.choice(''.join(ROWS)))
            else: letters[i], letters[i+1] = letters[i+1], letters[i]
        positions = rng.sample(range(len(letters)), count-int(structural))
        for i in positions:
            neighbors = [c for c in ''.join(ROWS) if adjacent(letters[i], c)]
            if neighbors: letters[i] = rng.choice(neighbors)
        value = ''.join(letters)
        if value not in dictionary and len(value) >= (7 if count == 3 else 5) and distance(value,word) == count:
            return value
    return None

def prepare(output):
    import pyarrow.parquet as parquet
    if output.exists(): raise ValueError('FRESH_OUTPUT_REQUIRED')
    if digest(FREQUENCY) != common.FREQUENCY_SHA256: raise ValueError('FREQUENCY_IDENTITY')
    dictionary = morphology(); known = {line.split()[0] for line in FREQUENCY.read_text().splitlines()}
    generator = common.load_generator()
    pools = {part: {} for part in ('train','calibration','holdout')}; bindings = {}
    article_sets = {part: set() for part in pools}
    for shard in range(11,18):
        part = 'train' if shard <= 13 else 'calibration' if shard <= 15 else 'holdout'
        source = ROOT / f'build/typing-ranker-v2/ru-{shard:04d}.parquet'
        manifests = list((ROOT/'build/typing-ranker-v2').glob(f'external-holdout-*-ru{shard:04d}/manifest.json'))
        if len(manifests) != 1: raise ValueError('SOURCE_MANIFEST')
        binding = json.loads(manifests[0].read_text())['source']
        if digest(source) != binding['sha256'] or source.stat().st_size != binding['bytes']: raise ValueError('SOURCE_IDENTITY')
        bindings[str(source.relative_to(ROOT))] = binding
        for batch in parquet.ParquetFile(source).iter_batches(batch_size=128, columns=['id','text']):
            for article, text in zip(batch.column(0).to_pylist(), batch.column(1).to_pylist()):
                article_sets[part].add(str(article))
                for item in generator.spelling_candidates(text or '', 'ru', known, set(), 26092026):
                    word = item['word']; lemma = dictionary.get(word)
                    if not lemma or len(word) not in range(8,31): continue
                    family = str(lemma)
                    bucket = int(hashlib.sha256((SEED+family).encode()).hexdigest()[:8],16)%5
                    assigned = 'train' if bucket < 2 else 'calibration' if bucket == 2 else 'holdout'
                    if assigned != part: continue
                    old = pools[part].get(family)
                    if old is None or item['selectionHash'] < old['selectionHash']:
                        pools[part][family] = dict(item, family=family, article=str(article), shard=shard)
        print(f'SOURCE_COMPLETE:{shard}:{part}:{len(pools[part])}', flush=True)
    for a,b in [('train','calibration'),('train','holdout'),('calibration','holdout')]:
        if article_sets[a] & article_sets[b] or pools[a].keys() & pools[b].keys(): raise ValueError('SPLIT_OVERLAP')
    output.mkdir(parents=True)
    counts = {}
    for part, pool in pools.items():
        quota = 500 if part == 'calibration' else 1000
        ordered = sorted(pool.values(), key=lambda x: hashlib.sha256((SEED+x['family']).encode()).digest())
        rows = []
        for group in GROUPS:
            selected = 0
            for item in ordered:
                typed = typo(item['word'], group, part, dictionary)
                if typed is None: continue
                rows.append(dict(item, typed=typed, prefix=item['prefix'], expected=item['word'],
                    group=group, split=part, id=f'{part}-{group}-{selected}', noAuto=False))
                selected += 1
                if selected == quota: break
            if selected != quota: raise ValueError(f'INSUFFICIENT_POOL:{part}:{group}:{selected}')
        # Valid originals and protected tokens have explicit keep-original labels.
        if len(ordered) < quota: raise ValueError('CONTROL_POOL')
        for i,item in enumerate(ordered[:quota]):
            for protected in (False,True):
                typed = item['word'] + ('42' if protected else '')
                rows.append(dict(item, typed=typed, expected=typed, group='protected' if protected else 'correct',
                    split=part, id=f'{part}-control-{i}-{int(protected)}', noAuto=True))
        jsonl(output/f'{part}.jsonl',rows)
        counts[part] = dict(Counter(row['group'] for row in rows))
    write(output/'manifest.json',dict(schema=1, seed=SEED, publicOnly=True, sources=bindings,
        morphology=digest(MORPH), frequency=digest(FREQUENCY), context=digest(CONTEXT),
        generator=digest(__file__), counts=counts,
        files={f'{part}.jsonl':digest(output/f'{part}.jsonl') for part in pools}))

def replay(corpus, part, output, mode="recovery"):
    import importlib.util
    spec=importlib.util.spec_from_file_location('replay',ROOT/'tools/eval/smart-typing-0.3/pipeline/final_product_replay.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    manifest=json.loads((corpus/'manifest.json').read_text()); rows_path=corpus/f'{part}.jsonl'
    if digest(rows_path)!=manifest['files'][rows_path.name]: raise ValueError('ROWS_DRIFT')
    rows=read(rows_path); output.mkdir(parents=True,exist_ok=False)
    java=Path(os.environ['JAVA_HOME'])/'bin/java'
    sources,jars,android=module.compile_inputs(java)
    jar,command=module.compile_harness(output,java,sources,jars,android)
    b64=lambda s:base64.b64encode(s.encode()).decode()
    inputs=output/'inputs.tsv'
    inputs.write_text(''.join(f"{i}\t{b64(r['id'])}\t{r['split']}\tru\t{b64(r['prefix'])}\t{b64(r['typed'])}\n" for i,r in enumerate(rows)))
    module.run_harness(output,java,jars,android,jar,inputs,output/'observations.jsonl',mode)
    write(output/'receipt.json',dict(rows=digest(rows_path),corpus=digest(corpus/'manifest.json'),jar=digest(jar),
        observations=digest(output/'observations.jsonl'),sources={str(p.relative_to(ROOT)):digest(p) for p in sources},
        assets={str(p.relative_to(ROOT)):digest(p) for p in [*module.asset_paths(),*module.compact_asset_paths()]},
        command=command))

def groups(corpus, part, replay_dir):
    receipt = json.loads((replay_dir/'receipt.json').read_text())
    if receipt['rows'] != digest(corpus/f'{part}.jsonl') or receipt['observations'] != digest(replay_dir/'observations.jsonl'):
        raise ValueError('REPLAY_IDENTITY')
    for section in ('sources','assets'):
        if any(digest(ROOT/path) != value for path,value in receipt[section].items()):raise ValueError('REPLAY_BINDING_DRIFT')
    rows = read(corpus/f'{part}.jsonl'); observations = read(replay_dir/'observations.jsonl')
    if len(rows) != len(observations): raise ValueError('REPLAY_LENGTH')
    import abstaining_ranker as ranker
    result = []
    for row, observed in zip(rows,observations):
        if observed.get('id') != row['id'] or observed.get('status') != 'COMPLETE': raise ValueError('REPLAY_ROW')
        recovery = observed['fullTokenGeneration']['neighborRecovery']
        candidates = [ranker.original_candidate(row)] + recovery['alternatives']
        baseline = observed['afterBoundary']['text'].rstrip().split()[-1]
        matches = [i for i,c in enumerate(candidates) if c['text'] == row['expected']]
        target = matches[0] if matches and not row['noAuto'] else 0
        result.append(dict(row=row,candidates=candidates,target=target,baseline=baseline,
            complete=recovery['completion']=='COMPLETE',admitted=observed['recoveryAdmission']))
    return result

def records(weights, data):
    import abstaining_ranker as ranker
    import neural_refinement as neural
    from functools import lru_cache
    import math
    model = neural.load_model(CONTEXT)
    blob = weights.read_bytes()
    @lru_cache(maxsize=32768)
    def context_score(prefix,word): return neural.context_score(model,prefix,word)
    result = []
    for group in data:
        row = group['row']
        if len(group['candidates']) < 2 or not group['complete'] or group['baseline'] != row['typed']: continue
        scores = [.8*math.tanh(ranker.rank.tree_score(blob,ranker.rank.features(row['prefix'],row['typed'],c))/4)
            +context_score(row['prefix'],c['text']) for c in group['candidates']]
        order = sorted(range(len(scores)),key=lambda i:(-scores[i],i))
        best=order[0]; candidate=group['candidates'][best]['text']
        if best == 0 or not group['admitted'].get(candidate): continue
        result.append(dict(id=row['id'], family=row['family'], group=row['group'],
            topScore=scores[best],margin=scores[best]-scores[order[1]],candidate=candidate,
            correct=not row['noAuto'] and candidate==row['expected'],control=row['noAuto']))
    return result

def calibrate(records):
    import math
    best=None
    for score in sorted({r['topScore'] for r in records},reverse=True):
        eligible=[r for r in records if r['topScore']>=score]
        bad=[r['margin'] for r in eligible if not r['correct'] or r['control']]
        margin=math.nextafter(max([0.0,*bad]),math.inf)
        chosen=[r for r in eligible if r['margin']>=margin]
        key=(len(chosen),margin,score)
        if chosen and (best is None or key>best[0]):best=(key,score,margin)
    if best is None:return None
    return dict(minimumScore=best[1],minimumMargin=best[2])

def train(corpus, train_replay, calibration_replay, output):
    import abstaining_ranker as ranker
    if output.exists():raise ValueError('FRESH_OUTPUT_REQUIRED')
    output.mkdir(parents=True)
    training=groups(corpus,'train',train_replay)
    development=groups(corpus,'calibration',calibration_replay)
    weights=output/'ru-neighbor-ranker.bin'
    ranker.fit([g for g in training if len(g['candidates'])>=2],weights)
    measured=records(weights,development)
    jsonl(output/'calibration-records.jsonl',measured)
    policy=calibrate(measured)
    write(output/'frozen-policy.json',dict(schema=1, policy=policy, rankerSha256=digest(weights),
        contextSha256=digest(CONTEXT), corpusSha256=digest(corpus/'manifest.json'),
        trainReceipt=digest(train_replay/'receipt.json'), calibrationReceipt=digest(calibration_replay/'receipt.json'),
        toolSha256=digest(__file__), frozenBeforeHoldout=True))
    print('CALIBRATION_COMPLETE:'+str(policy is not None),flush=True)

def evaluate(corpus, holdout_replay, frozen, output):
    policy=json.loads((frozen/'frozen-policy.json').read_text())
    weights=frozen/'ru-neighbor-ranker.bin'
    if policy['rankerSha256']!=digest(weights) or policy['contextSha256']!=digest(CONTEXT) or policy['corpusSha256']!=digest(corpus/'manifest.json'):
        raise ValueError('FROZEN_ARTIFACT_DRIFT')
    if output.exists():raise ValueError('FRESH_OUTPUT_REQUIRED')
    data=groups(corpus,'holdout',holdout_replay)
    measured=records(weights,data); thresholds=policy['policy']
    selected=[] if thresholds is None else [r for r in measured if r['topScore']>=thresholds['minimumScore'] and r['margin']>=thresholds['minimumMargin']]
    counts=Counter(r['group'] for r in selected if r['correct'])
    incorrect=sum(not r['correct'] for r in selected); controls=sum(r['control'] for r in selected)
    passed=thresholds is not None and not incorrect and not controls and sum(counts.values())>=100 and all(counts[g]>=25 for g in GROUPS)
    write(output,dict(schema=1,passed=passed,correctAdditions=sum(counts.values()),correctByGroup=dict(counts),
        incorrectAdditions=incorrect,controlChanges=controls,rows=len(data),
        frozenPolicySha256=digest(frozen/'frozen-policy.json'),replayReceiptSha256=digest(holdout_replay/'receipt.json'),
        selected=selected))
    print('HOLDOUT_PASS' if passed else 'HOLDOUT_REFUSED',flush=True)
    return passed

def main():
    parser=argparse.ArgumentParser(); sub=parser.add_subparsers(dest='command',required=True)
    prep=sub.add_parser('prepare');prep.add_argument('output',type=Path)
    rep=sub.add_parser('replay');rep.add_argument('corpus',type=Path);rep.add_argument('part',choices=['train','calibration','holdout']);rep.add_argument('output',type=Path);rep.add_argument('--mode',choices=['recovery','refinement-export'],default='recovery')
    tr=sub.add_parser('train')
    for name in ['corpus','train_replay','calibration_replay','output']:tr.add_argument(name,type=Path)
    ev=sub.add_parser('evaluate')
    for name in ['corpus','holdout_replay','frozen','output']:ev.add_argument(name,type=Path)
    args=parser.parse_args()
    if args.command=='prepare':prepare(args.output)
    elif args.command=='replay':replay(args.corpus,args.part,args.output,args.mode)
    elif args.command=='train':train(args.corpus,args.train_replay,args.calibration_replay,args.output)
    else:sys.exit(0 if evaluate(args.corpus,args.holdout_replay,args.frozen,args.output) else 2)

if __name__=='__main__':main()
