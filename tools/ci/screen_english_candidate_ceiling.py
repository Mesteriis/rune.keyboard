#!/usr/bin/env python3
"""Screen candidate availability in the disclosed Q7 replay, never qualify a model."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

import generate_product_replay_v1 as corpus
import product_replay_ci

ROOT = Path(__file__).resolve().parents[2]
KINDS = {1: 'delete-middle', 2: 'transpose-first'}


def screen(inputs, origins, observations):
    if len(inputs) != len(observations) or len(inputs) != 4 * len(origins):
        raise ValueError('EN_SCREEN_COUNT')
    result = {name: Counter() for name in KINDS.values()}
    for index, (row, obs) in enumerate(zip(inputs, observations, strict=True)):
        origin = origins[index // 4]
        if (origin.get('group') != index // 4 or row.get('language') != origin.get('language') or
                obs.get('index') != index or any(obs.get(k) != row.get(k) for k in ('language', 'prefix', 'typed', 'split'))):
            raise ValueError('EN_SCREEN_ALIGNMENT')
        target = origin['target']['word']
        if (row['typed'] != corpus.variants(target)[index % 4] or
                row['prefix'] != ' '.join(item['word'] for item in origin['context'])):
            raise ValueError('EN_SCREEN_TRANSFORM')
        kind = KINDS.get(index % 4)
        if row['language'] != 'en' or kind is None:
            continue
        if row['typed'] == target:
            result[kind]['unchangedTransform'] += 1
            continue
        generation = obs.get('fullTokenGeneration')
        if not isinstance(generation, dict) or generation.get('original') != row['typed']:
            raise ValueError('EN_SCREEN_GENERATION')
        completion = generation.get('completion')
        blocked = generation.get('prohibitsAutoReplace')
        candidates = generation.get('alternatives')
        if (completion not in ('COMPLETE', 'STATES_EXHAUSTED', 'VERIFIED_EXHAUSTED', 'VALID_WORD', 'UNAVAILABLE') or
                type(blocked) is not bool or not isinstance(candidates, list) or
                any(not isinstance(c, dict) or not isinstance(c.get('text'), str) or not isinstance(c.get('language'), str)
                    for c in candidates)):
            raise ValueError('EN_SCREEN_GENERATION')
        seen = any(c['language'] == 'en' and c['text'].casefold() == target.casefold() for c in candidates)
        stats = result[kind]
        stats['changedTransforms'] += 1
        stats['completion:' + completion] += 1
        stats['targetInAlternatives'] += int(seen)
        stats['targetSeenAndSearchAllowsAuto'] += int(seen and not blocked)
        stats['targetSeenButSearchProhibitsAuto'] += int(seen and blocked)
        stats['targetAbsent'] += int(not seen)
    return {name: dict(sorted(counts.items())) for name, counts in result.items()}


def run():
    data = corpus.DATA
    paths = [data / name for name in ('inputs.jsonl', 'origins.jsonl', 'manifest.json',
                                     'baseline.jsonl.gz', 'baseline-manifest.json')]
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    meta = product_replay_ci.validate()
    inputs = [json.loads(line) for line in paths[0].read_bytes().splitlines()]
    origins = [json.loads(line) for line in paths[1].read_bytes().splitlines()]
    with gzip.open(paths[3], 'rt', encoding='utf-8') as stream:
        observations = [json.loads(line) for line in stream]
    counts = screen(inputs, origins, observations)
    if any(hashlib.sha256(p.read_bytes()).hexdigest() != digest for p, digest in before.items()):
        raise ValueError('EN_SCREEN_INPUT_DRIFT')
    return dict(schemaVersion=1, scope='disclosed-synthetic-diagnostic-not-qualification',
                sourceCaptureCommit=meta['capturedSourceCommit'],
                projectionSha256=meta['projectionSha256'],
                inputs={str(p.relative_to(ROOT)): h for p, h in before.items()},
                analyzerSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                counts=counts, targetMeaning='frequency-list source surface, not a verified correction',
                contextMeaning='adjacent frequency-list entries, not a natural sentence',
                qualification=False, modelCalls=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'):
        raise ValueError('EN_SCREEN_OUTPUT')
    result = run()
    output.write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps(result['counts'], sort_keys=True))


if __name__ == '__main__':
    main()
