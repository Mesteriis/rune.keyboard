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
    def test_mismatch_summary_reports_categories_without_private_values(self):
        report={'differentRows':2,'differences':[
            {'baselineId':'secret-id','paths':['/jointModelScores/0','/afterBoundary/text']},
            {'candidateId':'secret-id','paths':['/private-word/value','/jointModelScores/4']}]}
        message=replay.mismatch_summary('REPLAY_NONDETERMINISTIC', report)
        self.assertNotIn('secret',message)
        self.assertNotIn('private-word',message)
        self.assertEqual({'differentRows':2,'fieldCategories':{'afterBoundary':1,'jointModelScores':2,'other':1}},
                         json.loads(message.split(':',1)[1]))

    def test_recovery_summary_counts_bounded_hypotheses_without_exposing_values(self):
        def row(completion, states):
            return {'fullTokenGeneration': {'neighborRecovery': {
                'completion': completion, 'inspectedStates': states,
                'alternatives': [{'text': 'private-word'}]}}}
        first = [row('COMPLETE', 100), row('STATES_EXHAUSTED', 32768), row('COMPLETE', 10)]
        second = [row('STATES_EXHAUSTED', 42), row('COMPLETE', 100), row('STATES_EXHAUSTED', True)]
        report = {'differentRows': 3, 'differences': [
            {'row': index + 1, 'baselineId': 'private-id',
             'paths': ['/fullTokenGeneration/neighborRecovery/completion']} for index in range(3)]}
        message = replay.mismatch_summary('REPLAY_NONDETERMINISTIC', report, first, second)
        self.assertNotIn('private', message)
        summary = json.loads(message.split(':', 1)[1])
        self.assertEqual({'changedEvidencePairs': 3, 'secondPossibleDeadline': 1},
                         summary['neighborRecovery'])
        self.assertEqual({'other': 3}, summary['fieldCategories'])

    def test_recovery_summary_ignores_missing_or_invalid_rows(self):
        report = {'differentRows': 2, 'differences': [
            {'row': 0, 'paths': ['/x']}, {'row': 2, 'paths': ['/x']}]}
        summary = json.loads(replay.mismatch_summary('FAIL', report, [{}], [{}]).split(':', 1)[1])
        self.assertEqual({}, summary['neighborRecovery'])

    def test_recovery_diagnostic_bound_matches_product_source(self):
        source = replay.harness.REPO / ('app/src/main/java/io/github/mesteriis/rune/keyboard/'
                                        'smarttyping/lexicon/NeighborRecoverySearch.kt')
        match = re.search(r'const val MAX_STATES\s*=\s*([\d_]+)', source.read_text())
        self.assertIsNotNone(match)
        self.assertEqual(int(match.group(1).replace('_', '')), replay.NEIGHBOR_MAX_STATES)

    def test_instrumented_baseline_excludes_only_observed_full_order(self):
        rows = [{'fullCandidateOrder': [], 'candidateView': {'enabled': True}, 'other': 1}]
        self.assertEqual([{'candidateView': {'enabled': True}, 'other': 1}],
                         replay.baseline_projection(rows, True))
        self.assertIs(rows, replay.baseline_projection(rows, False))
        with self.assertRaisesRegex(ValueError, 'REPLAY_CANDIDATE_ORDER_MISSING'):
            replay.baseline_projection([{'other': 1}], True)

    def test_java_is_explicit_and_has_no_machine_local_default(self):
        with self.assertRaises(SystemExit):
            replay.parser().parse_args(['--rows', 'rows.jsonl', '--output', 'build/replay'])
        args = replay.parser().parse_args(['--java', '/jdk/bin/java', '--rows', 'en.jsonl',
            '--rows', 'ru.jsonl', '--output', 'build/replay'])
        self.assertEqual(Path('/jdk/bin/java'), args.java)
        self.assertEqual([Path('en.jsonl'), Path('ru.jsonl')], args.rows)
        self.assertEqual('on', args.manual_expansion)
        self.assertEqual('space', args.boundary)
        self.assertFalse(args.a3_rare_probe)
        self.assertFalse(args.contextual_score_probe)
        self.assertFalse(args.disable_contextual_choice)
        probe = replay.parser().parse_args(['--java', '/jdk/bin/java', '--rows', 'ru.jsonl',
            '--output', 'build/replay', '--a3-rare-probe'])
        self.assertTrue(probe.a3_rare_probe)
        probe = replay.parser().parse_args(['--java', '/jdk/bin/java', '--rows', 'ru.jsonl',
            '--output', 'build/replay', '--contextual-score-probe'])
        self.assertTrue(probe.contextual_score_probe)
        probe = replay.parser().parse_args(['--java', '/jdk/bin/java', '--rows', 'ru.jsonl',
            '--output', 'build/replay', '--disable-contextual-choice'])
        self.assertTrue(probe.disable_contextual_choice)
        args = replay.parser().parse_args(['--java', '/jdk/bin/java', '--rows', 'ru.jsonl',
            '--output', 'build/replay', '--manual-expansion', 'off'])
        self.assertEqual('off', args.manual_expansion)
        for boundary in ('period', 'colon'):
            args = replay.parser().parse_args(['--java', '/jdk/bin/java', '--rows', 'ru.jsonl',
                '--output', 'build/replay', '--boundary', boundary])
            self.assertEqual(boundary, args.boundary)
        with self.assertRaises(SystemExit):
            replay.parser().parse_args(['--java', '/jdk/bin/java', '--rows', 'ru.jsonl',
                '--output', 'build/replay', '--boundary', 'comma'])

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
