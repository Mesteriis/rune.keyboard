import json
from pathlib import Path
import re
import tempfile
import unittest

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
            self.assertEqual([{key: row[key] for key in replay.INPUT_FIELDS}], replay.load_inputs([path]))
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
