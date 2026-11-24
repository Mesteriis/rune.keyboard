import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import register_authored_typo_inputs as subject
import register_authored_dialogue as source


class AuthoredDialogueTest(unittest.TestCase):
    def test_registered_context_rejected_by_both_gates(self):
        rows, _ = subject.inputs()
        self.assertEqual(94, len(rows))
        self.assertEqual(94, subject.check())
        with self.assertRaisesRegex(ValueError, 'CONTROL_OVERLAP:regression'):
            subject.control.assert_disjoint([rows[-1]], subject.control.load(subject.CONTROL), 'regression')
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:context'):
            subject.lexical.assert_disjoint([rows[-1]], subject.lexical.load_ledger(subject.LEXICAL),
                                            kinds=('context',), require_complete=False)

    def test_changed_source_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder) / 'fixture'
            shutil.copytree(subject.FIXTURE, fixture)
            path = fixture / 'dialogues.jsonl'
            path.write_bytes(path.read_bytes() + b' ')
            with mock.patch.object(source, 'FIXTURE', fixture):
                with self.assertRaisesRegex(ValueError, 'DIALOGUE_SOURCE_IDENTITY'):
                    subject.inputs()

    def test_registry_check_without_build(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ('tools/ci/register_authored_dialogue.py',
                         'tools/ci/register_authored_phrase_inputs.py',
                         'tools/ci/register_authored_typo_inputs.py',
                         'tools/typing_experiments/control_ledger.py',
                         'tools/typing_experiments/holdout_ledger.py',
                         'tools/typing_experiments/conversation_split_checks.py',
                         'tools/typing_experiments/source_identities.py',
                         'tools/typing_experiments/control-ledger.json',
                         'tools/typing_experiments/holdout-ledger.json'):
                dest = root / name; dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(subject.ROOT / name, dest)
            shutil.copytree(subject.FIXTURE, root / 'tools/typing_experiments/authored-dialogue-v1')
            result = subprocess.run([sys.executable, '-I', str(root / 'tools/ci/register_authored_typo_inputs.py'), '--check'],
                                    cwd=root, text=True, capture_output=True, timeout=120)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual({'tokens': 94, 'independentQualification': False}, json.loads(result.stdout))
            self.assertFalse((root / 'build').exists())


if __name__ == '__main__': unittest.main()
