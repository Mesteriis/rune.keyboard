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


def inspect(root):
    submodule = root / 'runtime-llama/src/main/cpp/llama.cpp'
    commit = subprocess.check_output(['git', '-C', str(submodule), 'rev-parse', 'HEAD'], text=True).strip()
    subprocess.run(['git', '-C', str(submodule), 'diff', '--exit-code', 'HEAD', '--'], check=True,
                   stdout=subprocess.DEVNULL)
    paths = runtime_inputs(root)
    descriptor = json.loads((root / 'app/src/main/assets/model/rune-text-0.1.json').read_text())
    return {'runtimeBuildId': fingerprint(root, paths, commit), 'runtimeApi': descriptor['runtimeApi'],
            'modelSha256': descriptor['sha256'], 'llamaCommit': commit,
            'runtimeFiles': {p: sha(root / p) for p in paths}}


def verify(root):
    record = inspect(root)
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
    args = parser.parse_args()
    record = verify(args.root.resolve())
    if args.receipt:
        args.receipt.write_text(json.dumps(record, sort_keys=True, indent=2) + '\n')
    print('Qualification artifact metadata verified: ' + record['runtimeBuildId'])
