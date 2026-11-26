"""Screen static project imports absent from recorded role-model source bindings."""
import ast
import json
from pathlib import Path
import subprocess

import verify_role_model_sources as inventory

ROOT = Path(__file__).resolve().parents[2]


def static_imports_by_scope(path):
    tree = ast.parse(Path(path).read_bytes(), filename=str(path))
    top_level, nested = set(), set()
    for statement in tree.body:
        for node in ast.walk(statement):
            destination = top_level if node is statement else nested
            if isinstance(node, ast.Import):
                destination.update(alias.name.split('.')[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                destination.add(node.module.split('.')[0])
    return top_level, nested


def static_imports(path):
    top_level, nested = static_imports_by_scope(path)
    return top_level | nested


def missing_for_sources(paths, bound, project_modules):
    missing = set()
    for path in paths:
        missing.update((static_imports(path) & project_modules) - bound)
    return sorted(missing)


def audit(root):
    root = Path(root).resolve()
    inventory.verify(root)
    files = subprocess.check_output(['git', 'ls-files', 'tools/typing_experiments', 'tools/morphology'],
                                    cwd=root, text=True).splitlines()
    project_modules = {Path(name).stem for name in files if name.endswith('.py')
                       and '/frozen_sources/' not in name and '/late_training_sources/' not in name
                       and not Path(name).name.startswith('test_')}
    data = json.loads((root / inventory.INVENTORY).read_bytes())
    findings = []
    for record in data['records']:
        bound = {Path(source['originalName']).stem for source in record['sourceBindings']}
        paths = [root / source['trackedPath'] for source in record['sourceBindings']]
        missing = missing_for_sources(paths, bound, project_modules)
        top_level = set()
        for path in paths:
            direct, _ = static_imports_by_scope(path)
            top_level.update((direct & project_modules) - bound)
        findings.append({'model': record['model'], 'unboundStaticImports': missing,
                         'unboundTopLevelImports': sorted(top_level)})
    return {'scope': 'static-project-import-screen', 'models': findings,
            'unboundModelImportPairs': sum(len(item['unboundStaticImports']) for item in findings),
            'transitiveClosureEstablished': False, 'historicalExecutionEstablished': False}


if __name__ == '__main__':
    print(json.dumps(audit(ROOT), indent=2, sort_keys=True))
