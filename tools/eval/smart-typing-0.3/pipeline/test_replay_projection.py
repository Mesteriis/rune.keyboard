import copy
import gzip
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import replay_projection as replay


def observation():
    return {'index': 0, 'id': 'synthetic', 'language': 'en', 'split': 'calibration',
        'prefix': 'go', 'typed': 'hom', 'status': 'COMPLETE',
        'beforeBoundary': {'text': 'go hom', 'caret': 6},
        'afterBoundary': {'text': 'go home ', 'caret': 8},
        'afterBackspace': {'text': 'go hom', 'caret': 6},
        'boundaryCommands': [{'commit': 'home '}], 'backspaceCommands': [{'restore': 'hom'}],
        'stateAfterBoundary': {'suggestions': ['home', 'hom'], 'allowed': True},
        'stateAfterBackspace': {'suggestions': []},
        'fullTokenGenerationNanos': 10, 'hostStageNanos': {'baseline': 20}}


class ReplayProjectionTest(unittest.TestCase):
    def read(self, root, name, rows):
        path = root / name
        path.write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
        return path, replay.read_projection(path)

    def test_only_two_top_level_host_timings_are_excluded(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            old = observation(); new = copy.deepcopy(old)
            new.update(fullTokenGenerationNanos=999, hostStageNanos={'baseline': 888})
            _, first = self.read(root, 'first', [old]); _, second = self.read(root, 'second', [new])
            result = replay.compare(first, second)
            self.assertTrue(result['passed'])
            self.assertEqual(result['baselineProjectionSha256'], result['candidateProjectionSha256'])
            for field in ('otherNanos', 'reportedModelMillis'):
                changed = copy.deepcopy(second); changed[0][field] = 1
                self.assertFalse(replay.compare(first, changed)['passed'])
            changed = copy.deepcopy(second); changed[0]['stateAfterBoundary']['hostStageNanos'] = 1
            self.assertFalse(replay.compare(first, changed)['passed'])

    def test_text_commands_suggestion_order_source_and_allowed_drift_are_all_reported(self):
        before = observation(); after = copy.deepcopy(before)
        after['afterBoundary']['text'] = 'go hom '
        after['backspaceCommands'][0]['restore'] = 'wrong'
        after['stateAfterBoundary']['suggestions'].reverse()
        after['stateAfterBoundary']['allowed'] = False
        after['automaticSource'] = 'changed'
        result = replay.compare([before], [after])
        self.assertEqual(1, result['differentRows'])
        self.assertEqual(1, result['differences'][0]['row'])
        self.assertEqual({'/afterBoundary/text', '/backspaceCommands/0/restore',
            '/stateAfterBoundary/suggestions/0', '/stateAfterBoundary/suggestions/1',
            '/stateAfterBoundary/allowed', '/automaticSource'}, set(result['differences'][0]['paths']))

    def test_boolean_and_numeric_type_changes_are_not_equal(self):
        for before, after in ((True, 1), (1, 1.0), (False, 0)):
            self.assertEqual(['/x'], replay.changed_paths({'x': before}, {'x': after}))

    def test_extra_or_removed_row_fails_with_its_row_number(self):
        for old, new in (([observation()], []), ([], [observation()])):
            result = replay.compare(old, new)
            self.assertFalse(result['passed'])
            self.assertEqual(1, result['differentRows'])
            self.assertEqual(['/'], result['differences'][0]['paths'])

    def test_missing_incomplete_duplicate_reordered_or_empty_observations_fail_closed(self):
        cases = [[], [dict(observation(), status='ERROR')], [dict(observation(), index=True)],
            [dict(observation(), index=1)], [dict(observation(), id='')],
            [dict(observation(), language='fr')], [dict(observation(), split='future')],
            [observation(), dict(observation(), index=1)],
            [{k: v for k, v in observation().items() if k != 'afterBackspace'}]]
        with tempfile.TemporaryDirectory() as folder:
            for index, rows in enumerate(cases):
                with self.subTest(index=index), self.assertRaises(ValueError):
                    self.read(Path(folder), str(index), rows)

    def test_nonfinite_and_duplicate_json_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'bad.jsonl'
            for value in ('{"id":"a","id":"b"}', '{"score":NaN}', '{"score":Infinity}'):
                path.write_text(value + '\n')
                with self.assertRaises(ValueError): replay.read_projection(path)

    def test_overflowed_finite_json_literal_is_rejected_before_projection(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'overflow.jsonl'
            path.write_text(json.dumps(observation())[:-1] + ', "score":1e400}\n')
            with self.assertRaises(ValueError): replay.read_projection(path)

    def test_cli_returns_failure_and_writes_nested_row_diff_without_overwriting_baseline(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); old = observation(); new = copy.deepcopy(old)
            new['stateAfterBoundary']['allowed'] = False
            baseline, _ = self.read(root, 'baseline.jsonl', [old])
            candidate, _ = self.read(root, 'candidate.jsonl', [new])
            report = root / 'diff.json'; original = baseline.read_bytes()
            command = [sys.executable, str(Path(replay.__file__)), '--baseline', str(baseline),
                '--candidate', str(candidate), '--report', str(report)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(1, result.returncode)
            self.assertEqual(['/stateAfterBoundary/allowed'], json.loads(report.read_text())['differences'][0]['paths'])
            self.assertEqual(original, baseline.read_bytes())
            self.assertEqual(2, subprocess.run(command, capture_output=True).returncode)

    def test_gzip_and_plain_have_identical_projection_and_bounded_decoding(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            plain, rows = self.read(root, 'plain.jsonl', [observation()])
            compressed = root / 'baseline.jsonl.gz'
            compressed.write_bytes(gzip.compress(plain.read_bytes(), mtime=0))
            self.assertTrue(replay.compare(rows, replay.read_projection(compressed))['passed'])
            for setting in ('MAX_LINE_BYTES', 'MAX_TOTAL_BYTES'):
                with mock.patch.object(replay, setting, 8), self.assertRaisesRegex(ValueError, 'SIZE_LIMIT'):
                    replay.read_projection(compressed)
            compressed.write_bytes(b'not gzip')
            with self.assertRaises(OSError): replay.read_projection(compressed)

    def test_canonical_projection_preserves_unicode_newlines_and_json_pointer_escaping(self):
        row = observation(); row['typed'] = 'ещё\n🙂'
        self.assertIn('ещё'.encode(), replay.projection_bytes([row]))
        self.assertEqual(['/a~1b~0c'], replay.changed_paths({'a/b~c': 1}, {'a/b~c': 2}))
