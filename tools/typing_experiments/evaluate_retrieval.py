#!/usr/bin/env python3
"""Compare actual bounded candidate pools with unchanged shipped manual scorers."""
from pathlib import Path
import argparse
from collections import Counter
import json
import math
import retrieval_evaluation_receipt as binding
from export_retrieval import support

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'app/src/main/assets/smarttyping/experiments'


def load_scoring():
    global rank, neural
    import rank_refinement as rank
    import neural_refinement as neural


def verify_export(directory):
    receipt_path = directory / 'receipt.json'
    receipt = json.loads(receipt_path.read_text())
    support.require(receipt.get('scope') == 'host-production-manual-retrieval', 'EXPORT_SCOPE')
    for name in ('rows.jsonl', 'observations.jsonl', 'source-freeze.json', 'inputs.tsv'):
        path = directory / name
        support.require(receipt['files'].get(str(path.resolve())) == support.sha(path), 'CONSUMED_FILE_BINDING')
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
    load_scoring()
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
    support.require(selection['freshManifestSha256'] == support.sha(manifest_path), 'FRESH_MANIFEST_IDENTITY')
    row_path = manifest_path.parent / 'test-rows.jsonl'
    support.require(manifest.get('containsPersonalMessages') is False and
        manifest['files'][row_path.name] == support.sha(row_path) and support.read_jsonl(row_path) == rows, 'FRESH_ROWS_IDENTITY')
    lock = json.loads((ROOT / 'tools/model/rune-text-0.2/source-lock.json').read_text())
    support.require(manifest['sourceSha256'] == lock['wikipediaContext']['files']['ru-0007.parquet']['sha256'], 'PUBLIC_SOURCE_IDENTITY')
    support.require(set(map(str, (r['articleId'] for r in rows))).issubset(set(manifest['articles'])), 'FRESH_ARTICLES')
    return support.sha(selection_path)


def run(directory,output,historical_reproduction=False,manifest_path=None,selection_path=None):
    frozen=binding.freeze(directory,historical_reproduction,ROOT,manifest_path,selection_path)
    output=Path(output).resolve()
    support.require(output.is_relative_to(ROOT/'build') and not output.exists() and not output.is_symlink(),
                    'FRESH_BUILD_OUTPUT_REQUIRED')
    load_scoring()
    import promote_refinement as promotion
    promotion.validate_tree((ASSETS/'ru-ranker.bin').read_bytes(),rank.FEATURES)
    result=summarize(frozen['rows'],frozen['observations'])
    result.update(schema=1,exportReceiptSha256=frozen['receipt']['exportReceiptSha256'],
        evaluationScriptSha256=support.sha(Path(__file__)),selectionSha256=frozen['receipt']['selectionSha256'],
        modelHashes=frozen['receipt']['modelHashes'],
        scope='Public synthetic manual suggestions, original separate; personal/touch scores zero; no model retraining; host latency excludes scoring/editor/render/loading; correct controls assess supplemental pool and existing local policy only')
    binding.finish_report(frozen,result)
    support.write_json(output,result)
    print(json.dumps(result,ensure_ascii=False));return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--fresh-manifest',type=Path)
    parser.add_argument('--selection',type=Path)
    parser.add_argument('--historical-reproduction',action='store_true')
    args=parser.parse_args()
    run(args.export,args.output,args.historical_reproduction,args.fresh_manifest,args.selection)


if __name__ == '__main__':
    main()
