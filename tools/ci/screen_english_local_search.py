#!/usr/bin/env python3
"""Screen a completed local pool when the disclosed wider search exhausts."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

import generate_product_replay_v1 as corpus
import product_replay_ci
import screen_english_candidate_ceiling as baseline

ROOT = Path(__file__).resolve().parents[2]


def screen(inputs, origins, observations):
    baseline.screen(inputs, origins, observations)  # Verify group, transform and replay alignment first.
    counts = {name: Counter() for name in baseline.KINDS.values()}
    for index, (row, obs) in enumerate(zip(inputs, observations, strict=True)):
        kind = baseline.KINDS.get(index % 4)
        if row['language'] != 'en' or kind is None:
            continue
        target = origins[index // 4]['target']['word']
        if row['typed'] == target:
            continue
        generation = obs['fullTokenGeneration']
        if generation['completion'] != 'STATES_EXHAUSTED':
            continue
        local = generation.get('localSearch')
        if (not isinstance(local, dict) or local.get('completion') not in
                ('COMPLETE', 'STATES_EXHAUSTED', 'VERIFIED_EXHAUSTED', 'UNAVAILABLE', 'CANCELLED', 'READER_FAILURE') or
                not isinstance(local.get('alternatives'), list) or
                any(not isinstance(c, dict) or not isinstance(c.get('language'), str) or
                    not isinstance(c.get('text'), str) for c in local['alternatives'])):
            raise ValueError('EN_LOCAL_SEARCH_SCHEMA')
        alternatives = local['alternatives']
        matches = [i for i, c in enumerate(alternatives)
                   if c['language'] == 'en' and c['text'].casefold() == target.casefold()]
        stats = counts[kind]
        stats['widerSearchExhausted'] += 1
        stats['localCompletion:' + local['completion']] += 1
        if local['completion'] != 'COMPLETE':
            continue
        stats['targetInCompleteLocalPool'] += int(bool(matches))
        stats['targetFirstInCompleteLocalPool'] += int(matches == [0])
        stats['targetOnlyInCompleteLocalPool'] += int(bool(matches) and len(alternatives) == 1)
        stats['targetWithCompetitorsInCompleteLocalPool'] += int(bool(matches) and len(alternatives) > 1)
        stats['targetAbsentFromCompleteLocalPool'] += int(not matches)
    return {name: dict(sorted(value.items())) for name, value in counts.items()}


def run():
    data = corpus.DATA
    paths = [data / name for name in ('inputs.jsonl', 'origins.jsonl', 'manifest.json',
                                     'baseline.jsonl.gz', 'baseline-manifest.json')]
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    meta = product_replay_ci.validate()
    rows = [json.loads(line) for line in paths[0].read_bytes().splitlines()]
    origins = [json.loads(line) for line in paths[1].read_bytes().splitlines()]
    with gzip.open(paths[3], 'rt', encoding='utf-8') as stream:
        observations = [json.loads(line) for line in stream]
    counts = screen(rows, origins, observations)
    if any(hashlib.sha256(p.read_bytes()).hexdigest() != digest for p, digest in before.items()):
        raise ValueError('EN_LOCAL_INPUT_DRIFT')
    return dict(schemaVersion=1, scope='disclosed-synthetic-diagnostic-not-qualification',
                sourceCaptureCommit=meta['capturedSourceCommit'], projectionSha256=meta['projectionSha256'],
                inputs={str(p.relative_to(ROOT)): digest for p, digest in before.items()},
                analyzerSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                parentAnalyzerSha256=hashlib.sha256(Path(baseline.__file__).read_bytes()).hexdigest(),
                counts=counts, targetMeaning='frequency-list source surface, not a verified correction',
                contextMeaning='adjacent frequency-list entries, not a natural sentence',
                qualification=False, modelCalls=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    output = parser.parse_args().output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'):
        raise ValueError('EN_LOCAL_OUTPUT')
    result = run()
    output.write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps(result['counts'], sort_keys=True))


if __name__ == '__main__':
    main()
