import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import select_local_policy as select
import evaluate_local_holdout as holdout
import run_local_qualification as runner


def fixture(split='calibration', changed=True, undo=True, protected=False):
    row = {'id': split + '-1', 'split': split, 'language': 'en', 'typed': 'teh',
           'cohort': 'protected' if protected else 'typo', 'expectedSpelling': 'the', 'noAuto': protected}
    observation = {'id': row['id'], 'split': split, 'language': 'en', 'typed': 'teh', 'prefix': '',
        'status': 'COMPLETE', 'inputChangedByTyping': False, 'currentQualificationWithoutModel': False,
        'boundaryChangedBeyondInsertedSpace': changed, 'afterBoundary': {'text': 'the ' if changed else 'teh '},
        'restoredBeforeBoundaryExactly': undo, 'candidateView': {'candidates': [{'text': 'teh', 'role': 'ORIGINAL'}]},
        'fullTokenGeneration': {'alternatives': [{'text': 'the', 'kind': 'COMMON_CONFUSION'}], 'protectedReason': None}}
    return row, observation


class LocalQualificationTest(unittest.TestCase):
    def test_evaluator_cli_refuses_every_independent_holdout_failure_without_a_receipt(self):
        for mutation in ('protected', 'correct', 'undo', 'original', 'original-no-coverage', 'precision'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as folder:
                row, obs = fixture('holdout', changed=mutation != 'original-no-coverage',
                                   protected=mutation == 'protected', undo=mutation != 'undo')
                if mutation == 'correct': row['cohort'] = 'correct'
                if mutation in ('original', 'original-no-coverage'): obs['candidateView']['candidates'] = []
                if mutation == 'precision': obs['afterBoundary']['text'] = 'wrong '
                result, output = self.cli(Path(folder), row, obs)
                self.assertNotEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertFalse(output.exists())

    def test_evaluator_cli_distinguishes_safe_no_coverage_from_qualified_replacements(self):
        for changed, expected in ((False, 'NO_COVERAGE'), (True, 'QUALIFIED')):
            with tempfile.TemporaryDirectory() as folder:
                row, obs = fixture('holdout', changed=changed)
                result, output = self.cli(Path(folder), row, obs)
                self.assertEqual(0, result.returncode, result.stderr)
                report = json.loads(output.read_text())
                self.assertTrue(report['observedGatePassed'])
                self.assertEqual(expected, report['languages']['en']['qualification'])
                self.assertEqual(changed, report['languages']['en']['pass'])
                self.assertFalse(report['generalLocalEnabled'])

    def test_evaluator_rejects_substituted_missing_or_foreign_input_context(self):
        for mutation in ('substituted', 'missing', 'language', 'split'):
            row, obs = fixture('holdout')
            row['prefix'] = 'please type'
            obs['prefix'] = 'please type'
            obs['afterBoundary']['text'] = 'please type the '
            if mutation == 'substituted':
                obs['prefix'] = 'other context'
                obs['afterBoundary']['text'] = 'other context the '
            if mutation == 'missing': obs.pop('prefix')
            if mutation == 'language': obs['language'] = 'es'
            if mutation == 'split': obs['split'] = 'calibration'
            with self.assertRaisesRegex(ValueError, 'REPLAY_IDENTITY'):
                holdout.metrics([row], [obs])

    @staticmethod
    def cli(folder, row, obs):
        calibration, co = fixture()
        values = {'config': select.select([calibration], [co], {}), 'artifacts': {},
                  'rows': row, 'observations': obs}
        args = []
        for name, value in values.items():
            path = folder / (name + '.json')
            path.write_text(json.dumps(value) + '\n')
            args += ['--' + name, str(path)]
        output = folder / 'receipt.json'
        result = subprocess.run([sys.executable, holdout.__file__, *args, '--output', str(output)],
                                capture_output=True, text=True)
        return result, output

    def test_source_binding_tracks_replay_helper_corpus_and_complete_java_distribution(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            java = root / 'jdk/bin/java'
            for name in runner.replay.JDK_RUNTIME_INVENTORY:
                path = root / 'jdk' / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(name)
            android = root / 'android.jar'; android.write_text('android')
            before, runtime = runner.artifact_bindings(java, [], [], android)
            for path in (Path(runner.replay.__file__), runner.replay.TOOLCHAIN,
                         runner.replay.CORPUS / 'manifest.json'):
                self.assertEqual(runner.replay.sha256(path), before[runner.replay.path_key(path)])
            self.assertEqual(set(runner.replay.JDK_RUNTIME_INVENTORY), set(runtime['files']))
            for name in ('lib/modules', 'lib/server/libjvm.dylib', 'lib/libjli.dylib', 'release'):
                path = root / 'jdk' / name
                original = path.read_text(); path.write_text(original + ' changed')
                changed, _ = runner.artifact_bindings(java, [], [], android)
                self.assertNotEqual(before, changed)
                with self.assertRaises(ValueError): runner.replay.verify_bound_files({'files': before})
                path.write_text(original)
            helper = root / 'replay-helper.py'; helper.write_text('execution helper')
            corpus = root / 'corpus'; corpus.mkdir()
            manifest = corpus / 'manifest.json'; manifest.write_text('{}')
            with mock.patch.object(runner.replay, '__file__', str(helper)), \
                    mock.patch.object(runner.replay, 'CORPUS', corpus):
                before, _ = runner.artifact_bindings(java, [], [], android)
                for path in (helper, manifest):
                    original = path.read_text(); path.write_text(original + ' changed')
                    changed, _ = runner.artifact_bindings(java, [], [], android)
                    self.assertNotEqual(before, changed)
                    with self.assertRaises(ValueError): runner.replay.verify_bound_files({'files': before})
                    path.write_text(original)
    def test_selection_rejects_a_protected_change_even_before_holdout(self):
        row, obs = fixture(protected=True)
        with self.assertRaises(ValueError): select.select([row], [obs], {})
    def test_existing_canonical_change_is_reported_separately_from_finite_spelling(self):
        row, obs = fixture('holdout')
        obs['fullTokenGeneration']['alternatives'][0]['kind'] = 'CANONICAL_CASE'
        result = holdout.metrics([row], [obs])
        self.assertEqual(0, result['replacements'])
        self.assertEqual(1, result['otherAutomaticChanges'])
    def test_selection_rejects_holdout_and_never_activates_general_ranking(self):
        row, obs = fixture()
        config = select.select([row], [obs], {'artifact': 'frozen'})
        self.assertFalse(config['generalLocalEnabled'])
        hr, ho = fixture('holdout')
        with self.assertRaises(ValueError):
            select.select([hr], [ho], {})

    def test_holdout_rejects_overlap_and_artifact_drift(self):
        row, obs = fixture()
        config = select.select([row], [obs], {'artifact': 'frozen'})
        hr, ho = fixture('holdout')
        with self.assertRaises(ValueError):
            holdout.evaluate(config, [hr], [ho], {'artifact': 'changed'})
        hr['id'] = ho['id'] = row['id']
        with self.assertRaises(ValueError):
            holdout.evaluate(config, [hr], [ho], {'artifact': 'frozen'})

    def test_one_protected_change_or_inexact_undo_or_missing_original_fails(self):
        for mutation in ('protected', 'undo', 'original'):
            row, obs = fixture('holdout', protected=mutation == 'protected', undo=mutation != 'undo')
            if mutation == 'original': obs['candidateView']['candidates'] = []
            self.assertFalse(holdout.metrics([row], [obs])['pass'])


if __name__ == '__main__': unittest.main()
