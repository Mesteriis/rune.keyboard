"""Synthetic candidate loss, causal scorer parity and held-out access contracts."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import neural_refinement as neural
import word_ranking as word


def synthetic_model(seed=11):
    rng = np.random.default_rng(seed)
    shapes = ((48*34, 48), (48,), (48, 34), (34,))
    return neural.Model(48, 48, [rng.normal(0, .06, shape).astype(np.float32) for shape in shapes])


def group(prefix='мы идём', words=('домой', 'дом', 'дома'), labels=(1, 0, 0)):
    return dict(prefix=prefix, candidates=list(words), tree=[.1, .15, -.05][:len(words)], labels=list(labels),
                typo=True, editCount=1, originalFirst=[False]*len(words))


class WordRankingTests(unittest.TestCase):
    def test_exact_shipped_initialization_and_export(self):
        source = word.ASSETS/'ru-ranking-context.bin'
        model = neural.load_model(source)
        self.assertEqual((model.window, model.hidden), (48, 48))
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'original.bin'
            neural.export_model(model, path)
            self.assertEqual(path.read_bytes(), source.read_bytes())

    def test_preprocessing_and_runtime_score_numeric_parity(self):
        model = synthetic_model()
        for prefix in ('', 'мы идём', 'я '*70, 'ТЕКСТ\n', 'x!?'):
            for candidate in ('Домой', 'я', 'а'*40, 'ёжик'):
                x, y = word.encode(prefix, candidate)
                self.assertEqual(len(y), min(len(candidate), 32)+1)
                self.assertEqual(y[-1], 0)
                self.assertEqual(x.shape, (len(y), 48))
                g = group(prefix, (candidate,), (1,))
                actual = word.context_values(model, [g])[0][0]
                expected = neural.context_score(model, prefix, candidate)
                self.assertAlmostEqual(actual, expected, places=12)
        a, _ = word.encode('мы идём', 'домой')
        b, _ = word.encode('мы идём', 'домики')
        np.testing.assert_array_equal(a[:4], b[:4])
        self.assertEqual(a[0, -1], 0)
        with self.assertRaises(ValueError):
            word.encode('x', '')
        with self.assertRaises(ValueError):
            word.encode('x', 'а'*129)

    def test_controls_coverage_and_missing_targets(self):
        records = []
        for i, (count, cohort, no_auto, expected, candidates) in enumerate([
            (0, 'correct', True, 'дом', ['дом', 'том']),
            (1, 'typo', False, 'дом', ['дом', 'том']),
            (2, 'typo', False, 'дом', ['том', 'ком']),
            (3, 'typo', False, 'дом', []),
            (1, 'typo', False, 'дом', ['дом']),
            (2, 'typo', False, 'дом', ['дом', 'ДОМ']),
        ]):
            records.append(dict(row=dict(id=str(i), articleId=str(i), prefix='', typed='том',
                              expectedSpelling=expected, errorCount=count, cohort=cohort, noAuto=no_auto),
                                observation=dict(generation=dict(isValidWord=False, alternatives=[dict(text=c) for c in candidates]))))
        groups, coverage = word.pack(records, [[0]*len(r['observation']['generation']['alternatives']) for r in records])
        self.assertEqual([g['eligible'] for g in groups], [False, True, False, False, False, False])
        self.assertEqual(coverage['control']['rows'], 1)
        report = word.summarize(groups, [[0]*len(g['labels']) for g in groups])
        self.assertEqual(report['typoRows'], 5)
        self.assertEqual(report['expectedAvailable'], 3)
        self.assertEqual(report['combinedTop1'], 3)
        # Stable alternative ordering; the product's original slot is separate.
        g = group(words=('том', 'дом'), labels=(0, 1))
        g['tree'] = [0, 0]
        g['originalFirst'] = [False, True]
        self.assertEqual(word.summarize([g], [[0, 0]])['combinedTop1'], 0)

    def test_train_dev_boundary_rejects_before_any_open(self):
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('no reads')), \
             patch.object(Path, 'read_text', side_effect=AssertionError('no reads')):
            for path, split in [('test.jsonl', 'test'), ('test.jsonl', 'dev'), ('dev.jsonl', 'train')]:
                with self.assertRaisesRegex(ValueError, 'TRAIN_DEV_ONLY'):
                    word.verified_records(path, split)
        # Runtime dispatch has no test command, and train consumes only train cache keys.
        source = Path(word.__file__).read_text()
        self.assertNotIn("allow_test=True", source)
        self.assertNotIn("/'test.jsonl'", source)
        self.assertNotIn('test-rows.jsonl', source)

    def test_selection_ties_are_frozen(self):
        def result(a, b, epoch):
            return dict(newDev=dict(combinedTop1=a), oldDev=dict(combinedTop1=b), epoch=epoch)
        models = dict(original=result(10, 10, 0), **{'epoch-1': result(10, 10, 1), 'epoch-6': result(10, 10, 6)})
        self.assertEqual(word.choose(models), 'original')
        models['epoch-6']['oldDev']['combinedTop1'] = 11
        self.assertEqual(word.choose(models), 'epoch-6')
        models['epoch-1']['newDev']['combinedTop1'] = 11
        self.assertEqual(word.choose(models), 'epoch-1')
        models['epoch-6'] = result(11, 10, 6)
        self.assertEqual(word.choose(models), 'epoch-1')

    def test_numpy_loss_group_mean_and_terminal_score(self):
        model = synthetic_model()
        teacher = synthetic_model(12)
        groups = [group(), group('я', ('я', 'мама'), (0, 1))]
        arrays = word.batch_arrays(groups)
        together = word.numpy_loss(model, teacher, arrays)
        separate = np.mean([word.numpy_loss(model, teacher, word.batch_arrays([g])) for g in groups])
        self.assertAlmostEqual(together, separate, places=12)
        same = word.numpy_loss(model, model, arrays)
        manual = []
        for g in groups:
            scores = (np.array(g['tree'], dtype=np.float32)+np.array([neural.context_score(model, g['prefix'], c) for c in g['candidates']]))/.1
            z = scores-scores.max()
            manual.append(np.log(np.exp(z).sum())-np.log(np.exp(z)[np.array(g['labels'], dtype=bool)].sum()))
        self.assertAlmostEqual(same, float(np.mean(manual)), places=12)

    @unittest.skipUnless(importlib.util.find_spec('mlx'), 'MLX environment required')
    def test_mlx_loss_parity_initialization_and_finite_gradient(self):
        import mlx.core as mx
        import mlx.nn as nn
        model = neural.load_model(word.ASSETS/'ru-ranking-context.bin')
        Network = word.network_class()
        net, teacher = Network(model), Network(model)
        for key, original in zip(word.KEYS, model.weights):
            np.testing.assert_array_equal(np.array(net[key]), original)
        arrays = word.batch_arrays([group(), group('я', ('я', 'мама'), (0, 1))])
        value_grad = nn.value_and_grad(net, lambda m, *args: word.loss_mlx(m, teacher, *args))
        loss, grad = value_grad(net, *[mx.array(a) for a in arrays])
        mx.eval(loss, grad)
        self.assertAlmostEqual(float(loss.item()), word.numpy_loss(model, model, arrays), delta=2e-5)
        self.assertTrue(all(np.isfinite(np.array(grad[key])).all() for key in word.KEYS))
        self.assertGreater(sum(float(np.abs(np.array(grad[key])).sum()) for key in word.KEYS), 0)
        # A different fixed teacher exercises nonzero distillation numeric parity.
        different = synthetic_model(31)
        loss = word.loss_mlx(net, Network(different), *[mx.array(a) for a in arrays])
        self.assertAlmostEqual(float(loss.item()), word.numpy_loss(model, different, arrays), delta=2e-5)
        index = np.unravel_index(np.abs(np.array(grad['w2'])).argmax(), model.weights[2].shape)
        epsilon = 1e-3
        def shifted(delta):
            weights = [a.copy() for a in model.weights]
            weights[2][index] += delta
            return word.numpy_loss(neural.Model(48, 48, weights), model, arrays)
        finite_difference = (shifted(epsilon)-shifted(-epsilon))/(2*epsilon)
        self.assertAlmostEqual(float(np.array(grad['w2'])[index]), finite_difference, delta=2e-3)


if __name__ == '__main__':
    unittest.main()
