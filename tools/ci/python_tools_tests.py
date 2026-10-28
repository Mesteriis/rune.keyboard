"""Run the versioned Q7 test inventory, one module per interpreter process."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(__file__).with_name('python-tools-tests.json')
SCOPES = ('tools/typing_experiments/test_*.py', 'tools/morphology/test_*.py',
          'tools/test_qualification_artifacts.py')
PROFILES = ('stdlib', 'scientific', 'historical-artifacts')


def validate(root=ROOT, manifest=MANIFEST):
    data = json.loads(manifest.read_text())
    if data.get('schemaVersion') != 1 or set(data.get('profiles', {})) != set(PROFILES):
        raise ValueError('INVALID_TEST_INVENTORY')
    assigned = []
    for profile in PROFILES:
        paths = data['profiles'][profile]
        if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
            raise ValueError('INVALID_TEST_PATHS')
        if paths != sorted(set(paths)):
            raise ValueError('UNSORTED_OR_DUPLICATE_TEST_PATHS')
        assigned.extend(paths)
    tracked = subprocess.check_output(
        ['git', 'ls-files', '--', *SCOPES], cwd=root, text=True).splitlines()
    if not tracked or len(assigned) != len(set(assigned)) or set(assigned) != set(tracked):
        raise ValueError('TEST_INVENTORY_DRIFT: missing=' +
                         repr(sorted(set(tracked) - set(assigned))) + ' stale=' +
                         repr(sorted(set(assigned) - set(tracked))))
    for name in assigned:
        path = root / name
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('TEST_SOURCE_UNAVAILABLE: ' + name)
    return data


def run(profile, output, *, root=ROOT, manifest=MANIFEST, timeout=240):
    data = validate(root, manifest)
    output.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    results = []
    receipt = {'schemaVersion': 1, 'profile': profile, 'modules': results, 'status': 'RUNNING'}
    for name in data['profiles'][profile]:
        path = Path(name)
        summary_path = output.resolve() / (name.replace('/', '__') + '.json')
        command = [sys.executable, str(Path(__file__).with_name('python_tools_test_child.py')),
                   str(path), str(summary_path)]
        start = time.monotonic()
        timed_out = False
        with (output / (name.replace('/', '__') + '.log')).open('wb') as log:
            try:
                child = subprocess.run(command, cwd=root, env=env, stdout=log,
                                       stderr=subprocess.STDOUT, timeout=timeout)
                code = child.returncode
            except subprocess.TimeoutExpired:
                code, timed_out = 124, True
        summary = json.loads(summary_path.read_text()) if summary_path.exists() else None
        if code == 0 and (summary is None or summary['tests'] < 1):
            code = 1
        results.append({'path': name, 'exitCode': code, 'timedOut': timed_out,
                        'seconds': time.monotonic() - start, 'unittest': summary})
        receipt = {'schemaVersion': 1, 'profile': profile, 'modules': results,
                   'status': 'RUNNING'}
        (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(name, 'exit=' + str(code), flush=True)
    receipt['status'] = 'PASS' if results and all(r['exitCode'] == 0 for r in results) else 'FAIL'
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return 0 if receipt['status'] == 'PASS' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=PROFILES)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        data = validate()
        print(json.dumps({p: len(data['profiles'][p]) for p in PROFILES}, sort_keys=True))
        return 0
    if not args.profile or not args.output:
        parser.error('--profile and --output are required without --check')
    return run(args.profile, args.output)


if __name__ == '__main__':
    sys.exit(main())
