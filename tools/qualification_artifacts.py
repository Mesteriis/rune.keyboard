#!/usr/bin/env python3
"""Verify qualification metadata against the model descriptor and runtime source/build identity.

The build ID identifies source plus pinned build recipe, not an APK binary hash.
No model is opened and no qualification constant is automatically rewritten.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(root, paths, llama_commit):
    record = {'llamaCommit': llama_commit,
              'files': {p: sha(root / p) for p in sorted(paths)}}
    return hashlib.sha256(json.dumps(record, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def runtime_inputs(root):
    paths = ['runtime-llama/build.gradle.kts', 'gradle/libs.versions.toml',
             'tools/eval/smart-typing-0.3/scoring.cpp', 'tools/eval/smart-typing-0.3/scoring.h']
    paths += [str(p.relative_to(root)) for p in (root / 'runtime-llama/src/main').rglob('*')
              if p.is_file() and 'llama.cpp' not in p.parts]
    return sorted(set(paths))


def check_runtime_source(root, prepared_source=None):
    submodule = root / 'runtime-llama/src/main/cpp/llama.cpp'
    if prepared_source is not None:
        from fdroid_prepared_source import PREPARER, check_prepared
        if prepared_source != PREPARER:
            raise ValueError('QUALIFICATION_PREPARED_SOURCE_UNSUPPORTED')
        check_prepared(root)
        # The runtime ID binds the submodule commit, not arbitrary dirty C++.
        # Even a future policy revision must never hide compiled-source edits.
        raw = subprocess.check_output(['git', '-C', str(submodule), 'diff', '--name-status',
                                       '--no-renames', '-z', 'HEAD', '--'])
        expected = {b'examples/llama.android/gradlew',
                    b'examples/llama.android/gradle/wrapper/gradle-wrapper.jar'}
        rows = raw.split(b'\x00')
        if not raw.endswith(b'\x00') or len(rows) != 5 or \
                any(rows[i] != b'D' for i in (0, 2)) or {rows[1], rows[3]} != expected:
            raise ValueError('QUALIFICATION_PREPARED_RUNTIME_DIRTY')
    else:
        subprocess.run(['git', '-C', str(submodule), 'diff', '--exit-code', 'HEAD', '--'], check=True,
                       stdout=subprocess.DEVNULL)


def inspect(root, prepared_source=None):
    submodule = root / 'runtime-llama/src/main/cpp/llama.cpp'
    commit = subprocess.check_output(['git', '-C', str(submodule), 'rev-parse', 'HEAD'], text=True).strip()
    check_runtime_source(root, prepared_source)
    paths = runtime_inputs(root)
    descriptor = json.loads((root / 'app/src/main/assets/model/rune-text-0.1.json').read_text())
    return {'runtimeBuildId': fingerprint(root, paths, commit), 'runtimeApi': descriptor['runtimeApi'],
            'modelSha256': descriptor['sha256'], 'llamaCommit': commit,
            'runtimeFiles': {p: sha(root / p) for p in paths}}


def verify(root, prepared_source=None):
    record = inspect(root, prepared_source)
    contract = (root / 'app/src/main/java/io/github/mesteriis/rune/keyboard/intelligence/ipc/ScoringContract.kt').read_text()
    for name, key in [('MODEL_SHA256', 'modelSha256'), ('RUNTIME_BUILD_ID', 'runtimeBuildId'),
                      ('RUNTIME_API', 'runtimeApi')]:
        value = re.search(r'const val ' + name + r' = ("[^"]+"|\d+)', contract)
        if not value or json.loads(value[1]) != record[key]:
            raise ValueError('QUALIFICATION_METADATA_DRIFT:' + name)
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--receipt', type=Path)
    parser.add_argument('--prepared-source', choices=['fdroidserver-2.4.5'])
    args = parser.parse_args()
    record = verify(args.root.resolve(), args.prepared_source)
    if args.receipt:
        args.receipt.write_text(json.dumps(record, sort_keys=True, indent=2) + '\n')
    print('Qualification artifact metadata verified: ' + record['runtimeBuildId'])
