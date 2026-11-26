#!/usr/bin/env python3
"""Quarantine disclosed v2-v4 qualification inputs in the control registry."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile

import check_historical_qualification_archives as archives
import control_ledger as control

ROOT = Path(__file__).resolve().parents[2]
CONTROL = ROOT / 'tools/typing_experiments/control-ledger.json'
V2 = ROOT / 'tools/eval/smart-typing-0.3/qualification-v2/corpus'
ARCHIVES = ROOT / 'tools/typing_experiments/historical-qualification-v3-v4'
PREFIX = 'historical-qualification-inputs-'
V2_MANIFEST = '8bb3d0a0db1c11306ab809a4a1ede7c1a2b613529c7305e51523d668afd5a452'
LANGUAGES = ('en', 'es', 'ru')
KINDS = ('regression', 'punctuation', 'protected')
EXPECTED = {'regression': 3400, 'punctuation': 400, 'protected': 600}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def inputs(root=ROOT):
    root = Path(root); v2 = root / V2.relative_to(ROOT); archive_dir = root / ARCHIVES.relative_to(ROOT)
    raw = (v2 / 'manifest.json').read_bytes()
    if sha(raw) != V2_MANIFEST: raise ValueError('HISTORICAL_CONTROL_V2_MANIFEST')
    manifest = json.loads(raw)
    if manifest.get('containsPersonalMessages') is not False or manifest.get('corpusVersion') != 2:
        raise ValueError('HISTORICAL_CONTROL_V2_SCOPE')
    files = {'manifest.json': raw}
    if set(manifest.get('files', {})) != archives.NAMES - {'manifest.json'}:
        raise ValueError('HISTORICAL_CONTROL_V2_FILES')
    for name, expected in manifest['files'].items():
        files[name] = (v2 / name).read_bytes()
        if sha(files[name]) != expected: raise ValueError('HISTORICAL_CONTROL_V2_ROW_IDENTITY')
    return {'v2': files, **archives.load(archive_dir)}


def derive(files, ledger, root=ROOT):
    root = Path(root); ledger = control.validate(ledger)
    existing = {entry['id']: entry for entry in ledger['entries']}
    if set(files) != {'v2', 'v3', 'v4'}: raise ValueError('HISTORICAL_CONTROL_VERSIONS')
    results = []; all_bindings = {}; surfaces_by_language = {lang: set() for lang in LANGUAGES}
    for version in ('v2', 'v3', 'v4'):
        source = files[version]
        if set(source) != archives.NAMES: raise ValueError('HISTORICAL_CONTROL_SOURCE_FILES')
        shared = [root / 'tools/typing_experiments/register_historical_qualification_controls.py',
                  root / 'tools/typing_experiments/control_ledger.py',
                  root / 'tools/typing_experiments/source_identities.py']
        if version == 'v2':
            paths = shared + [root / V2.relative_to(ROOT) / name for name in sorted(archives.NAMES)]
        else:
            directory = root / ARCHIVES.relative_to(ROOT)
            paths = shared + [directory / f'qualification-{version}.tar.bz2', directory / 'catalog.json',
                              root / 'tools/typing_experiments/check_historical_qualification_archives.py']
        bindings = {str(p.relative_to(root)): sha(p.read_bytes()) for p in paths}
        if version == 'v2':
            if any(bindings[str((root / V2.relative_to(ROOT) / name).relative_to(root))] != sha(source[name])
                   for name in archives.NAMES):
                raise ValueError('HISTORICAL_CONTROL_INPUT_DRIFT')
        else:
            directory = root / ARCHIVES.relative_to(ROOT)
            catalog = json.loads((directory / 'catalog.json').read_bytes())
            archive_path = directory / f'qualification-{version}.tar.bz2'
            checker = root / 'tools/typing_experiments/check_historical_qualification_archives.py'
            if (bindings[str(archive_path.relative_to(root))] != catalog['archives'][version]['archiveSha256'] or
                    bindings[str(checker.relative_to(root))] != sha(Path(archives.__file__).read_bytes())):
                raise ValueError('HISTORICAL_CONTROL_INPUT_DRIFT')
        for key, value in bindings.items():
            if key in all_bindings and all_bindings[key] != value: raise ValueError('HISTORICAL_CONTROL_INPUT_DRIFT')
            all_bindings[key] = value
        groups = {(kind, lang): [] for kind in KINDS for lang in LANGUAGES}
        for filename, raw in source.items():
            if filename == 'manifest.json': continue
            ids = set()
            for line in raw.splitlines():
                row = json.loads(line)
                if not isinstance(row, dict) or not isinstance(row.get('id'), str) or row['id'] in ids:
                    raise ValueError('HISTORICAL_CONTROL_ROW_ID')
                ids.add(row['id']); lang = row.get('language')
                if lang not in LANGUAGES: raise ValueError('HISTORICAL_CONTROL_LANGUAGE')
                if filename == 'protected-tokens.jsonl':
                    kind = 'protected'
                    if row.get('task') != 'spelling' or row.get('cohort') != 'protected':
                        raise ValueError('HISTORICAL_CONTROL_PROTECTED_SCOPE')
                elif filename == f'punctuation-{lang}.jsonl':
                    kind = 'punctuation'
                    if row.get('task') != 'punctuation': raise ValueError('HISTORICAL_CONTROL_PUNCTUATION_SCOPE')
                elif filename == f'spelling-{lang}.jsonl':
                    kind = 'regression'
                    if row.get('task') != 'spelling': raise ValueError('HISTORICAL_CONTROL_SPELLING_SCOPE')
                else: raise ValueError('HISTORICAL_CONTROL_FILE_SCOPE')
                groups[(kind, lang)].append(row)
        for (kind, lang), rows in groups.items():
            if len(rows) != EXPECTED[kind]: raise ValueError('HISTORICAL_CONTROL_ROW_COUNT')
            keys = sorted({control.key_for(row, kind) for row in rows})
            surfaces = sorted({control.surface_key(lang, row.get('currentWord') if kind == 'punctuation' else row.get('typed'))
                               for row in rows})
            surfaces_by_language[lang].update(surfaces)
            if kind == 'regression':
                results.append({'id': f'{PREFIX}{version}-{kind}-{lang}', 'kind': kind, 'language': lang,
                                'rowCount': len(rows), 'keys': keys, 'bindings': bindings,
                                'semantics': 'Exact previously disclosed spelling inputs; no fresh qualification inferred.'})
            else:
                historical = 'qualification-v2' if version == 'v2' else 'compact-' + version
                prior = existing.get(f'{historical}-{kind}-{lang}')
                if (not isinstance(prior, dict) or prior.get('kind') != kind or prior.get('language') != lang or
                        prior.get('rowCount') != len(rows) or prior.get('keys') != keys):
                    raise ValueError('HISTORICAL_CONTROL_PRIOR_COMPONENT')
    for lang in LANGUAGES:
        anchor = existing.get('ci-product-replay-v1-' + lang)
        if not isinstance(anchor, dict) or anchor.get('kind') != 'regression' or anchor.get('language') != lang:
            raise ValueError('HISTORICAL_CONTROL_SURFACE_ANCHOR')
        results.append({'id': f'{PREFIX}surfaces-{lang}', 'kind': 'regression', 'language': lang,
                        'rowCount': anchor['rowCount'], 'keys': list(anchor['keys']),
                        'surfaceKeys': sorted(surfaces_by_language[lang]), 'bindings': all_bindings,
                        'semantics': 'Exact previously disclosed spelling, punctuation and protected surfaces; no intent or family inferred.'})
    return results


def check(ledger, root=ROOT):
    ledger = control.validate(ledger); expected = derive(inputs(root), ledger, root)
    found = [entry for entry in ledger['entries'] if entry['id'].startswith(PREFIX)]
    if found != expected: raise ValueError('HISTORICAL_CONTROL_REGISTERED_DRIFT')
    return {'entries': len(expected), 'independentQualification': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true'); parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    if args.check == args.write: parser.error('choose exactly one of --check or --write')
    original = CONTROL.read_bytes(); ledger = control.validate(json.loads(original))
    if args.check:
        result = check(ledger)
    else:
        if any(e['id'].startswith(PREFIX) for e in ledger['entries']):
            raise ValueError('HISTORICAL_CONTROL_ALREADY_REGISTERED')
        entries = derive(inputs(), ledger); modified = copy.deepcopy(ledger); modified['entries'].extend(entries)
        control.validate(modified); check(modified)
        raw = (json.dumps(modified, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
        name = None
        try:
            with tempfile.NamedTemporaryFile(dir=CONTROL.parent, prefix='.historical-control-', delete=False) as out:
                name = out.name; os.fchmod(out.fileno(), CONTROL.stat().st_mode & 0o777)
                out.write(raw); out.flush(); os.fsync(out.fileno())
            if CONTROL.read_bytes() != original: raise ValueError('HISTORICAL_CONTROL_CONCURRENT_CHANGE')
            os.replace(name, CONTROL); name = None
        finally:
            if name is not None: Path(name).unlink(missing_ok=True)
        result = {'entries': len(entries), 'independentQualification': False}
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
