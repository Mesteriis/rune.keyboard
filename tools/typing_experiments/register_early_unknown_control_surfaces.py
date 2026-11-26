#!/usr/bin/env python3
"""Exclude disclosed early RU unknown target surfaces from control collection."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile

import check_historical_qualification_archives as archives
import control_ledger as control
import holdout_ledger as lexical
from source_identities import unsupported_surface_key

ROOT = Path(__file__).resolve().parents[2]
LEXICAL = ROOT / 'tools/typing_experiments/holdout-ledger.json'
CONTROL = ROOT / 'tools/typing_experiments/control-ledger.json'
ARCHIVE_DIR = ROOT / 'tools/typing_experiments/historical-qualification-v3-v4'
V2 = ROOT / 'tools/eval/smart-typing-0.3/qualification-v2/corpus'
ENTRY = 'historical-early-ru-unknown-control-surfaces-v1'
ANCHOR = 'ci-product-replay-v1-ru'
PARENTS = {'qualification-v2': 171, 'compact-v3': 222, 'compact-v4': 261}
V2_MANIFEST = '8bb3d0a0db1c11306ab809a4a1ede7c1a2b613529c7305e51523d668afd5a452'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def project(rows, unknown):
    found = set(); surfaces = set(); occurrences = 0
    for row in rows:
        if not isinstance(row, dict) or row.get('language') != 'ru' or row.get('task') != 'spelling':
            raise ValueError('EARLY_CONTROL_ROW_SCOPE')
        target = row.get('expectedSpelling')
        if target is None and row.get('cohort') == 'correct': target = row.get('typed')
        if not isinstance(target, str) or not target:
            raise ValueError('EARLY_CONTROL_TARGET')
        key = unsupported_surface_key(target)
        if key in unknown:
            found.add(key); surfaces.add(control.surface_key('ru', target)); occurrences += 1
    if found != unknown:
        raise ValueError('EARLY_CONTROL_UNKNOWN_COVERAGE')
    return surfaces, occurrences


def make_entry(lexical_data, control_data, root=ROOT):
    root = Path(root)
    lexical_data = lexical.validate_ledger(lexical_data)
    control_data = control.validate(control_data)
    parents = {e['id']: e for e in lexical_data['entries']}
    anchors = [e for e in control_data['entries'] if e['id'] == ANCHOR]
    if len(anchors) != 1 or anchors[0]['language'] != 'ru' or anchors[0]['kind'] != 'regression':
        raise ValueError('EARLY_CONTROL_ANCHOR')
    v2 = root / 'tools/eval/smart-typing-0.3/qualification-v2/corpus'
    archive_dir = root / 'tools/typing_experiments/historical-qualification-v3-v4'
    v2_manifest = (v2 / 'manifest.json').read_bytes()
    if digest(v2_manifest) != V2_MANIFEST:
        raise ValueError('EARLY_CONTROL_V2_MANIFEST')
    manifest = json.loads(v2_manifest); v2_rows = (v2 / 'spelling-ru.jsonl').read_bytes()
    if digest(v2_rows) != manifest['files']['spelling-ru.jsonl']:
        raise ValueError('EARLY_CONTROL_V2_ROWS')
    loaded = archives.load(archive_dir)
    data = {'qualification-v2': v2_rows, 'compact-v3': loaded['v3']['spelling-ru.jsonl'],
            'compact-v4': loaded['v4']['spelling-ru.jsonl']}
    all_surfaces = set(); parent_hashes = {}; occurrences = 0
    for name, count in PARENTS.items():
        ident = 'public-early-ru-' + name
        parent = parents.get(ident)
        if not isinstance(parent, dict) or parent.get('rowCount') != 3400:
            raise ValueError('EARLY_CONTROL_PARENT')
        unknown = parent.get('unsupportedSurfaceKeys')
        if not isinstance(unknown, list) or len(unknown) != count:
            raise ValueError('EARLY_CONTROL_PARENT_SURFACES')
        rows = [json.loads(line) for line in data[name].splitlines()]
        if len(rows) != parent['rowCount']:
            raise ValueError('EARLY_CONTROL_ROW_COUNT')
        surfaces, n = project(rows, set(unknown)); all_surfaces.update(surfaces); occurrences += n
        parent_hashes[ident] = digest(json.dumps(parent, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())
    if len(all_surfaces) != 654 or occurrences != 654:
        raise ValueError('EARLY_CONTROL_SURFACE_COUNT')
    paths = [v2 / 'manifest.json', v2 / 'spelling-ru.jsonl', archive_dir / 'catalog.json',
             archive_dir / 'qualification-v3.tar.bz2', archive_dir / 'qualification-v4.tar.bz2',
             root / 'tools/typing_experiments/register_early_unknown_control_surfaces.py',
             root / 'tools/typing_experiments/check_historical_qualification_archives.py',
             root / 'tools/typing_experiments/holdout_ledger.py', root / 'tools/typing_experiments/control_ledger.py',
             root / 'tools/typing_experiments/source_identities.py']
    return {'id': ENTRY, 'kind': 'regression', 'language': 'ru', 'rowCount': anchors[0]['rowCount'],
            'keys': list(anchors[0]['keys']), 'surfaceKeys': sorted(all_surfaces),
            'parentEntries': list(parent_hashes), 'parentEntrySha256': parent_hashes,
            'bindings': {str(p.relative_to(root)): digest(p.read_bytes()) for p in paths},
            'semantics': 'Exact unsupported target surfaces from disclosed early RU corpora; no canonical family or intended sense inferred.'}


def check(lexical_data, control_data, root=ROOT):
    expected = make_entry(lexical_data, control_data, root)
    matches = [entry for entry in control_data['entries'] if entry['id'] == ENTRY]
    if matches != [expected]: raise ValueError('EARLY_CONTROL_REGISTERED_DRIFT')
    return {'surfaces': len(expected['surfaceKeys']), 'independentQualification': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true'); parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    if args.check == args.write: parser.error('choose exactly one of --check or --write')
    original = CONTROL.read_bytes(); lexical_before = digest(LEXICAL.read_bytes())
    lex = lexical.load_ledger(LEXICAL); ctl = control.validate(json.loads(original))
    if args.check:
        result = check(lex, ctl)
    else:
        if any(entry['id'] == ENTRY for entry in ctl['entries']): raise ValueError('EARLY_CONTROL_ALREADY_REGISTERED')
        entry = make_entry(lex, ctl); modified = copy.deepcopy(ctl); modified['entries'].append(entry)
        control.validate(modified); check(lex, modified)
        raw = (json.dumps(modified, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
        if CONTROL.read_bytes() != original: raise ValueError('EARLY_CONTROL_CONCURRENT_CHANGE')
        name = None
        try:
            with tempfile.NamedTemporaryFile(dir=CONTROL.parent, prefix='.early-control-', delete=False) as output:
                name = output.name; os.fchmod(output.fileno(), CONTROL.stat().st_mode & 0o777)
                output.write(raw); output.flush(); os.fsync(output.fileno())
            if CONTROL.read_bytes() != original or digest(LEXICAL.read_bytes()) != lexical_before:
                raise ValueError('EARLY_CONTROL_CONCURRENT_CHANGE')
            os.replace(name, CONTROL); name = None
        finally:
            if name is not None: Path(name).unlink(missing_ok=True)
        result = {'surfaces': len(entry['surfaceKeys']), 'independentQualification': False}
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
