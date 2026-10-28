"""Require real pinned backends and reject skipped/missing backend test cases."""
import argparse
from contextlib import redirect_stderr, redirect_stdout
from importlib import metadata
import json
import hashlib
from pathlib import Path
import platform
import sys
import traceback
import unittest

ROOT = Path(__file__).resolve().parents[2]
VERSIONS = {
    'mlx': {'numpy': '2.4.6', 'pyarrow': '25.0.1', 'mlx': '0.32.2', 'mlx-metal': '0.32.2'},
    'pymorphy': {'pymorphy3': '2.0.6', 'pymorphy3-dicts-ru': '2.4.417150.4580142', 'dawg2-python': '0.9.0', 'setuptools': '84.2.1'},
}
REQUIRED = {
    'mlx': {'test_word_ranking.WordRankingTests.test_mlx_loss_parity_initialization_and_finite_gradient'},
    'pymorphy': {'backend_cases.LivePymorphyTest.' + name for name in (
        'test_dictionary_inflections_and_all_ambiguous_lemmas',
        'test_guesses_and_unsupported_tokens_never_become_evidence',
        'test_context_decisions_use_real_dictionary_analyses',
        'test_case_normalization_and_bounded_live_lookup_cache',
        'test_receipt_binds_installed_dictionary_and_code')},
}


def preflight(backend):
    versions = {name: metadata.version(name) for name in VERSIONS[backend]}
    if versions != VERSIONS[backend]:
        raise ValueError('BACKEND_VERSION_MISMATCH')
    if backend == 'mlx':
        if sys.platform != 'darwin' or platform.machine() != 'arm64':
            raise ValueError('MLX_MACOS_ARM64_REQUIRED')
        import mlx.core as mx
        mx.set_default_device(mx.cpu)
    return versions


def load_suite(backend):
    if backend == 'mlx':
        sys.path.insert(0, str(ROOT / 'tools/typing_experiments'))
        return unittest.defaultTestLoader.loadTestsFromName('test_word_ranking.WordRankingTests')
    return unittest.defaultTestLoader.loadTestsFromName('backend_cases.LivePymorphyTest')


def test_ids(suite):
    result = []
    for test in suite:
        result.extend(test_ids(test) if isinstance(test, unittest.TestSuite) else [test.id()])
    return result


def execute(suite, required):
    ids = test_ids(suite)
    if not ids or len(ids) != len(set(ids)) or not required <= set(ids):
        raise ValueError('REQUIRED_BACKEND_TEST_MISSING')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    summary = {'tests': result.testsRun, 'ids': ids,
               'failures': [test.id() for test, _ in result.failures],
               'errors': [test.id() for test, _ in result.errors],
               'expectedFailures': [test.id() for test, _ in result.expectedFailures],
               'unexpectedSuccesses': [test.id() for test in result.unexpectedSuccesses],
               'skipped': [{'test': test.id(), 'reason': reason} for test, reason in result.skipped]}
    passed = (result.wasSuccessful() and not result.skipped and not result.expectedFailures
              and not result.unexpectedSuccesses and result.testsRun == len(ids))
    return passed, summary


def input_bindings(backend):
    names = ['tools/ci/backend_test_gate.py']
    if backend == 'mlx':
        names += ['tools/typing_experiments/test_word_ranking.py',
                  'tools/typing_experiments/word_ranking.py',
                  'tools/typing_experiments/neural_refinement.py',
                  'app/src/main/assets/smarttyping/experiments/ru-ranking-context.bin',
                  'tools/typing_experiments/requirements-neural.txt']
    else:
        names += ['tools/ci/backend_cases.py', 'tools/morphology/ranker.py',
                  'tools/morphology/test_ranker.py', 'tools/morphology/requirements.lock']
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}


def run(backend, output):
    output.mkdir(parents=True, exist_ok=False)
    receipt = {'schemaVersion': 1, 'backend': backend, 'status': 'FAIL',
               'versions': None, 'unittest': None, 'device': None, 'inputBindings': None}
    with (output / 'tests.log').open('w') as log, redirect_stdout(log), redirect_stderr(log):
        try:
            receipt['inputBindings'] = input_bindings(backend)
            receipt['versions'] = preflight(backend)
            receipt['device'] = 'cpu' if backend == 'mlx' else None
            passed, receipt['unittest'] = execute(load_suite(backend), REQUIRED[backend])
            if passed:
                if input_bindings(backend) != receipt['inputBindings']:
                    raise ValueError('BACKEND_INPUT_CHANGED')
                if backend == 'pymorphy':
                    from ranker import PymorphyLexicon
                    receipt['dictionary'] = PymorphyLexicon().receipt()
                receipt['status'] = 'PASS'
        except Exception as error:
            receipt['errorType'] = type(error).__name__
            traceback.print_exc()
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(backend, receipt['status'])
    return 0 if receipt['status'] == 'PASS' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', choices=VERSIONS, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    sys.exit(run(args.backend, args.output))
