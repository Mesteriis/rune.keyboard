"""Reproduce the shared historical v5/v6 groups from the archived authored inputs."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tarfile
import tempfile


ROOT = Path(__file__).resolve().parents[2]
REVISION = '3bd893ca175bf7c62760611d09c0dab7e5d1fe68'
EXPERIMENTS = ROOT / 'tools/typing_experiments'
FEATURES = Path('tools/typing_experiments/right_context_role_features.py')
V4_FEATURES = '2442a38501946f6fcaad293a99b11d0ad785123efb1fe207b03beb5332a841d0'
REPLAY = 'tools/eval/smart-typing-0.3/pipeline/final_product_replay.py'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify(path, expected, code):
    if digest(path) != expected:
        raise ValueError(f'{code}:{path.name}')


def read_jsonl(path):
    with path.open(encoding='utf-8') as stream:
        return [json.loads(line) for line in stream]


def export_revision(source):
    # A depth-one CI checkout can fetch the pinned commit without attaching it
    # to a ref. Export it directly from the repository that fetched its tree.
    source.mkdir()
    with tempfile.TemporaryFile() as snapshot:
        subprocess.run(['git', 'archive', '--format=tar', REVISION], cwd=ROOT,
                       stdout=snapshot, check=True, timeout=120)
        snapshot.seek(0)
        with tarfile.open(fileobj=snapshot, mode='r:') as archive:
            archive.extractall(source, filter='data')


def prepare_rows(source, bindings, archive):
    features = source / FEATURES
    v5_features = features.read_bytes()
    v4_features = archive / f'right_context_role_features_{V4_FEATURES[:16]}.py'
    verify(v4_features, V4_FEATURES, 'ROLE_V4_FEATURE_SOURCE')
    shutil.copyfile(v4_features, features)
    for version in (4, 5):
        name = f'build/right-context-training-v{version}-20261027'
        stage = source / name
        stage.mkdir(parents=True)
        preparer_sha = bindings[f'{name}/prepare.py']
        preparer = archive / f'prepare_{preparer_sha[:16]}.py'
        verify(preparer, preparer_sha, 'ROLE_AUTHORED_PREPARER')
        shutil.copyfile(preparer, stage / 'prepare.py')
        subprocess.run([sys.executable, '-B', f'{name}/prepare.py'], cwd=source,
                       check=True, stdout=subprocess.DEVNULL, timeout=120)
        verify(stage / 'corpus/train.jsonl', bindings[f'{name}/corpus/train.jsonl'],
               'ROLE_AUTHORED_ROWS')
        features.write_bytes(v5_features)
    return stage


def compiler_inputs(replay, java):
    version = subprocess.run([java, '-version'], capture_output=True, check=True, timeout=15)
    if b'version "17.' not in version.stderr:
        raise ValueError('JAVA_17_REQUIRED')
    android_home = os.environ.get('ANDROID_HOME') or os.environ.get('ANDROID_SDK_ROOT')
    if not android_home:
        raise ValueError('ANDROID_HOME_MISSING')
    android = (Path(android_home) / 'platforms/android-37.0/android.jar').resolve(strict=True)
    gradle_home = Path(os.environ.get('GRADLE_USER_HOME', str(Path.home() / '.gradle'))).expanduser()
    cache = gradle_home / 'caches/modules-2/files-2.1'
    jars = []
    for item in json.loads(replay['TOOLCHAIN'].read_bytes())['jars']:
        directory = cache / item['group'] / item['artifact'] / item['version']
        matched = [path for path in directory.glob('*/*.jar') if digest(path) == item['sha256']]
        if len(matched) != 1:
            raise ValueError('PINNED_KOTLIN_CACHE:' + item['artifact'])
        jars.append(matched[0])
    sources = replay['final_product_sources']()
    diagnostics = (replay['REPO'] / 'app/src/main/java/io/github/mesteriis/rune/keyboard'
                   / 'smarttyping/diagnostics/TypingDiagnostics.kt')
    if diagnostics not in sources:
        sources.append(diagnostics)
    sources.append(replay['HARNESS'])
    return sources, jars, android


def recover(java, output):
    bindings = json.loads((ROOT / 'docs/acceptance/2026-10-27-late-authored-history-evidence.json')
                          .read_bytes())['receipt']['bindings']
    lineage = json.loads((EXPERIMENTS / 'historical_provenance_sources/v6-inputs'
                          / 'role-training-v5-v6-lineage.json').read_bytes())['shared']
    with tempfile.TemporaryDirectory(prefix='.rune-role-training-', dir=output.parent) as directory:
        temporary = Path(directory)
        source = temporary / 'source'
        export_revision(source)
        stage = prepare_rows(source, bindings, EXPERIMENTS / 'frozen_sources')
        replay = runpy.run_path(str(source / REPLAY))
        select_groups = runpy.run_path(str(source / 'tools/typing_experiments/right_context_training_groups.py'))[
            'select_groups']
        sources, jars, android = compiler_inputs(replay, java)
        jar, _ = replay['compile_harness'](temporary, java, sources, jars, android)
        observations = temporary / 'observations.jsonl'
        queries = stage / 'queries.tsv'
        replay['run_harness'](temporary, java, jars, android, jar, queries, observations,
                              'noun-case-production')
        observed = read_jsonl(observations)
        groups, skips = select_groups(read_jsonl(stage / 'corpus/train.jsonl'), observed)
        result = temporary / 'verified'
        result.mkdir()
        group_file = result / 'groups.jsonl'
        with group_file.open('x', encoding='utf-8', newline='\n') as stream:
            for group in groups:
                stream.write(json.dumps(group, ensure_ascii=False) + '\n')
        verify(group_file, lineage['groupsSha256'], 'ROLE_GROUPS_IDENTITY')
        candidate_rows = sum(len(group['candidates']) for group in groups)
        if (len(groups), candidate_rows) != (lineage['trainingGroups'], lineage['candidateRows']):
            raise ValueError('ROLE_GROUP_COUNTS')
        receipt = {'sourceCommit': REVISION, 'groupsSha256': digest(group_file),
                   'groups': len(groups), 'candidateRows': candidate_rows, 'queries': len(observed),
                   'querySha256': digest(queries), 'skipped': skips, 'qualified': False}
        (result / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
        result.rename(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java', type=Path, required=True, help='Path to the Java 17 launcher')
    parser.add_argument('--output', type=Path, required=True, help='Fresh directory under build/')
    args = parser.parse_args()
    output = args.output.resolve()
    if ROOT / 'build' not in output.parents or output.exists():
        parser.error('--output must be a fresh directory under build/')
    output.parent.mkdir(parents=True, exist_ok=True)
    recover(args.java.resolve(strict=True), output)


if __name__ == '__main__':
    main()
