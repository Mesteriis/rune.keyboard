"""Analyze disclosed neighbor label mismatches without changing policy."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/ci'))
import register_neighbor_observed as observed_fixture


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def selected_rows():
    observed, _ = observed_fixture.inputs()
    source = [json.loads(line) for line in (observed_fixture.DATA / 'holdout.jsonl').read_bytes().splitlines()]
    indexed = {row['id']: row for row in source}
    return [(dict(indexed[item['sourceId']], language='ru'), item) for item in observed
            if indexed[item['sourceId']]['group'] not in ('correct', 'protected')
            and item['typed'] != indexed[item['sourceId']]['expected']]


def analyze(pairs, observations):
    counts = Counter()
    seen = set()
    for (row, disclosed), obs in zip(pairs, observations, strict=True):
        rid, target = row.get('id'), row.get('expected')
        if (not isinstance(rid, str) or not rid or rid in seen or obs.get('id') != rid or
                obs.get('status') != 'COMPLETE' or not isinstance(target, str) or not target or
                disclosed.get('sourceId') != rid):
            raise ValueError('NEIGHBOR_RANKING_IDENTITY')
        seen.add(rid)
        before = obs.get('beforeBoundary', {}).get('text')
        after = obs.get('afterBoundary', {}).get('text')
        if (not isinstance(before, str) or not before.endswith(row['typed']) or
                after != disclosed['prefix'] + ' ' + disclosed['typed'] + ' ' or
                after == before + ' ' or obs.get('afterBackspace', {}).get('text') != before):
            raise ValueError('NEIGHBOR_RANKING_EDITOR')
        generation = (obs.get('autoEdit') or {}).get('correctionGeneration') or {}
        candidates = generation.get('alternatives')
        selected = obs.get('automaticAdmissionCandidate')
        pool = (obs.get('jointSearch') or {}).get('alternatives')
        scores = obs.get('jointModelScores')
        admissions = obs.get('jointSourceAdmission')
        refusals = obs.get('jointSourceRefusals')
        if (not isinstance(candidates, list) or not isinstance(pool, list) or not isinstance(scores, list) or
                len(scores) != len(pool) + 1 or any(type(s) not in (int, float) or not math.isfinite(s) for s in scores) or
                not isinstance(admissions, dict) or not isinstance(refusals, dict) or not isinstance(selected, str)):
            raise ValueError('NEIGHBOR_RANKING_SHAPE')
        names = [item.get('text') for item in pool]
        if any(not isinstance(name, str) or not name for name in names) or len(set(names)) != len(names):
            raise ValueError('NEIGHBOR_RANKING_POOL')
        selected_candidates = [item for item in candidates if item.get('text') == selected]
        if len(selected_candidates) != 1 or type(selected_candidates[0].get('unitDistance')) is not int:
            raise ValueError('NEIGHBOR_RANKING_SELECTED')
        counts['rows'] += 1
        counts['target_in_correction_pool'] += any(item.get('text') == target for item in candidates)
        counts['selected_distance_' + str(selected_candidates[0]['unitDistance'])] += 1
        if target not in names:
            counts['target_missing_from_joint_pool'] += 1
            continue
        counts['target_in_joint_pool'] += 1
        allowed, refusal = admissions.get(target), refusals.get(target)
        if type(allowed) is not bool or (allowed and refusal is not None) or (not allowed and not isinstance(refusal, str)):
            raise ValueError('NEIGHBOR_RANKING_ADMISSION')
        counts['hypothetical_target_admitted' if allowed else 'hypothetical_target_refused_' + refusal] += 1
        target_index = names.index(target) + 1
        order = sorted(range(len(scores)), key=lambda i: (-scores[i], i))
        if order[0] == target_index:
            counts['target_highest_raw_joint_score'] += 1
            counts['target_highest_raw_score_and_admitted'] += allowed
        if selected in names and scores[target_index] > scores[names.index(selected) + 1]:
            counts['target_score_above_selected'] += 1
    if not seen:
        raise ValueError('NEIGHBOR_RANKING_EMPTY')
    return dict(sorted(counts.items()))


def run(rows_path, observation_path, receipt_path, output):
    paths = [Path(rows_path), Path(observation_path), Path(receipt_path)]
    raw = [path.read_bytes() for path in paths]
    receipt = json.loads(raw[2])
    pairs = selected_rows()
    rows = [json.loads(line) for line in raw[0].splitlines()]
    observations = [json.loads(line) for line in raw[1].splitlines()]
    if (rows != [row for row, _ in pairs] or receipt.get('mode') != 'current-product' or
            receipt.get('status') != 'COMPLETE' or receipt.get('exitCode') != 0 or
            receipt.get('rowsSha256') != sha(raw[0]) or receipt.get('observationsSha256') != sha(raw[1])):
        raise ValueError('NEIGHBOR_RANKING_BINDING')
    counts = analyze(pairs, observations)
    if any(path.read_bytes() != value for path, value in zip(paths, raw, strict=True)):
        raise ValueError('NEIGHBOR_RANKING_DRIFT')
    report = dict(scope='disclosed-historical-neighbor-diagnostic', independentQualification=False,
                  historicalSourceLabelsQualified=False, policyChanged=False, counts=counts,
                  rowsSha256=sha(raw[0]), observationsSha256=sha(raw[1]), replayReceiptSha256=sha(raw[2]),
                  analyzerSha256=sha(Path(__file__).read_bytes()))
    output = Path(output)
    if output.exists() or not output.resolve().is_relative_to(ROOT / 'build'):
        raise ValueError('NEIGHBOR_RANKING_OUTPUT')
    output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps(counts, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ('rows', 'observations', 'receipt', 'output'):
        parser.add_argument('--' + field, type=Path, required=True)
    args = parser.parse_args()
    run(args.rows, args.observations, args.receipt, args.output)
