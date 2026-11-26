from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
DRIVER = ROOT / 'tools/typing_experiments/replay_historical_context_features.py'


class HistoricalContextReplayGuardTest(unittest.TestCase):
    def test_refuses_outside_existing_and_optimized_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            outside = Path(directory) / 'existing.json'
            outside.write_text('sentinel')
            result = subprocess.run([sys.executable, str(DRIVER), '--output', str(outside)],
                                    cwd=ROOT, text=True, capture_output=True)
            self.assertNotEqual(0, result.returncode)
            self.assertIn('CONTEXT_REPLAY_OUTPUT_OR_WORKDIR', result.stderr)
            self.assertEqual('sentinel', outside.read_text())
            result = subprocess.run([sys.executable, '-O', str(DRIVER), '--output', str(outside)],
                                    cwd=ROOT, text=True, capture_output=True)
            self.assertNotEqual(0, result.returncode)
            self.assertIn('CONTEXT_REPLAY_REQUIRES_ASSERTIONS', result.stderr)
            self.assertEqual('sentinel', outside.read_text())
        build = ROOT / 'build'
        build.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='context-replay-guard-', dir=build) as folder:
            existing = Path(folder) / 'result.json'
            existing.write_text('sentinel')
            result = subprocess.run([sys.executable, str(DRIVER), '--output', str(existing)],
                                    cwd=ROOT, text=True, capture_output=True)
            self.assertNotEqual(0, result.returncode)
            self.assertIn('CONTEXT_REPLAY_OUTPUT_OR_WORKDIR', result.stderr)
            self.assertEqual('sentinel', existing.read_text())

    def test_score_replay_refuses_outside_output_and_optimized_python(self):
        driver = ROOT / 'tools/typing_experiments/replay_historical_context_scores.py'
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'existing.json'
            output.write_text('sentinel')
            for flags, reason in (([], 'CONTEXT_SCORE_OUTPUT_OR_WORKDIR'),
                                  (['-O'], 'CONTEXT_SCORE_REQUIRES_ASSERTIONS')):
                with self.subTest(flags=flags):
                    result = subprocess.run([sys.executable, *flags, str(driver), '--output', str(output)],
                                            cwd=ROOT, text=True, capture_output=True)
                    self.assertNotEqual(0, result.returncode)
                    self.assertIn(reason, result.stderr)
                    self.assertEqual('sentinel', output.read_text())

    def test_residual_replay_refuses_outside_output_and_optimized_python(self):
        driver = ROOT / 'tools/typing_experiments/replay_historical_residual_scores.py'
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'existing.json'
            output.write_text('sentinel')
            for flags, reason in (([], 'RESIDUAL_REPLAY_OUTPUT_OR_WORKDIR'),
                                  (['-O'], 'RESIDUAL_REPLAY_REQUIRES_ASSERTIONS')):
                with self.subTest(flags=flags):
                    result = subprocess.run([sys.executable, *flags, str(driver), '--output', str(output)],
                                            cwd=ROOT, text=True, capture_output=True)
                    self.assertNotEqual(0, result.returncode)
                    self.assertIn(reason, result.stderr)
                    self.assertEqual('sentinel', output.read_text())

    def test_residual_feature_replay_refuses_outside_output_and_optimized_python(self):
        driver = ROOT / 'tools/typing_experiments/replay_historical_residual_features.py'
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'existing.json'
            output.write_text('sentinel')
            for flags, reason in (([], 'RESIDUAL_FEATURE_OUTPUT_OR_WORKDIR'),
                                  (['-O'], 'RESIDUAL_FEATURE_REQUIRES_ASSERTIONS')):
                with self.subTest(flags=flags):
                    result = subprocess.run([sys.executable, *flags, str(driver), '--output', str(output)],
                                            cwd=ROOT, text=True, capture_output=True)
                    self.assertNotEqual(0, result.returncode)
                    self.assertIn(reason, result.stderr)
                    self.assertEqual('sentinel', output.read_text())


if __name__ == '__main__':
    unittest.main()
