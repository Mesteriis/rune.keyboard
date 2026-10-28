import copy
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('evaluate_distance_one_policy',
    HERE / 'evaluate_distance_one_policy.py')
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def snapshot(text, composing=True):
    size = len(text.encode('utf-16-le')) // 2
    return dict(text=text, caret=size, composingStart=0 if composing else -1,
                composingEnd=size if composing else -1)


def observation(row, decision='mistake', applied='mistake'):
    prefix = row.get('prefix', '') + ' ' if row.get('prefix') else ''
    before = snapshot(prefix + row['typed'])
    changed = applied is not None
    text = prefix + (applied if changed else row['typed']) + ' '
    return dict(id=row['id'], status='COMPLETE', language=row['language'], split=row['split'],
        prefix=row.get('prefix', ''), typed=row['typed'], inputExpected=before['text'],
        beforeBoundary=before, afterBoundary=snapshot(text, False), afterBackspace=copy.deepcopy(before),
        inputChangedByTyping=False, boundaryChangedBeyondInsertedSpace=changed,
        morphologyAdmission=True, localDecision=decision,
        autoEdit=dict(original=row['typed'], applied=applied+' ',
            committedStart=len(prefix.encode('utf-16-le'))//2, correctionGeneration={}) if changed else None,
        automaticAdmissionAllowed=True if changed else False,
        automaticAdmissionRefusal=None if changed else 'ORIGINAL_VALID',
        automaticAdmissionCandidate=decision, restoredBeforeBoundaryExactly=True,
        candidateView={'candidates': [{'role': 'ORIGINAL', 'text': row['typed']}]})


class DistanceOnePolicyEvaluationTest(unittest.TestCase):
    def fixture(self):
        rows, observations = [], []
        for language in MODULE.LANGUAGES:
            for split in ('calibration', 'holdout'):
                for ordinal in range(300):
                    row = dict(id=f'{language}-{split}-{ordinal}', split=split, language=language,
                        cohort='typo', family=f'word-{ordinal}', typed='mistke', prefix='',
                        expectedSpelling='mistake', noAuto=False)
                    rows.append(row)
                    observations.append(observation(row, applied='mistake' if MODULE.QUALIFIED[language] else None))
        return rows, observations

    def test_holdout_counts_precision_undo_and_original(self):
        rows, observations = self.fixture()
        row = dict(id='ru-holdout-valid', split='holdout', language='ru', cohort='correct',
                   family='valid', typed='valid', prefix='', noAuto=False)
        rows.append(row); observations.append(observation(row, decision='other', applied=None))
        report = MODULE.evaluate(rows, observations)['report']
        self.assertTrue(report['historicalHoldoutGatePassed'])
        self.assertFalse(report['releaseApproved'])
        self.assertFalse(report['productionQualified'])
        self.assertFalse(report['newUnseenHoldout'])
        self.assertEqual(1, report['holdout']['ru']['admissionVetoes'])
        self.assertEqual(0, report['holdout']['ru']['unexpectedAdmissionVetoes'])
        self.assertEqual(300, report['holdout']['ru']['distinctCorrectFamilies'])
        self.assertEqual(1.0, report['holdout']['es']['precision'])
        self.assertEqual(0, report['holdout']['en']['automaticChanges'])

    def test_qualified_false_change_fails_gate(self):
        row = dict(id='x', split='holdout', language='ru', cohort='protected',
                   family='x', typed='Name', prefix='', noAuto=True)
        report = MODULE.evaluate([row], [observation(row, 'name', 'name')])['report']
        self.assertFalse(report['holdout']['ru']['passed'])
        self.assertEqual(1, report['holdout']['ru']['protectedChanges'])

    def test_real_editor_text_controls_correctness_even_with_correct_decision(self):
        rows, observations = self.fixture()
        index = next(i for i,r in enumerate(rows) if r['language']=='ru' and r['split']=='holdout')
        # A consistent but wrong editor replacement must not receive credit from the decision label.
        observations[index] = observation(rows[index], decision='mistake', applied='wrong')
        result = MODULE.evaluate(rows, observations)['report']['holdout']['ru']
        self.assertEqual(299, result['correctChanges'])
        self.assertFalse(result['passed'])  # Only 299 correct families remain.

    def test_forged_identity_snapshots_flags_edit_and_admission_are_rejected(self):
        row = dict(id='x', split='holdout', language='ru', cohort='typo', family='x',
                   typed='mistke', prefix='😀', expectedSpelling='mistake', noAuto=False)
        good = observation(row)
        self.assertEqual(1, MODULE.evaluate([row], [good])['report']['holdout']['ru']['correctChanges'])
        mutations = [
            lambda o:o.update(typed='different'),
            lambda o:o.update(prefix='different'),
            lambda o:o.update(inputExpected='different'),
            lambda o:o['afterBoundary'].update(text='different'),
            lambda o:o['afterBackspace'].update(text='different'),
            lambda o:o.update(restoredBeforeBoundaryExactly='true'),
            lambda o:o.update(boundaryChangedBeyondInsertedSpace=False),
            lambda o:o['autoEdit'].update(committedStart=2),  # Emoji is two UTF-16 units; space is one.
            lambda o:o['autoEdit'].update(applied='different'),
            lambda o:o.update(automaticAdmissionRefusal='PROTECTED'),
            lambda o:o.update(automaticAdmissionAllowed=1),
            lambda o:o.pop('automaticAdmissionCandidate'),
            lambda o:o.pop('morphologyAdmission'),
        ]
        for mutate in mutations:
            bad = copy.deepcopy(good); mutate(bad)
            with self.subTest(mutation=mutations.index(mutate)):
                with self.assertRaises(ValueError): MODULE.evaluate([row], [bad])

    def test_undo_includes_caret_and_composition(self):
        rows, observations = self.fixture()
        index = next(i for i,r in enumerate(rows) if r['language']=='ru' and r['split']=='holdout')
        observations[index]['afterBackspace']['composingStart'] = -1
        observations[index]['afterBackspace']['composingEnd'] = -1
        result = MODULE.evaluate(rows, observations)['report']['holdout']['ru']
        self.assertEqual(1, result['undoFailures'])
        self.assertFalse(result['passed'])

    def test_undeclared_jvm_options_fail_before_any_export(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / 'build/output'
            with patch.object(MODULE, 'REPO', Path(directory).resolve()), \
                    patch.dict(MODULE.os.environ, {'_JAVA_OPTIONS': '-Dcontrolled=1'}):
                with self.assertRaisesRegex(ValueError, 'UNDECLARED_JAVA_OPTIONS'):
                    MODULE.run(SimpleNamespace(output=output))
            self.assertFalse(output.exists())


if __name__ == '__main__': unittest.main()
