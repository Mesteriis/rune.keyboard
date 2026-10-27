"""Bootstrap durable exclusions from explicitly pinned public corpus receipts.

This imports six historical spelling corpora and the current right-context
corpus. It intentionally leaves historical article/canonical-family recovery,
other corpus imports and remaining generator-source archival pending. It cannot
mark the ledger complete or overwrite an existing snapshot.
"""
import argparse
import hashlib
import json
from pathlib import Path

from holdout_ledger import KEY_SCHEMA, KINDS, keys_for, validate_ledger

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def build_snapshot(root):
    root = Path(root)
    entries = []
    parent = root / 'build/right-context-sentence-pairs-v2-v6-20261027/plan.json'
    protected = json.loads(parent.read_text())['exclusionBindings']
    for version in range(7, 13):
        directory = root / f'build/typing-ranker-v2/external-holdout-v{version}-ru{version+5:04d}'
        manifest_path = directory / 'manifest.json'; rows_path = directory / 'rows.jsonl'
        manifest = json.loads(manifest_path.read_text())
        relative = str(rows_path.relative_to(root))
        digest = sha(rows_path)
        if (manifest.get('containsPersonalMessages') is not False or manifest.get('frozenBeforeScoring') is not True
                or manifest['source']['repository'] != 'https://huggingface.co/datasets/wikimedia/wikipedia'
                or digest != manifest['files']['rows.jsonl'] or digest != protected[relative]):
            raise ValueError('LEDGER_PUBLIC_SOURCE_BINDING')
        rows = [json.loads(line) for line in rows_path.read_text().splitlines()]
        if len(rows) != manifest['counts']['total']:
            raise ValueError('LEDGER_CORPUS_COUNT')
        for row in rows:
            if 'expectedSpelling' not in row:
                if row.get('cohort') != 'correct':
                    raise ValueError('LEDGER_LEGACY_TARGET_MISSING')
                row['expectedSpelling'] = row['typed']
        entries.append(dict(id=f'public-spelling-v{version}', usage='historical-exclusion',
            rowCount=len(rows), bindings={relative: digest,
                str(manifest_path.relative_to(root)): sha(manifest_path)},
            publicSource=manifest['source'],
            generatorBindings=manifest['sources'],
            generatorRuntime=manifest.get('generatorRuntime', {}),
            keys={'context': sorted(keys_for(rows, 'context'))},
            missingAxes=['article', 'family', 'sentence'],
            notes='Legacy rows lack article IDs; family strings are not certified as Pymorph lemmas.'))

    directory = root / 'build/right-context-available-clean-v6-20261027'
    manifest_path = directory / 'corpus/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    audit_path = directory / 'identity-audit.json'
    scoring_plan = root / 'build/right-context-v14-source6-traced-20261027/scoring-plan.json'
    plan = json.loads(scoring_plan.read_text())
    scoring_evidence = json.loads((root / 'docs/acceptance/2026-10-27-right-context-modal-source-evidence.json').read_text())
    available_plan_path = directory / 'plan.json'
    available_plan = json.loads(available_plan_path.read_text())
    relative_manifest = str(manifest_path.relative_to(root))
    if (sha(scoring_plan) != scoring_evidence['artifactHashes'][str(scoring_plan.relative_to(root))]
            or sha(manifest_path) != plan['inputSha256'][relative_manifest]
            or sha(available_plan_path) != manifest['planSha256']
            or sha(parent) != available_plan['parentPlanSha256']
            or sha(audit_path) != manifest['identityAuditSha256']
            or json.loads(audit_path.read_text()).get('passed') is not True):
        raise ValueError('LEDGER_RIGHT_CONTEXT_BINDING')
    for part, usage in [('calibration', 'disclosed'), ('holdout', 'reserved')]:
        path = directory / f'corpus/{part}.jsonl'
        if sha(path) != manifest['files'][path.name]:
            raise ValueError('LEDGER_RIGHT_CONTEXT_ROWS')
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        if len(rows) != manifest['counts'][part]['rows']:
            raise ValueError('LEDGER_CORPUS_COUNT')
        entries.append(dict(id=f'public-right-context-available-v6-{part}', usage=usage,
            rowCount=len(rows), bindings={str(p.relative_to(root)): sha(p)
                for p in (path, manifest_path, audit_path, parent, scoring_plan)},
            publicSource=dict(repository='https://huggingface.co/datasets/wikimedia/wikipedia',
                sourceBindings=json.loads(parent.read_text())['sourceBindings']),
            keys={kind: sorted(keys_for(rows, kind)) for kind in KINDS}, missingAxes=[]))

    prepared_path = root / 'build/right-context-oblique-v12-inputs-20261027/feature-preparation.json'
    evidence_path = root / 'docs/acceptance/2026-10-27-right-context-oblique-fit-evidence.json'
    prepared = json.loads(prepared_path.read_text())
    if sha(prepared_path) != json.loads(evidence_path.read_text())['artifactHashes'][str(prepared_path.relative_to(root))]:
        raise ValueError('LEDGER_SUPERVISED_FAMILY_BINDING')
    families = prepared['trainingFamilies']
    if len(families) != 42 or len(set(families)) != 42:
        raise ValueError('LEDGER_SUPERVISED_FAMILY_COUNT')
    entries.append(dict(id='authored-right-context-supervised-families-v12', usage='supervised',
        bindings={str(p.relative_to(root)): sha(p) for p in (prepared_path, evidence_path)},
        keys={'family': sorted(keys_for([dict(families=families)], 'family'))}, missingAxes=[]))
    return validate_ledger(dict(schema=1, keySchema=KEY_SCHEMA, publicDataOnly=True,
        coverage=dict(complete=False, pending=[
            'Recover historical article and source-sentence identities for spelling v7-v12.',
            'Map historical spelling family identifiers to pinned canonical lemma exclusions.',
            'Import remaining joint/context/conversation/public qualification and training exclusions.',
            'Archive required historical generator versions and verify full provenance coverage.',
        ]), entries=sorted(entries, key=lambda entry: entry['id'])))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    snapshot = build_snapshot(args.root)
    with args.output.open('x') as stream:
        stream.write(json.dumps(snapshot, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps(dict(entries=len(snapshot['entries']), coverageComplete=False,
                          sha256=sha(args.output))))


if __name__ == '__main__':
    main()
