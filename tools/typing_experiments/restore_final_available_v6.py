"""Recover the clean v6 plan and corpus from a replay of the parent selector."""
import argparse
import json
from pathlib import Path

from audit_available_v6_family_exposure import FLAGS, MANIFEST, PARENT_PLAN, PROVENANCE, serialize
from recover_natural_frozen_corpus import PARTS, ROOT, digest, encode


EVIDENCE = ROOT / 'docs/acceptance/2026-10-27-right-context-numeric-bridge-evidence.json'
PARENT_ROOT = 'build/right-context-sentence-pairs-v2-v6-20261027'
CLEAN_ROOT = 'build/right-context-available-clean-v6-20261027'
AUDIT_SOURCE = 'tools/typing_experiments/right_context_sentence_audit.py'
PREPARER = PROVENANCE / 'available_clean_v6_reconstructed.py'
PARENT_PLAN_SHA256 = 'b54efac3d50e8f5d59ec9796118c55a370dd97b0f2111c37fb23c0c3561d6346'


def assemble(parent_records, exclusions):
    variants = {part: [] for part in PARTS}
    targets = {part: set(exclusions[part]['removedContextHashes']) for part in PARTS}
    seen = set()
    removed = {part: set() for part in PARTS}
    index = dict.fromkeys(PARTS, 0)
    for item in map(json.loads, parent_records.splitlines()):
        part, context = item['part'], item['contextHash']
        if part not in variants or context in seen or item['familyExposure'] not in FLAGS:
            raise ValueError('FINAL_V6_CONTEXT')
        seen.add(context)
        width = 4 + bool(item['rival'])
        first = index[part]
        index[part] += width
        if context in targets[part]:
            removed[part].add(context)
            continue
        ids = [f'available-v6-{part}-{position:06d}' for position in range(first, first + width)]
        variants[part].append(serialize(item, ids, item['familyExposure']))

    files = {}
    for part, groups in variants.items():
        report = exclusions[part]
        raw = b''.join(groups)
        rows = raw.splitlines()
        if (index[part] != report['originalRows'] or removed[part] != targets[part]
                or len(rows) != report['keptRows'] or index[part] - len(rows) != report['removedRows']):
            raise ValueError('FINAL_V6_EXCLUSIONS:' + part)
        files[part + '.jsonl'] = raw
        files[part + '.tsv'] = ''.join(
            '\t'.join((str(position), encode(row['id']), part, 'ru', encode(row['prefix']), encode(row['typed']))) + '\n'
            for position, row in enumerate(map(json.loads, rows))
        ).encode()
    return files


def recover(parent_records, availability):
    evidence = json.loads(EVIDENCE.read_bytes())['bindings']
    inputs = {
        PARENT_ROOT + '/availability.json': availability,
        CLEAN_ROOT + '/corpus/manifest.json': MANIFEST.read_bytes(),
        CLEAN_ROOT + '/prior-context-exclusions.json': (PROVENANCE / 'available_clean_v6_prior_context_exclusions.json').read_bytes(),
        CLEAN_ROOT + '/identity-audit.json': (PROVENANCE / 'available_clean_v6_identity_audit.json').read_bytes(),
        AUDIT_SOURCE: (ROOT / AUDIT_SOURCE).read_bytes(),
    }
    for name, raw in inputs.items():
        if digest(raw) != evidence[name]:
            raise ValueError('FINAL_V6_INPUT_BINDING:' + name)
    if digest(PARENT_PLAN.read_bytes()) != PARENT_PLAN_SHA256:
        raise ValueError('FINAL_V6_PARENT_PLAN')
    manifest = json.loads(inputs[CLEAN_ROOT + '/corpus/manifest.json'])
    exclusions = json.loads(inputs[CLEAN_ROOT + '/prior-context-exclusions.json'])
    files = assemble(parent_records, exclusions)
    plan = dict(stage='available-record-calibration-diagnostic-only', fullCohortGatePassed=False,
                failedAvailabilitySha256=digest(availability), parentPlanSha256=PARENT_PLAN_SHA256,
                recordsSha256=digest(parent_records), modelSha256=manifest['modelSha256'],
                scriptSha256=digest(PREPARER.read_bytes()), auditSourceSha256=evidence[AUDIT_SOURCE],
                qualificationRequirementsChanged=False, holdoutScoringAllowed=False, modelCalls=0)
    files['plan.json'] = json.dumps(plan, indent=2).encode()
    expected = {**manifest['files'], 'plan.json': manifest['planSha256']}
    actual = {name: digest(raw) for name, raw in files.items()}
    matches = {name: actual[name] == checksum for name, checksum in expected.items()}
    return files, matches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent-dir', required=True, type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = args.output.resolve() if args.output is not None else None
    if output is not None and (output.exists() or not output.is_relative_to(ROOT / 'build')):
        parser.error('output must be a new directory inside the repository build directory')
    files, matches = recover((args.parent_dir / 'contexts.unqualified.jsonl').read_bytes(),
                             (args.parent_dir / 'availability.json').read_bytes())
    print(json.dumps(dict(matches=matches, modelCalls=0), indent=2))
    if not all(matches.values()):
        raise SystemExit(1)
    if output is not None:
        output.mkdir(parents=True, mode=0o700)
        for name, raw in files.items():
            (output / name).write_bytes(raw)


if __name__ == '__main__':
    main()
