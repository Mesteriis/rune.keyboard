import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import check_retrieval_suspended_history as subject


class SuspendedHistoryTest(unittest.TestCase):
    def make_root(self, folder):
        root = Path(folder)
        fixture = root / subject.FIXTURE
        fixture.mkdir(parents=True)
        (fixture / 'helper-snapshots.json').write_bytes((subject.ROOT / subject.FIXTURE / 'helper-snapshots.json').read_bytes())
        bindings = {'tools/typing_experiments/' + name: sha for name, sha in subject.HELPERS.items()}
        for name, entry in (('control-ledger.json', subject.ENTRY), ('holdout-ledger.json', subject.ENTRY + '-contexts')):
            (root / 'tools/typing_experiments' / name).write_text(json.dumps({'entries': [{'id': entry, 'bindings': bindings}]}))
        for name in subject.HELPERS:
            (root / 'tools/typing_experiments' / name).write_text('changed live helper\n')
        return root

    def test_archived_helpers_run_only_inside_temporary_tree(self):
        with tempfile.TemporaryDirectory() as folder:
            root = self.make_root(folder)
            calls = []
            def run(command, *, cwd, check, env):
                self.assertTrue(check)
                self.assertEqual('1', env['PYTHONDONTWRITEBYTECODE'])
                for name, digest in subject.HELPERS.items():
                    self.assertEqual(digest, subject.sha((cwd / 'tools/typing_experiments' / name).read_bytes()))
                    self.assertEqual('changed live helper\n', (root / 'tools/typing_experiments' / name).read_text())
                calls.append(command)
            with mock.patch.object(subject.subprocess, 'run', side_effect=run):
                subject.verify(root)
            self.assertEqual(2, len(calls))
            self.assertTrue(calls[1][-2].endswith('register_retrieval_suspended_source.py'))
            self.assertEqual('--check', calls[1][-1])

    def test_corrupted_snapshot_or_registry_is_refused_before_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            root = self.make_root(folder)
            fixture = root / subject.FIXTURE / 'helper-snapshots.json'
            data = json.loads(fixture.read_text()); name = next(iter(subject.HELPERS));data[name] += '\n'
            fixture.write_text(json.dumps(data))
            with mock.patch.object(subject.subprocess, 'run') as run:
                with self.assertRaisesRegex(ValueError, 'SUSPENDED_HISTORY_HELPER'):
                    subject.verify(root)
                run.assert_not_called()
        with tempfile.TemporaryDirectory() as folder:
            root = self.make_root(folder)
            ledger = root / 'tools/typing_experiments/control-ledger.json'
            data = json.loads(ledger.read_text()); data['entries'][0]['bindings']['tools/typing_experiments/control_ledger.py'] = '0'*64
            ledger.write_text(json.dumps(data))
            with mock.patch.object(subject.subprocess, 'run') as run:
                with self.assertRaisesRegex(ValueError, 'SUSPENDED_HISTORY_BINDING'):
                    subject.verify(root)
                run.assert_not_called()

    def test_failure_from_historical_verifier_propagates(self):
        with tempfile.TemporaryDirectory() as folder:
            root = self.make_root(folder)
            with mock.patch.object(subject.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, ['check'])):
                with self.assertRaises(subprocess.CalledProcessError):
                    subject.verify(root)

    def test_duplicate_snapshot_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = self.make_root(folder)
            (root / subject.FIXTURE / 'helper-snapshots.json').write_text('{"control_ledger.py":"a","control_ledger.py":"b"}')
            with mock.patch.object(subject.subprocess, 'run') as run:
                with self.assertRaisesRegex(ValueError, 'SUSPENDED_HISTORY_DUPLICATE'):
                    subject.verify(root)
                run.assert_not_called()

    def test_symlinked_helper_directory_cannot_escape_snapshot(self):
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as outside:
            root = Path(folder)
            foreign = self.make_root(outside)
            (root / 'tools').mkdir()
            (root / 'tools/typing_experiments').symlink_to(foreign / 'tools/typing_experiments', target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'SUSPENDED_HISTORY_HELPER'):
                subject.overlay_helpers(root)
            self.assertEqual('changed live helper\n', (foreign / 'tools/typing_experiments/control_ledger.py').read_text())


if __name__ == '__main__':
    unittest.main()
