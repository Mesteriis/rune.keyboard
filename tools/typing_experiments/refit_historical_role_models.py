"""Refit the historical v5/v6 role models from verified groups and count tables."""

import argparse
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from recover_role_training_groups import EXPERIMENTS, REVISION, ROOT, digest, export_revision, verify


COUNTS = ('context-ranking-20261025/counts-v3/model-counts.jsonl',
          'context-feature-ranker-20261026/tatoeba-train-counts.jsonl')
LINEAGE = EXPERIMENTS / 'historical_provenance_sources/v6-inputs/role-training-v5-v6-lineage.json'
RECORD_IMPORTS = """
_refit_source_root = Path.cwd()
_refit_imports = {}
for _refit_name, _refit_module in tuple(sys.modules.items()):
    _refit_file = getattr(_refit_module, '__file__', None)
    if not _refit_file or _refit_name == '__main__':
        continue
    _refit_source = Path(_refit_file).resolve()
    if _refit_source.is_relative_to(_refit_source_root):
        _refit_imports[_refit_name] = {
            'path': _refit_source.relative_to(_refit_source_root).as_posix(),
            'sha256': hashlib.sha256(_refit_source.read_bytes()).hexdigest(),
        }
Path(__file__).with_name('imports.json').write_text(
    json.dumps(_refit_imports, sort_keys=True), encoding='utf-8')
"""


def archived_source(path, expected, sources):
    if path.startswith('build/'):
        return EXPERIMENTS / 'late_training_sources' / f'train_{expected[:16]}.py'
    return sources / path


def verify_imports(path, sources):
    imports = json.loads(path.read_bytes())
    if not imports:
        raise ValueError('ROLE_REFIT_IMPORTS_EMPTY')
    for record in imports.values():
        relative = Path(record['path'])
        source = (sources / relative).resolve()
        if not source.is_relative_to(sources) or source.relative_to(sources) != relative:
            raise ValueError('ROLE_REFIT_IMPORT_PATH')
        historical = subprocess.run(
            ['git', 'cat-file', 'blob', f'{REVISION}:{relative.as_posix()}'], cwd=ROOT,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10)
        if historical.returncode or sha256(historical.stdout).hexdigest() != record['sha256']:
            raise ValueError(f'ROLE_REFIT_IMPORT_IDENTITY:{relative}')
        verify(source, record['sha256'], 'ROLE_REFIT_IMPORT_IDENTITY')
    return imports


def fit(sources, stage, runner):
    driver = stage / 'refit.py'
    driver.write_text(runner + '\n' + RECORD_IMPORTS, encoding='utf-8')
    subprocess.run([sys.executable, '-B', str(driver)], cwd=sources,
                   check=True, timeout=900)
    return verify_imports(stage / 'imports.json', sources)


def v5_stages(trainer):
    # The historical receipt checks precede the vectorization and fit. The
    # caller checks the recovered computational inputs against frozen digests.
    code = trainer.read_text(encoding='utf-8')
    preamble = code.index("selection=load(root/'selection.json')")
    count_paths = code.index('counts=[', preamble)
    receipt_checks = code.index('previous=load(', count_paths)
    computation = code.index('groups=[json.loads(line)', receipt_checks)
    epilogue = code.index("write('frozen-model.json'", computation)
    return (code[:preamble] + code[count_paths:receipt_checks]
            + 'lex=PymorphyLexicon(cache_size=16384)\n' + code[computation:epilogue])


def v6_stages(trainer):
    code = trainer.read_text(encoding='utf-8')
    preamble = code.index("frozen=load(parent/'frozen-model.json')")
    computation = code.index('data=np.load(', preamble)
    epilogue = code.index("write('frozen-model.json'", computation)
    return code[:preamble] + "plan=load(root/'plan.json')\n" + code[computation:epilogue]


def refit(groups, counts, output):
    lineage = json.loads(LINEAGE.read_bytes())
    shared = lineage['shared']
    v5, v6 = (lineage['versions'][name] for name in ('v5', 'v6'))
    verify(groups, shared['groupsSha256'], 'ROLE_GROUPS_IDENTITY')
    for path, expected in zip(counts, shared['countsSha256'], strict=True):
        verify(path, expected, 'ROLE_COUNT_TABLE_IDENTITY')
    for name, required in [('numpy', '2.2.6'), ('catboost', '1.2.8')]:
        if version(name) != required:
            raise ValueError('ROLE_FIT_DEPENDENCY:' + name)

    with tempfile.TemporaryDirectory(prefix='.rune-role-refit-', dir=output.parent) as directory:
        temporary = Path(directory)
        sources = temporary / 'source'
        export_revision(sources)
        for path, expected in v6['featureSources'].items():
            verify(archived_source(path, expected, sources), expected, 'ROLE_FEATURE_SOURCE_IDENTITY')
        assets = sources / 'app/src/main/assets/smarttyping/experiments'
        for name, expected in shared['installedAssets'].items():
            verify(assets / name, expected, 'ROLE_ASSET_IDENTITY')
        for name, path, expected in zip(COUNTS, counts, shared['countsSha256'], strict=True):
            local = sources / 'build' / name
            local.parent.mkdir(parents=True)
            shutil.copyfile(path, local)
            verify(local, expected, 'ROLE_COUNT_TABLE_IDENTITY')
        stages = [sources / f'build/right-context-training-{name}-20261027' for name in ('v5', 'v6')]
        old, new = stages
        old.mkdir()
        new.mkdir()
        shutil.copyfile(groups, old / 'groups.jsonl')
        verify(old / 'groups.jsonl', shared['groupsSha256'], 'ROLE_GROUPS_IDENTITY')
        old_source = v5['featureSources']['build/right-context-training-v5-20261027/train.py']
        new_source = v6['featureSources']['build/right-context-training-v6-20261027/train.py']
        v5_imports = fit(sources, old, v5_stages(archived_source('build/train.py', old_source, sources)))
        vectors = old / 'train-vectors.npz'
        verify(vectors, shared['vectorsSha256'], 'ROLE_VECTORS_IDENTITY')
        verify(old / 'experimental-ranker.bin', v5['modelSha256'], 'ROLE_V5_MODEL_IDENTITY')

        plan = json.loads((old / 'plan.json').read_bytes())
        if plan['depth'] != v5['depth'] or plan['features'] != v6['featureCount']:
            raise ValueError('ROLE_FIT_LAYOUT')
        plan['depth'] = v6['depth']
        (new / 'plan.json').write_text(json.dumps(plan), encoding='utf-8')
        shutil.copyfile(old / 'groups.jsonl', new / 'groups.jsonl')
        shutil.copyfile(vectors, new / vectors.name)
        v6_imports = fit(sources, new, v6_stages(archived_source('build/train.py', new_source, sources)))
        verify(new / 'experimental-ranker.bin', v6['modelSha256'], 'ROLE_V6_MODEL_IDENTITY')

        result = temporary / 'verified'
        result.mkdir()
        shutil.move(vectors, result / vectors.name)
        receipt = {'sourceCommit': REVISION, 'groupsSha256': shared['groupsSha256'],
                   'vectorsSha256': shared['vectorsSha256'], 'qualified': False, 'models': {},
                   'projectModulesPresentAfterFit': {'v5': v5_imports, 'v6': v6_imports}}
        for name, stage, binding in zip(('v5', 'v6'), stages, (v5, v6), strict=True):
            model = stage / 'experimental-ranker.bin'
            if model.stat().st_size != binding['modelBytes']:
                raise ValueError('ROLE_MODEL_SIZE:' + name)
            receipt['models'][name] = {'bytes': model.stat().st_size, 'sha256': digest(model)}
            shutil.move(model, result / f'{name}-experimental-ranker.bin')
        (result / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
        result.rename(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--groups', type=Path, required=True)
    parser.add_argument('--wiki-counts', type=Path, required=True)
    parser.add_argument('--tatoeba-counts', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='Fresh directory under build/')
    args = parser.parse_args()
    output = args.output.resolve()
    if ROOT / 'build' not in output.parents or output.exists():
        parser.error('--output must be a fresh directory under build/')
    output.parent.mkdir(parents=True, exist_ok=True)
    counts = (args.wiki_counts.resolve(strict=True), args.tatoeba_counts.resolve(strict=True))
    refit(args.groups.resolve(strict=True), counts, output)


if __name__ == '__main__':
    main()
