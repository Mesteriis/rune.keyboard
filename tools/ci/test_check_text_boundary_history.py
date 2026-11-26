from pathlib import Path
import json
import subprocess
import tempfile
import unittest
from unittest import mock

import check_text_boundary_history as subject


class HistoricalVerificationTest(unittest.TestCase):
    def make_root(self, folder):
        root = Path(folder)
        (root / 'app/src/main').mkdir(parents=True)
        (root / 'tools/typing_experiments').mkdir(parents=True)
        (root / 'tools/typing_experiments/control-ledger.json').write_text(json.dumps({'entries': []}))
        for name, digest in subject.HELPERS.items():
            archive = subject.archived_path(name, digest)
            (root / archive).parent.mkdir(parents=True, exist_ok=True)
            (root / archive).write_bytes((subject.ROOT / archive).read_bytes())
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_text('changed live helper\n')
        return root

    def test_archived_helpers_run_in_isolated_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            root = self.make_root(folder)
            observed = []
            def run(command, *, cwd, check):
                self.assertTrue(check)
                for name, digest in subject.HELPERS.items():
                    self.assertEqual((root / subject.archived_path(name, digest)).read_bytes(),
                                     (cwd / name).read_bytes())
                    self.assertEqual('changed live helper\n', (root / name).read_text())
                observed.append(command)
            with mock.patch.object(subject.subprocess, 'run', side_effect=run):
                subject.verify(root)
            self.assertEqual(12, len(observed))
            for verifier in subject.VERIFIERS:
                self.assertTrue(any('test_register_' + verifier + '.py' in cmd for cmd in observed))
                self.assertTrue(any(cmd[-2].endswith('/register_' + verifier + '.py')
                                    and cmd[-1] == '--check' for cmd in observed))
            self.assertTrue(observed[-1][-2].endswith('import_neighbor_article_segments.py'))
            self.assertEqual('--check', observed[-1][-1])

    def test_projection_removes_only_source_entries(self):
        with tempfile.TemporaryDirectory() as folder:
            root = self.make_root(folder)
            path = root / 'tools/typing_experiments/control-ledger.json'
            retained = [{'id': 'first', 'kind': 'regression'}, {'id': 'later', 'kind': 'punctuation'}]
            original = {'entries': [retained[0], {'id': subject.EWT_SOURCE, 'kind': 'source'},
                                    {'id': 'other-source', 'kind': 'source'}, retained[1]]}
            path.write_text(json.dumps(original))
            self.assertEqual({subject.EWT_SOURCE, 'other-source'}, subject.project_control_ledger(path))
            self.assertEqual(retained, json.loads(path.read_text())['entries'])
            original['entries'][1]['kind'] = 'regression'
            path.write_text(json.dumps(original))
            with self.assertRaisesRegex(ValueError, 'HISTORICAL_CONTROL_SOURCE'):
                subject.project_control_ledger(path)

    def test_source_projection_runs_live_registration_check_first(self):
        with tempfile.TemporaryDirectory() as folder:
            root = self.make_root(folder)
            path = root / 'tools/typing_experiments/control-ledger.json'
            keys = [f'{i:064x}' for i in range(1174)]
            path.write_text(json.dumps({'entries': [dict(id=subject.EWT_SOURCE, kind='source',
                language='en', rowCount=16622, keys=[], articleKeys=keys)]}))
            commands = []
            with mock.patch.object(subject.subprocess, 'run', side_effect=lambda command, **kw: commands.append(command)):
                subject.verify(root)
            self.assertEqual(14, len(commands))
            self.assertTrue(commands[0][-2].endswith('control_ledger.py'))
            self.assertEqual('--validate-only', commands[0][-1])
            self.assertTrue(commands[1][-2].endswith('register_ewt_control_source.py'))
            self.assertEqual('--check', commands[1][-1])
            self.assertEqual(1,len(json.loads(path.read_text())['entries']))

    def test_corrupt_archived_helper_never_runs_verifier(self):
        with tempfile.TemporaryDirectory() as folder:
            root = self.make_root(folder)
            name, digest = next(iter(subject.HELPERS.items()))
            (root / subject.archived_path(name, digest)).write_bytes(b'corrupt')
            with mock.patch.object(subject.subprocess, 'run') as run:
                with self.assertRaisesRegex(ValueError, 'HISTORICAL_HELPER_MISMATCH'):
                    subject.verify(root)
                run.assert_not_called()

    def test_neighbor_failure_is_not_hidden(self):
        with tempfile.TemporaryDirectory() as folder:
            root = self.make_root(folder)
            def run(command, *, cwd, check):
                if command[-2].endswith('import_neighbor_article_segments.py'):
                    raise subprocess.CalledProcessError(1, command)
            with mock.patch.object(subject.subprocess, 'run', side_effect=run):
                with self.assertRaises(subprocess.CalledProcessError):
                    subject.verify(root)


if __name__ == '__main__':
    unittest.main()
