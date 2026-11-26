"""Register exclusions from the exact recovered v6 selection ancestry."""

import argparse
import hashlib
import json
from pathlib import Path

from audit_available_v6_family_exposure import MANIFEST, PARENT_PLAN, PROVENANCE
from holdout_ledger import KINDS, keys_for, load_ledger, pack_ledger
from restore_final_available_v6 import PARENT_PLAN_SHA256, PARENT_ROOT


ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = PROVENANCE / 'v6-inputs'
PREFIX = 'public-recovered-v6-'
PARENT_ENTRY = PREFIX + 'sentence-pairs-v2-v6'
CONTEXTS = {
    'fresh-matched-v5': 45,
    'reliable-side-v5': 1690,
    'sentence-corpus-v6': 2068,
    'sentence-pairs-v2-v6': 3293,
}
RARE_ROOT = 'build/diagnostic-rare-ranking/fresh-corpus'


def checked_bytes(path, expected):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('V6_HISTORY_DIGEST:' + path.name)
    return raw


def make_entry(name, rows, count, axes, bindings):
    if len(rows) != count:
        raise ValueError('V6_HISTORY_ROW_COUNT:' + name)
    return dict(id=PREFIX + name, usage='historical-exclusion', rowCount=count,
                bindings=bindings, keys={axis: sorted(keys_for(rows, axis)) for axis in axes},
                missingAxes=[axis for axis in KINDS if axis not in axes])


def project(recovery_dir):
    parent = json.loads(checked_bytes(PARENT_PLAN, PARENT_PLAN_SHA256))
    clean_path = ARCHIVE / 'available-clean-v6-plan.json'
    manifest = json.loads(MANIFEST.read_bytes())
    clean_digest = manifest['planSha256']
    clean = json.loads(checked_bytes(clean_path, clean_digest))
    if clean['parentPlanSha256'] != PARENT_PLAN_SHA256:
        raise ValueError('V6_HISTORY_PARENT_PLAN')
    parent_binding = {PARENT_PLAN.relative_to(ROOT).as_posix(): PARENT_PLAN_SHA256}
    entries = []

    for name, count in CONTEXTS.items():
        filename = 'contexts.unqualified.jsonl'
        if name == 'sentence-pairs-v2-v6':
            origin = f'{PARENT_ROOT}/{filename}'
            digest = clean['recordsSha256']
            bindings = parent_binding | {clean_path.relative_to(ROOT).as_posix(): clean_digest}
        else:
            origin = f'build/right-context-{name}-20261027/{filename}'
            digest = parent['additionalArticleBindings'][origin]
            bindings = parent_binding
        raw = checked_bytes(recovery_dir / name / filename, digest)
        rows = [dict(row, expectedSpelling=row['word']) for row in map(json.loads, raw.splitlines())]
        entry = make_entry(name, rows, count, KINDS, bindings | {origin: digest})
        entry['notes'] = 'Original rejected selection, with the recorded source context hash and declared dictionary families.'
        entries.append(entry)

    for part, rows, count, bindings in rare_ranking_payloads(recovery_dir):
        entry = make_entry('diagnostic-rare-ranking-' + part, rows, count, ('article', 'context'), bindings)
        entry['notes'] = 'Exact diagnostic rows. Packed family identifiers and sentence hashes are outside this projection.'
        entries.append(entry)
    return entries


def rare_ranking_payloads(recovery_dir):
    parent = json.loads(checked_bytes(PARENT_PLAN, PARENT_PLAN_SHA256))
    parent_binding = {PARENT_PLAN.relative_to(ROOT).as_posix(): PARENT_PLAN_SHA256}
    rare_manifest_path = ARCHIVE / 'diagnostic-rare-ranking-manifest.json'
    proof = json.loads((ARCHIVE / 'joint-diagnostic-recovery.json').read_bytes())
    rare_manifest_sha = proof['corpora']['diagnostic-rare-ranking']['manifestSha256']
    rare_manifest = json.loads(checked_bytes(rare_manifest_path, rare_manifest_sha))
    for part in ('calibration', 'holdout'):
        filename = part + '.jsonl'
        origin = RARE_ROOT + '/' + filename
        digest = parent['exclusionBindings'][origin]
        if rare_manifest['files'][filename] != digest:
            raise ValueError('V6_HISTORY_RARE_MANIFEST')
        raw = checked_bytes(recovery_dir / 'joint-diagnostic-replay/diagnostic-rare-ranking' / filename, digest)
        rows = list(map(json.loads, raw.splitlines()))
        bindings = parent_binding | {origin: digest, rare_manifest_path.relative_to(ROOT).as_posix(): rare_manifest_sha}
        yield part, rows, rare_manifest['counts'][part]['rows'], bindings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recovery-dir', required=True, type=Path)
    parser.add_argument('--base', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    base = load_ledger(args.base)
    entries = project(args.recovery_dir)
    if {entry['id'] for entry in entries} & {entry['id'] for entry in base['entries']}:
        raise ValueError('V6_HISTORY_ALREADY_REGISTERED')
    packed = pack_ledger(base | {'entries': entries})['entries']
    storage = json.loads(args.base.read_bytes())
    storage['entries'].extend(packed)
    with args.output.open('x') as output:
        output.write(json.dumps(storage, ensure_ascii=False, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
