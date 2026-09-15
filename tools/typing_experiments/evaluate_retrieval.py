#!/usr/bin/env python3
"""Compare actual bounded candidate pools with unchanged shipped manual scorers."""
from pathlib import Path
import argparse
from collections import Counter
import json
import math
import numpy as np
import rank_refinement as rank
import neural_refinement as neural
from export_retrieval import support

ROOT = rank.ROOT
ASSETS = ROOT / 'app/src/main/assets/smarttyping/experiments'


def verify_export(directory):
    receipt_path = directory / 'receipt.json'
    receipt = json.loads(receipt_path.read_text())
    support.require(receipt.get('scope') == 'host-production-manual-retrieval', 'EXPORT_SCOPE')
    for name in ('rows.jsonl', 'observations.jsonl', 'source-freeze.json', 'inputs.tsv'):
        path = directory / name
        support.require(receipt['files'].get(str(path.resolve())) == rank.sha(path), 'CONSUMED_FILE_BINDING')
    support.verify_bindings(receipt['sources'])
    support.verify_bindings(receipt['files'])
    rows = support.read_jsonl(directory / 'rows.jsonl')
    observations = support.read_jsonl(directory / 'observations.jsonl')
    support.validate_rows(rows)
    support.verify_observations(rows, observations)
    return rows, observations


def percentile(values):
    if not values:
        return None
    a = sorted(values)
    return {name: a[min(len(a)-1, math.ceil(q*len(a))-1)] for name, q in [('p50Ms', .5), ('p95Ms', .95), ('maxMs', 1)]}


def ordered(scores):
    return sorted(range(len(scores)), key=lambda i: -scores[i])


def aggregate(records):
    result = {'rows': len(records), 'baseline': {}, 'expanded': {}}
    for name in ('baseline', 'expanded'):
        result[name] = {key: sum(r[name][key] for r in records) for key in
            ('anyAlternatives', 'goldAvailable', 'treeTop1', 'combinedTop1', 'combinedTop2', 'combinedTop3')}
    return result


def summarize(rows, observations):
    tree = ASSETS / 'ru-ranker.bin'
    context = neural.load_model(ASSETS / 'ru-ranking-context.bin')
    # Score the union once per query; this mirrors one inference per candidate per UI projection.
    records = []
    controls = Counter()
    completions = Counter()
    for row, obs in zip(rows, observations, strict=True):
        baseline = obs['generation']['alternatives']
        manual = obs['manual']
        expanded = manual['alternatives'] if manual is not None else baseline
        support.require(len(expanded) <= 7 and len({c['canonicalKey'] for c in expanded}) == len(expanded), 'POOL_BOUND')
        support.require({c['canonicalKey'] for c in baseline}.issubset({c['canonicalKey'] for c in expanded}), 'BASELINE_LOST')
        for generation in (obs['generation'], manual):
            if generation is not None:
                support.require(0 <= generation['inspectedStates'] <= 8192 and
                    0 <= generation['verifiedTerminals'] <= 64, 'SEARCH_BUDGET')
        completions['baseline:' + obs['generation']['completion']] += 1
        completions['manual:' + (manual['completion'] if manual else 'NONE')] += 1
        if row['cohort'] == 'correct':
            support.require(row['typed'] == row['expectedSpelling'] and row['noAuto'], 'CONTROL_MUTATED')
            controls['rows'] += 1
            controls['supplementalChanges'] += int(expanded != baseline)
            controls['localAutomaticProposals'] += int(obs['baseline'] is not None)
            continue
        support.require(row['cohort'] == 'typo' and not row['noAuto'], 'TYPO_SCOPE')
        values = rank.scores(tree, [(row, expanded, None)])[0] if expanded else []
        combined = [v + neural.context_score(context, row['prefix'], c['text']) for v, c in zip(values, expanded)]
        lookup = {c['canonicalKey']: (v, n) for c, v, n in zip(expanded, values, combined)}
        target = row['expectedSpelling'].lower()
        record = {'errorCount': row['errorCount']}
        for name, candidates in [('baseline', baseline), ('expanded', expanded)]:
            tree_order = ordered([lookup[c['canonicalKey']][0] for c in candidates])
            combined_order = ordered([lookup[c['canonicalKey']][1] for c in candidates])
            gold = [c['text'].lower() == target for c in candidates]
            record[name] = dict(anyAlternatives=bool(candidates), goldAvailable=any(gold),
                treeTop1=any(gold[i] for i in tree_order[:1]),
                combinedTop1=any(gold[i] for i in combined_order[:1]),
                combinedTop2=any(gold[i] for i in combined_order[:2]),
                combinedTop3=any(gold[i] for i in combined_order[:3]))
        records.append(record)
    return dict(cohorts={'all': aggregate(records), **{str(n): aggregate([r for r in records if r['errorCount'] == n]) for n in (1, 2, 3)}},
        correctControls=dict(controls), completions=dict(completions),
        hostLatency={'baseline': percentile([o['generationMs'] for o in observations]),
            'manualAdditional': percentile([o['manualMs'] for o in observations]),
            'total': percentile([o['generationMs'] + o['manualMs'] for o in observations])})


def verify_fresh(rows, manifest_path, selection_path):
    manifest = json.loads(manifest_path.read_text())
    selection = json.loads(selection_path.read_text())
    support.require(selection.get('frozenBeforeFreshEvaluation') is True, 'FROZEN_SELECTION_REQUIRED')
    support.verify_bindings(selection['files'])
    support.require(selection['freshManifestSha256'] == rank.sha(manifest_path), 'FRESH_MANIFEST_IDENTITY')
    row_path = manifest_path.parent / 'test-rows.jsonl'
    support.require(manifest.get('containsPersonalMessages') is False and
        manifest['files'][row_path.name] == rank.sha(row_path) and support.read_jsonl(row_path) == rows, 'FRESH_ROWS_IDENTITY')
    lock = json.loads((ROOT / 'tools/model/rune-text-0.2/source-lock.json').read_text())
    support.require(manifest['sourceSha256'] == lock['wikipediaContext']['files']['ru-0007.parquet']['sha256'], 'PUBLIC_SOURCE_IDENTITY')
    support.require(set(map(str, (r['articleId'] for r in rows))).issubset(set(manifest['articles'])), 'FRESH_ARTICLES')
    return rank.sha(selection_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--export', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fresh-manifest', type=Path)
    parser.add_argument('--selection', type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    support.require(output.is_relative_to(ROOT / 'build') and not output.exists(), 'FRESH_BUILD_OUTPUT_REQUIRED')
    rows, observations = verify_export(args.export.resolve())
    selection_hash = None
    if args.fresh_manifest or args.selection:
        support.require(args.fresh_manifest is not None and args.selection is not None, 'FRESH_BINDINGS_REQUIRED')
        selection_hash = verify_fresh(rows, args.fresh_manifest, args.selection)
    result = summarize(rows, observations)
    result.update(schema=1, exportReceiptSha256=rank.sha(args.export / 'receipt.json'),
        evaluationScriptSha256=rank.sha(Path(__file__)), selectionSha256=selection_hash,
        modelHashes={p.name: rank.sha(p) for p in (ASSETS / 'ru-ranker.bin', ASSETS / 'ru-ranking-context.bin')},
        scope='Public synthetic manual suggestions, original separate; personal/touch scores zero; no model retraining; host latency excludes scoring/editor/render/loading; correct controls assess supplemental pool and existing local policy only')
    support.write_json(output, result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
