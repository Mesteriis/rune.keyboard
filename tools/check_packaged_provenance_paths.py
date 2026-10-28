#!/usr/bin/env python3
"""Audit explicit repository references in packaged provenance, without execution.

Dataset-relative names and remote repositories are not local source paths.
This does not establish transitive training dependencies or model reproduction.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ASSETS = 'app/src/main/assets'
SCRIPTS = 'tools/typing_experiments/'
HISTORICAL = {
    ('test_refinement.py', '9a183595c9f52c6a6d6f39d79d6f168369b7a7ae966ecc6b475f1798e2e155d9'):
        SCRIPTS + 'historical_provenance_sources/refinement_test_9a183595c9f52c6a6d6f39d79d6f168369b7a7ae966ecc6b475f1798e2e155d9.py',
}
NAMED_DIGESTS = {
    ASSETS + '/smarttyping/experiments/provenance.json':
        (('selected', 'scriptSha256'), SCRIPTS + 'augmented_abstaining_ranker.py'),
    ASSETS + '/smarttyping/lexicon/provenance/rare-word-manifest.json':
        (('scriptSha256',), SCRIPTS + 'pack_rare_word_lexicon.py'),
}


def file_bytes(root, name, tracked):
    if (name not in tracked or '\\' in name or
            any(part in {'', '.', '..'} for part in name.split('/'))):
        raise ValueError('UNTRACKED_OR_UNSAFE_PATH ' + name)
    path = root / name
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('UNSAFE_PATH ' + name)
    return path.read_bytes()


def strings(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)
    elif isinstance(value, str):
        yield value


def inspect(root=ROOT, tracked=None):
    if tracked is None:
        tracked = set(subprocess.check_output(['git', 'ls-files', '-z'], cwd=root)
                      .decode().split('\0'))
    receipts = []
    names = {name for name in tracked if name.startswith(ASSETS + '/')
             and Path(name).name.endswith('provenance.json')}
    names.update(path.relative_to(root).as_posix()
                 for path in (root / ASSETS).rglob('*provenance.json'))
    names.update(name for name in NAMED_DIGESTS if name in tracked or (root / name).exists())
    for name in sorted(names):
        data = json.loads(file_bytes(root, name, tracked))
        refs = sorted({ref for text in strings(data)
                       for ref in re.findall(r'(?<![\w/])(?:tools|docs|app)/[\w./-]+', text)})
        for ref in refs:
            file_bytes(root, ref, tracked)
        scripts = []
        for script, digest in data.get('trainingScripts', {}).items():
            if (Path(script).name != script or not script.endswith('.py') or
                    re.fullmatch('[0-9a-f]{64}', digest) is None):
                raise ValueError('UNREVIEWED_TRAINING_SCRIPT ' + name)
            current = SCRIPTS + script
            raw = file_bytes(root, current, tracked)
            resolved = current
            if hashlib.sha256(raw).hexdigest() != digest:
                resolved = HISTORICAL.get((script, digest))
                if resolved is None:
                    raise ValueError('TRAINING_SCRIPT_IDENTITY ' + script)
                raw = file_bytes(root, resolved, tracked)
            if hashlib.sha256(raw).hexdigest() != digest:
                raise ValueError('HISTORICAL_SCRIPT_IDENTITY ' + script)
            scripts.append({'declared': current, 'resolved': resolved, 'sha256': digest})
        qualification = data.get('automaticQualification', {})
        if 'policyPath' in qualification:
            raw = file_bytes(root, qualification['policyPath'], tracked)
            if hashlib.sha256(raw).hexdigest() != qualification.get('policySha256'):
                raise ValueError('AUTOMATIC_POLICY_IDENTITY')
        named = []
        if name in NAMED_DIGESTS:
            keys, source = NAMED_DIGESTS[name]
            value = data
            for key in keys:
                value = value.get(key) if isinstance(value, dict) else None
            # Only declared fields are identity claims; missing metadata is a
            # separate schema/data-policy check, not an inferred source binding.
            if value is not None:
                raw = file_bytes(root, source, tracked)
                if hashlib.sha256(raw).hexdigest() != value:
                    raise ValueError('NAMED_SOURCE_IDENTITY ' + source)
                named.append({'path': source, 'sha256': value})
        receipts.append({'provenance': name, 'repositoryPaths': refs,
                         'trainingScripts': scripts, 'namedSourceIdentities': named})
    if not receipts:
        raise ValueError('NO_PACKAGED_PROVENANCE')
    return {'scope': 'PACKAGED_EXPLICIT_REPOSITORY_PATHS_AND_TRAINING_SCRIPT_IDENTITIES',
            'provenanceFiles': receipts, 'modelExecutionEstablished': False,
            'transitiveDependencyCoverageEstablished': False}


if __name__ == '__main__':
    try:
        print(json.dumps(inspect(), indent=2, sort_keys=True))
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise SystemExit('Packaged provenance path audit FAILED: ' + str(error))
