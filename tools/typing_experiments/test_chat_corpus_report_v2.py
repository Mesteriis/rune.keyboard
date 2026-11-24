import copy
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import chat_corpus_report as historical
import chat_corpus_report_v2 as subject


def sample():
    row = dict(id='one', typed='слово', prefix='ну', expectedSpelling='слово',
               cohort='correct', noAuto=True, language='ru', register='chat-shaped-lowercase',
               purpose='DISCLOSED_REGRESSION_NOT_QUALIFICATION', clusterId='public:1', edit_kind='control')
    observation = dict(id='one', typed='слово', prefix='ну', status='COMPLETE',
                       beforeBoundary={'text':'ну слово'}, afterBoundary={'text':'ну Слово '},
                       afterBackspace={'text':'ну слово'}, boundaryChangedBeyondInsertedSpace=True,
                       restoredBeforeBoundaryExactly=True)
    return row, observation


class ChatReportUndoTest(unittest.TestCase):
    def test_false_success_is_refused_even_when_historical_report_accepts_it(self):
        row, obs = sample()
        obs['afterBackspace']['text'] = 'ну другое'
        self.assertEqual(0, historical.report([row], [obs])['overall']['undoFailures'])
        with self.assertRaisesRegex(ValueError, 'CHAT_UNDO_FLAG_MISMATCH'):
            subject.report([row], [obs])

    def test_true_failure_is_reported_and_inconsistent_false_is_refused(self):
        row, obs = sample()
        obs['afterBackspace']['text'] = 'ну другое'
        obs['restoredBeforeBoundaryExactly'] = False
        result = subject.report([row], [obs])
        self.assertEqual(1, result['overall']['undoFailures'])
        self.assertFalse(result['independentQualification'])
        obs['afterBackspace']['text'] = obs['beforeBoundary']['text']
        with self.assertRaisesRegex(ValueError, 'CHAT_UNDO_FLAG_MISMATCH'):
            subject.report([row], [obs])

    def test_missing_or_malformed_evidence_is_refused(self):
        row, obs = sample()
        for field, value in [('afterBackspace', None), ('beforeBoundary', {}),
                             ('restoredBeforeBoundaryExactly', 1)]:
            with self.subTest(field=field):
                altered = copy.deepcopy(obs)
                altered[field] = value
                with self.assertRaisesRegex(ValueError, 'CHAT_UNDO_EVIDENCE'):
                    subject.report([row], [altered])

    def test_existing_public_replay_snapshots_have_consistent_undo_flags(self):
        root = Path(__file__).resolve().parents[2]
        for name, expected in [('product-replay-v1', 2160), ('product-replay-history-v1', 12000)]:
            directory = root/'tools/ci'/name
            baseline = directory/'baseline.jsonl.gz'
            manifest = json.loads((directory/'baseline-manifest.json').read_text())
            with self.subTest(name=name), baseline.open('rb') as raw:
                self.assertEqual(manifest['fileSha256'], hashlib.file_digest(raw, 'sha256').hexdigest())
            with self.subTest(name=name), gzip.open(baseline, 'rt') as stream:
                observations = [json.loads(line) for line in stream]
                self.assertEqual(expected, len(observations))
                subject.verify_undo_text(observations)

    def test_cli_refuses_inconsistent_undo_without_creating_report(self):
        row, obs = sample()
        obs['afterBackspace']['text'] = 'ну другое'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = root/'rows.jsonl'
            observations = root/'observations.jsonl'
            output = root/'report.json'
            rows.write_text(json.dumps(row, ensure_ascii=False)+'\n')
            observations.write_text(json.dumps(obs, ensure_ascii=False)+'\n')
            result = subprocess.run([sys.executable, str(Path(subject.__file__)),
                                     '--rows', str(rows), '--observations', str(observations),
                                     '--output', str(output)], capture_output=True, text=True)
            self.assertNotEqual(0, result.returncode)
            self.assertIn('CHAT_UNDO_FLAG_MISMATCH', result.stderr)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
