"""Regression coverage for continuation identity and dev-only selection contracts."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import extra_epochs as extra
import neural_refinement as neural


class ExtraEpochTests(unittest.TestCase):
    def test_continuation_keeps_every_shipped_float_and_prediction(self):
        source = extra.ASSETS/'ru-ranking-context.bin'
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/'copy.bin'
            model = extra.original_copy(source, target)
            self.assertEqual(source.read_bytes(), target.read_bytes())
            old = neural.load_model(source)
            self.assertEqual((48,48), (model.window,model.hidden))
            for context in ('', 'мы идём домой', 'как приготовить обед'):
                np.testing.assert_array_equal(neural.probabilities(old,context), neural.probabilities(model,context))

    def test_continuation_rejects_legacy_architecture(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'REC2_REQUIRED'):
                extra.original_copy(extra.ASSETS/'ru-context.bin', Path(directory)/'model.bin')

    def test_no_extra_epochs_outside_fixed_budget(self):
        self.assertEqual(extra.CHECKPOINTS, (2,4,8,12))
        self.assertEqual(extra.learning_rate(1), .0005)
        self.assertAlmostEqual(extra.learning_rate(12), .0005*.9**11)
        for epoch in (0,13,-1):
            with self.assertRaisesRegex(ValueError, 'BOUNDS'):
                extra.learning_rate(epoch)

    def test_actual_train_dev_are_pinned_and_disjoint(self):
        manifest, train, dev = extra.verified_inputs()
        self.assertEqual(sum(len(r['text']) for r in train), 2000000)
        self.assertEqual(sum(len(r['text']) for r in dev), 250000)
        self.assertFalse({r['articleId'] for r in train}&{r['articleId'] for r in dev})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'manifest.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'INPUT_IDENTITY'):
                extra.verified_inputs(root)
        bad = copy.deepcopy(manifest)
        bad['files']['dev-text.jsonl'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            neural.verified_text(extra.DATA,'dev',bad)

    def test_test_partition_rejected_before_read(self):
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('unexpected read')):
            with self.assertRaisesRegex(ValueError, 'DEV_ONLY'):
                extra.verified_dev(extra.OBSERVATIONS.with_name('test.jsonl'))
            with self.assertRaises(ValueError):
                neural.verified_text(extra.DATA, 'test', {})

    def test_original_remains_candidate_when_checkpoints_regress(self):
        metrics = {'original': {'combinedTop1': 100, 'devCE': 2.0},
                   'extra-2': {'combinedTop1': 99, 'devCE': 1.0}}
        self.assertEqual(extra.choose(metrics), 'original')
        with self.assertRaisesRegex(ValueError, 'ORIGINAL_CANDIDATE_REQUIRED'):
            extra.choose({'extra-2': metrics['extra-2']})
        metrics['extra-2']['combinedTop1'] = 100
        self.assertEqual(extra.choose(metrics), 'extra-2')
        metrics['extra-2']['devCE'] = 2.0
        self.assertEqual(extra.choose(metrics), 'original')
        metrics['extra-2']['combinedTop1'] = 101
        metrics['extra-2']['devCE'] = 3.0
        self.assertEqual(extra.choose(metrics), 'extra-2')

    def test_selection_refuses_nonfinite_ce(self):
        with self.assertRaisesRegex(ValueError, 'INVALID_SELECTION_METRICS'):
            extra.choose({'original': {'combinedTop1': 1, 'devCE': float('nan')}})


if __name__ == '__main__':
    unittest.main()
