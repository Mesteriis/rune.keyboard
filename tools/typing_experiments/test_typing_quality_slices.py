import unittest
from copy import deepcopy
from typing_quality_slices import edit_distance, evaluate


class QualitySlicesTest(unittest.TestCase):
    def fixture(self, typed='зочу', target='хочу', changed=True, cohort='typo', no_auto=False):
        row = dict(id='case', typed=typed, prefix='я', expectedCandidate=target, cohort=cohort, noAuto=no_auto)
        observation = dict(id='case', typed=typed, prefix='я', status='COMPLETE',
            beforeBoundary={'text': 'я ' + typed}, afterBoundary={'text': 'я ' + (target if changed else typed) + ' '},
            boundaryChangedBeyondInsertedSpace=changed, restoredBeforeBoundaryExactly=True,
            fullTokenGeneration={'alternatives': [{'text': target}]})
        return row, observation

    def test_short_typo_reports_actual_application_retrieval_and_undo(self):
        row, obs = self.fixture()
        report = evaluate([row], [obs])['slices']['short_3_4']
        self.assertEqual((1, 1, 1, 0, 1.0),
                         (report['correct'], report['replacements'], report['retrievedTypos'], report['undoFailures'], report['recall']))

    def test_retrieval_without_application_is_not_correction(self):
        row, obs = self.fixture(changed=False)
        report = evaluate([row], [obs])['slices']['all']
        self.assertEqual((0, 1, None), (report['correct'], report['retrievedTypos'], report['precision']))

    def test_no_auto_and_correct_controls_never_count_as_success(self):
        for cohort, no_auto in [('correct', False), ('typo', True), ('protected', True)]:
            row, obs = self.fixture(cohort=cohort, no_auto=no_auto)
            report = evaluate([row], [obs])['slices']['all']
            self.assertEqual((0, 1, 1), (report['correct'], report['incorrect'], report['controlChanges']))

    def test_unknown_or_failed_undo_is_counted_as_failure(self):
        for value in [False, None]:
            row, obs = self.fixture()
            obs['restoredBeforeBoundaryExactly'] = value
            self.assertEqual(1, evaluate([row], [obs])['slices']['all']['undoFailures'])

    def test_identity_context_and_completion_fail_closed(self):
        row, original = self.fixture()
        for field, value in [('id', 'foreign'), ('prefix', ''), ('typed', 'other'), ('status', 'FAILED'),
                             ('boundaryChangedBeyondInsertedSpace', False)]:
            obs = deepcopy(original); obs[field] = value
            with self.assertRaises(ValueError): evaluate([row], [obs])
        with self.assertRaises(ValueError): evaluate([row, row], [original, original])

    def test_transpositions_are_one_unit_edit_and_multiple_errors_remain_separate(self):
        self.assertEqual(1, edit_distance('зочy', 'зчоy'))
        self.assertEqual(2, edit_distance('решкнте', 'решение'))
        row, obs = self.fixture('решкнте', 'решение')
        self.assertEqual(1, evaluate([row], [obs])['slices']['multi_edit']['correct'])

    def test_reports_mechanical_input_changes_without_losing_rows(self):
        row, obs = self.fixture()
        row['prefix'] = 'foo,bar'; obs['prefix'] = 'foo,bar'
        obs['beforeBoundary']['text'] = 'foo, bar зочу'
        obs['afterBoundary']['text'] = 'foo, bar хочу '
        obs['inputChangedByTyping'] = True
        report = evaluate([row], [obs])['slices']['all']
        self.assertEqual((1, 0, 1), (report['inputTransformations'], report['prefixChanges'], report['correct']))
        obs['afterBoundary']['text'] = 'corrupted хочу '
        report = evaluate([row], [obs])['slices']['all']
        self.assertEqual((1, 0), (report['prefixChanges'], report['correct']))

    def test_empty_data_has_no_invented_quality(self):
        self.assertEqual({}, evaluate([], [])['slices'])
