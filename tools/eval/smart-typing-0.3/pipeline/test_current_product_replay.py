import json
from pathlib import Path
import re
import os
import subprocess
import tempfile
import unittest
from unittest import mock

import current_product_replay as replay


class CurrentProductReplayTest(unittest.TestCase):
    def test_java_is_explicit_and_has_no_machine_local_default(self):
        with self.assertRaises(SystemExit):
            replay.parser().parse_args(['--rows', 'rows.jsonl', '--output', 'build/replay'])
        args = replay.parser().parse_args(['--java', '/jdk/bin/java', '--rows', 'en.jsonl',
            '--rows', 'ru.jsonl', '--output', 'build/replay'])
        self.assertEqual(Path('/jdk/bin/java'), args.java)
        self.assertEqual([Path('en.jsonl'), Path('ru.jsonl')], args.rows)

    def test_expected_labels_and_extra_fields_never_enter_input_projection(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'rows.jsonl'
            row = {'id': 'en-example', 'split': 'calibration', 'language': 'en', 'prefix': 'go',
                'typed': 'home', 'expected': 'injected', 'candidates': ['injected'], 'noAuto': True}
            path.write_text(json.dumps(row) + '\n')
            selected = replay.load_inputs([path])[0]
            self.assertEqual('replay-00000000', selected['id'])
            self.assertEqual('en-example', selected['sourceId'])
            self.assertEqual({key: row[key] for key in ('split', 'language', 'prefix', 'typed')},
                {key: selected[key] for key in ('split', 'language', 'prefix', 'typed')})
            row['expected'] = 'another injected value'; row['noAuto'] = False
            path.write_text(json.dumps(row) + '\n')
            self.assertEqual('home', replay.load_inputs([path])[0]['typed'])
            self.assertNotIn('expected', replay.load_inputs([path])[0])

    def test_duplicate_ids_wrong_scope_and_non_string_payloads_fail(self):
        base = {'id': 'id', 'split': 'holdout', 'language': 'es', 'prefix': 'hola', 'typed': 'amigo'}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'rows.jsonl'
            for rows in ([], [base, base], [dict(base, typed=1)], [dict(base, split='unknown')],
                         [dict(base, language='unknown')], [dict(base, id='')]):
                path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
                with self.assertRaises(ValueError): replay.load_inputs([path])

    def test_every_android_automatic_decision_callback_has_a_host_implementation(self):
        # A new Android source callback must also be represented by this host observer.
        pattern = r'override fun (\w+AutomaticDecision)\s*\('
        android = set(re.findall(pattern, replay.ANDROID_PERSONALIZATION.read_text()))
        host = set(re.findall(pattern, replay.harness.HARNESS.read_text()))
        self.assertEqual(8, len(android))
        self.assertEqual(android, host)
        self.assertTrue({'contextualAutomaticDecision', 'grammarRevisionAutomaticDecision',
            'nounCaseAutomaticDecision', 'wordContextAutomaticDecision'} <= android)


    def test_failed_compile_preserves_actual_child_exit_or_timeout_in_failed_receipt(self):
        for error in (subprocess.CalledProcessError(42, ['synthetic-compiler']),
                      subprocess.TimeoutExpired(['synthetic-compiler'], 7)):
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder).resolve(); java = root / 'java'; java.write_bytes(b'synthetic executable')
                rows = root / 'rows.jsonl'
                rows.write_text(json.dumps({'id': 'original', 'split': 'calibration', 'language': 'en',
                    'prefix': 'go', 'typed': 'home'}) + '\n')
                args = replay.parser().parse_args(['--java', str(java), '--rows', str(rows),
                    '--output', str(root / 'build/replay')])
                with mock.patch.object(replay.harness, 'REPO', root), \
                     mock.patch.object(replay.harness, 'ASSETS', root / 'assets'), \
                     mock.patch.object(replay.harness, 'compile_inputs', return_value=([java], [], java)), \
                     mock.patch.object(replay.harness, 'compile_harness', side_effect=error), \
                     mock.patch.dict(os.environ, {}, clear=True), self.assertRaises(type(error)):
                    replay.run(args)
                receipt = json.loads((args.output / 'receipt.json').read_text())
                self.assertEqual('FAILED', receipt['status'])
                self.assertEqual(1, receipt['exitCode'])
                if isinstance(error, subprocess.CalledProcessError):
                    self.assertEqual(42, receipt['subprocessExitCode'])
                    self.assertNotIn('subprocessTimeoutSeconds', receipt)
                else:
                    self.assertEqual(7, receipt['subprocessTimeoutSeconds'])
                    self.assertNotIn('subprocessExitCode', receipt)
