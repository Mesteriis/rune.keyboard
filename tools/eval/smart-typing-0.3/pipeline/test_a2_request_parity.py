import copy
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import final_product_replay as replay
from a2_request_parity import compare_requests


class RequestParityTest(unittest.TestCase):
    def test_request_bindings_do_not_require_native_scoring_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runner, model = root / 'runner', root / 'model'
            android = root / 'android.jar'
            android.write_bytes(b'compile stub')
            rows = [{'id': 'one', 'split': 'holdout'}]
            with (mock.patch.multiple(replay, RUNNER=runner, MODEL=model, JDK_RUNTIME_INVENTORY=()),
                  mock.patch.object(replay, 'java_runtime_binding', return_value={'home': str(root)}),
                  mock.patch.object(replay, 'asset_paths', return_value=[]),
                  mock.patch.object(replay, 'compact_asset_paths', return_value=[])):
                binding = replay.immutable_bindings(root / 'java', [], [], android, rows,
                                                    bind_native_model=False)
                self.assertNotIn('model', binding)
                self.assertNotIn('runner', binding)
                self.assertEqual(replay.sha256(android), binding['files'][replay.path_key(android)])
                with self.assertRaises(FileNotFoundError):
                    replay.immutable_bindings(root / 'java', [], [], android, rows)
                runner.write_bytes(b'bad runner')
                model.write_bytes(b'bad model')
                with self.assertRaisesRegex(ValueError, 'RUNNER_IDENTITY'):
                    replay.immutable_bindings(root / 'java', [], [], android, rows)
                with mock.patch.object(replay, 'RUNNER_SHA256', replay.sha256(runner)):
                    with self.assertRaisesRegex(ValueError, 'MODEL_IDENTITY'):
                        replay.immutable_bindings(root / 'java', [], [], android, rows)

    def test_checks_requests_and_missing_requests_in_order(self):
        request = {'sessionId': 1, 'revision': 2, 'requestId': 3, 'prefix': 'hello ',
                   'candidateIds': [0, 1], 'continuations': ['helo', 'hello']}
        rows = [{'id': 'one', 'split': 'holdout', 'language': 'en', 'actualModelRequest': request},
                {'id': 'two', 'split': 'calibration', 'language': 'ru', 'actualModelRequest': None}]
        self.assertEqual({'holdout': 1, 'calibration': 0}, compare_requests(rows, copy.deepcopy(rows)))
        for mutate in (lambda x: x[0]['actualModelRequest'].update(prefix='other '),
                       lambda x: x[1].update(actualModelRequest=request),
                       lambda x: x[0].update(language='es'),
                       lambda x: x.reverse()):
            changed = copy.deepcopy(rows)
            mutate(changed)
            with self.assertRaises(ValueError):
                compare_requests(rows, changed)
