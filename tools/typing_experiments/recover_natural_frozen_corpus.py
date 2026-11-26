"""Rebuild the historical Natural Frozen corpus from its seven exact local pools."""

import argparse
import base64
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from audit_frozen_context_descendants import SPECS, verify_variants
from recover_available_v6_articles import ROOT

METADATA = ROOT / 'tools/typing_experiments/historical_provenance_sources/v6-inputs'
SPEC = SPECS['natural-frozen']
PARTS = ('calibration', 'holdout')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_metadata():
    plan = (METADATA / 'natural-frozen-plan.json').read_bytes()
    manifest = (METADATA / 'natural-frozen-manifest.json').read_bytes()
    if digest(plan) != SPEC['planSha256'] or digest(manifest) != SPEC['manifestSha256']:
        raise ValueError('NATURAL_FROZEN_METADATA_DIGEST')
    return plan, manifest


def select(pool_dir, plan, manifest):
    articles, contexts = set(), set()
    families = defaultdict(list)
    duplicates = 0
    for path, expected in plan['sourceHashes'].items():
        name = Path(path).parent.name
        raw = (pool_dir / (name + '.jsonl')).read_bytes()
        if digest(raw) != expected:
            raise ValueError('NATURAL_FROZEN_POOL_DIGEST:' + name)
        for item in map(json.loads, raw.splitlines()):
            if item['article'] in articles:
                raise ValueError('NATURAL_FROZEN_DUPLICATE_ARTICLE')
            articles.add(item['article'])
            if item['contextHash'] in contexts:
                duplicates += 1
                continue
            contexts.add(item['contextHash'])
            families[item['family']].append(item)
    if duplicates != manifest['duplicateContextsExcluded']:
        raise ValueError('NATURAL_FROZEN_DUPLICATE_COUNT')
    if families.keys() & set(manifest['excludedOriginalTrainingFamilies']):
        raise ValueError('NATURAL_FROZEN_TRAINING_OVERLAP')

    selected = {part: [] for part in PARTS}
    for records in families.values():
        for row in sorted(records, key=lambda r: r['selectionHash'])[:plan['maximumContextsPerFamily']]:
            selected[row['provisionalSplit']].append(row)
    return {part: sorted(rows, key=lambda r: r['selectionHash'])[:plan['contextsPerPart']]
            for part, rows in selected.items()}


def variants(part, items):
    rows = []
    for item in items:
        choices = [(item['typed'], 'typo', False), (item['word'], 'correct', True),
                   (item['rival'], 'correct_rival', True), ('@' + item['word'], 'protected', True)]
        for typed, kind, control in choices:
            rows.append(dict(item, id=f'right-natural-{part}-{len(rows):06d}', language='ru',
                             split=part, typed=typed, expectedSpelling=typed if control else item['word'],
                             noAuto=control, cohort='correct' if control else 'typo', group=kind,
                             sourceSentenceUrl='https://ru.wikipedia.org/?curid=' + item['article']))
    return rows


def encode(value):
    return base64.b64encode(value.encode()).decode()


def recover(pool_dir):
    plan_bytes, manifest_bytes = read_metadata()
    plan, manifest = json.loads(plan_bytes), json.loads(manifest_bytes)
    selected = select(pool_dir, plan, manifest)
    payloads = {}
    for part, items in selected.items():
        rows = variants(part, items)
        captures = verify_variants(rows, natural=True)
        if (len(rows) != manifest['counts'][part]['rows']
                or len(captures) != manifest['counts'][part]['contexts']):
            raise ValueError('NATURAL_FROZEN_ROW_COUNTS:' + part)
        payloads[part + '.jsonl'] = ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows).encode()
        payloads[part + '.tsv'] = ''.join(
            '\t'.join([str(i), encode(r['id']), part, 'ru', encode(r['prefix']), encode(r['typed'])]) + '\n'
            for i, r in enumerate(rows)
        ).encode()
    if {name: digest(raw) for name, raw in payloads.items()} != manifest['files']:
        raise ValueError('NATURAL_FROZEN_PAYLOAD_DIGEST')
    return plan_bytes, manifest_bytes, payloads


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pool-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / 'build') or output.exists():
        parser.error('output must be a new directory inside the repository build directory')
    plan, manifest, payloads = recover(args.pool_dir)
    corpus = output / 'corpus'
    corpus.mkdir(parents=True, exist_ok=False)
    (output / 'plan.json').write_bytes(plan)
    (corpus / 'manifest.json').write_bytes(manifest)
    for name, raw in payloads.items():
        (corpus / name).write_bytes(raw)
    report = json.loads(manifest)
    print(sum(part['rows'] for part in report['counts'].values()), 'exact historical rows')


if __name__ == '__main__':
    main()
