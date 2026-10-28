#!/usr/bin/env python3
"""Reproduce the historical v2 corpus with exact archived sources and inputs."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
ARCHIVE = REPO / 'tools/typing_experiments/frozen_sources'
MANIFEST_SHA = '8bb3d0a0db1c11306ab809a4a1ede7c1a2b613529c7305e51523d668afd5a452'
SOURCES = {
    'tools/eval/smart-typing-0.3/evaluate.py':
        'ad76b78ba9f00f301465e0f47eb7e96781c44d8bc141a8e1176603bc7f12d5d7',
    'tools/eval/smart-typing-0.3/qualification-v2/generate_corpus.py':
        '2cbcb2508ef66b32a60b5c7665ad96c66dc1c6477c9da4ad6dde0ea969806e65',
    'tools/eval/smart-typing-0.3/qualification-v2/source-lock.json':
        'e3ad381de42a6ac08defd3bad7486789ea15329742e19448b39bf4ebaed795ed',
}


def require(value, code):
    if not value:
        raise ValueError(code)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def checked(path, expected):
    require(path.is_file() and not path.is_symlink() and sha(path) == expected,
            'V2_REPRODUCTION_IDENTITY')
    return path


def archived_sources():
    catalog = json.loads((ARCHIVE / 'manifest.json').read_text())['sources']
    result = {}
    for name, digest in SOURCES.items():
        row = catalog.get(digest)
        require(isinstance(row, dict) and row.get('originalPath') == name,
                'V2_REPRODUCTION_SOURCE_CATALOG')
        path = ARCHIVE / row['file']
        require(path.resolve().parent == ARCHIVE.resolve(), 'V2_REPRODUCTION_SOURCE_PATH')
        result[name] = checked(path, digest)
    return result


def reference():
    path = checked(HERE / 'corpus/manifest.json', MANIFEST_SHA)
    manifest = json.loads(path.read_text())
    require(manifest['sources'] == SOURCES, 'V2_REPRODUCTION_SOURCE_SET')
    for name, digest in manifest['files'].items():
        checked(HERE / 'corpus' / name, digest)
    return manifest


def verify_product(output, manifest):
    expected = dict(manifest['files'], **{'manifest.json': MANIFEST_SHA})
    require({p.name for p in output.iterdir()} == set(expected), 'V2_REPRODUCTION_OUTPUT_SET')
    for name, digest in expected.items():
        checked(output / name, digest)
    return expected


def run(args):
    manifest = reference()
    sources = archived_sources()
    lock = json.loads(sources[next(n for n in SOURCES if n.endswith('source-lock.json'))].read_text())
    old = args.old_corpus.resolve(strict=True)
    checked(old / 'manifest.json', manifest['oldCorpusManifestSha256'])
    old_manifest = json.loads((old / 'manifest.json').read_text())
    inputs = args.inputs.resolve(strict=True)
    frequency = args.frequency_inputs.resolve(strict=True)
    training = args.training_data.resolve(strict=True)
    bindings = {}
    for kind, directory, identities in (
            ('wikipedia', inputs, manifest['source']['files']),
            ('frequency', frequency, lock['frequencyWords']),
            ('training', training, manifest['trainingData']),
            ('oldCorpus', old, old_manifest['files'])):
        for name, digest in identities.items():
            checked(directory / name, digest)
            bindings[kind + '/' + name] = digest
    bindings['oldCorpus/manifest.json'] = manifest['oldCorpusManifestSha256']
    root = args.output.resolve()
    require(root.is_relative_to(REPO / 'build') and not root.exists(),
            'V2_REPRODUCTION_FRESH_BUILD_OUTPUT')
    ignored = subprocess.run(['git', 'check-ignore', '-q', str(root)], cwd=REPO,
                             capture_output=True, check=False)
    require(ignored.returncode == 0, 'V2_REPRODUCTION_IGNORED_OUTPUT')
    root.mkdir(parents=True, mode=0o700)
    projection = root / 'source-projection'
    for name, path in sources.items():
        target = projection / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
        checked(target, SOURCES[name])
    output = projection / 'build/corpus'
    command = [sys.executable,
               str(projection / 'tools/eval/smart-typing-0.3/qualification-v2/generate_corpus.py'),
               '--inputs', str(inputs), '--frequency-inputs', str(frequency),
               '--training-data', str(training), '--old-corpus', str(old), '--output', str(output)]
    with (root / 'generation.log').open('xb') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=3600,
                                check=False)
    require(result.returncode == 0, 'V2_REPRODUCTION_GENERATOR_FAILED')
    files = verify_product(output, manifest)
    # Re-read identities after execution; a successful output does not waive drift.
    reference()
    require(archived_sources() == sources, 'V2_REPRODUCTION_SOURCE_CHANGED')
    for name, digest in SOURCES.items():
        checked(projection / name, digest)
    for kind, directory in [('wikipedia', inputs), ('frequency', frequency),
                            ('training', training), ('oldCorpus', old)]:
        for name, digest in bindings.items():
            prefix = kind + '/'
            if name.startswith(prefix):
                checked(directory / name[len(prefix):], digest)
    receipt = dict(schema=1, passed=True, historicalReproductionOnly=True,
                   referenceManifestSha256=MANIFEST_SHA, sourceBindings=SOURCES,
                   inputBindings=bindings, outputFiles=files,
                   python=platform.python_version(), pyarrow=importlib.metadata.version('pyarrow'),
                   logSha256=sha(root / 'generation.log'), generatorExitCode=result.returncode)
    (root / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps(dict(passed=True, files=len(files), rows=manifest['validation']['samples'])))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--frequency-inputs', type=Path, required=True)
    parser.add_argument('--training-data', type=Path, required=True)
    parser.add_argument('--old-corpus', type=Path, default=HERE.parent)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        run(args)
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        parser.exit(1, type(error).__name__ + ': historical v2 reproduction failed; inspect local inputs/log\n')


if __name__ == '__main__':
    main()
