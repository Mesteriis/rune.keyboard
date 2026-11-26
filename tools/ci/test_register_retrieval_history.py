"""Verify historical retrieval disclosure and its portable registry bindings."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import register_retrieval_history as subject


class RetrievalHistoryTest(unittest.TestCase):
    def test_source_counts_and_all_registry_axes(self):
        rows, keys, _ = subject.inputs()
        control, lexical = subject.entries()
        self.assertEqual(1800, len(rows))
        self.assertEqual(341, len(keys['articleKeys']))
        self.assertEqual(1797, len(keys['contextKeys']))
        self.assertEqual(770, len(keys['familyKeys']))
        self.assertEqual(set(keys['controlKeys']), set(control['keys']))
        self.assertEqual(set(keys['sentenceKeys']), set(lexical[0]['keys']['sentence']))
        self.assertEqual(set(keys['contextKeys']), set(lexical[1]['keys']['context']))
        self.assertEqual(set(keys['familyKeys']), set(lexical[2]['keys']['family']))
        self.assertEqual(1800, subject.check())

    def test_real_overlap_gates_reject_historical_row(self):
        rows, _, _ = subject.inputs()
        row = rows[0] | {'article': rows[0]['articleId']}
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:article'):
            subject.lexical.assert_disjoint([row], subject.lexical.load_ledger(subject.LEXICAL),
                                            kinds=('article',), require_complete=False)
        with self.assertRaisesRegex(ValueError, 'CONTROL_OVERLAP:regression'):
            subject.control.assert_disjoint([row], subject.control.load(subject.CONTROL), 'regression')

    def test_modified_historical_rows_or_helper_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder) / 'fixture'
            shutil.copytree(subject.FIXTURE, fixture)
            with mock.patch.object(subject, 'FIXTURE', fixture):
                rows = fixture / 'rows.jsonl'
                original = rows.read_bytes()
                rows.write_bytes(original.replace(b'\n', b' \n', 1))
                with self.assertRaisesRegex(ValueError, 'RETRIEVAL_FIXTURE_IDENTITY'):
                    subject.inputs()
                rows.write_bytes(original)
                helper = next((fixture / 'sources').iterdir())
                helper.write_bytes(helper.read_bytes() + b' ')
                with self.assertRaisesRegex(ValueError, 'RETRIEVAL_FIXTURE_HELPERS'):
                    subject.inputs()

    def test_registry_check_in_checkout_without_build(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for relative in ('tools/ci/register_retrieval_history.py',
                             'tools/typing_experiments/control_ledger.py',
                             'tools/typing_experiments/holdout_ledger.py',
                             'tools/typing_experiments/conversation_split_checks.py',
                             'tools/typing_experiments/source_identities.py',
                             'tools/typing_experiments/control-ledger.json',
                             'tools/typing_experiments/holdout-ledger.json'):
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(subject.ROOT / relative, destination)
            shutil.copytree(subject.FIXTURE, root / 'tools/typing_experiments/retrieval-history-v1')
            result = subprocess.run([sys.executable, '-I', str(root / 'tools/ci/register_retrieval_history.py'), '--check'],
                                    cwd=root, capture_output=True, text=True, timeout=120)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual({'rows': 1800, 'independentQualification': False}, json.loads(result.stdout))
            self.assertFalse((root / 'build').exists())


if __name__ == '__main__':
    unittest.main()
