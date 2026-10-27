import unittest
from copy import deepcopy
from right_context_source_calibration import source_stage_records,select_source_policy,source_metrics


def row(index,acquisition=True,**changes):
    r=dict(id=str(index),original='готв',previous='готв' if acquisition else 'готов',proposed='готовы',
           expected='готовы',control=False,sourceCertified=True,score=.6,margin=.2)
    r.update(changes);return r


class SourceCalibrationTest(unittest.TestCase):
    def test_acquisition_and_revision_gains_are_both_incremental_and_original_input_is_preserved(self):
        records=[row(i,acquisition=i<100) for i in range(150)];before=deepcopy(records)
        policy=select_source_policy(records,required_precision=1.0)
        self.assertIsNotNone(policy)
        self.assertEqual(150,source_metrics(records,policy)['newCorrect'])
        self.assertEqual('готв',source_stage_records(records)[100]['editorOriginal'])
        self.assertEqual(records,before)

    def test_source_certification_is_required_and_unchanged_or_original_is_not_a_new_correction(self):
        for changes in [dict(sourceCertified=False),dict(sourceCertified=1),dict(proposed='готв'),dict(proposed='готовы',previous='готовы')]:
            with self.assertRaisesRegex(ValueError,'CONTEXTUAL_SOURCE_STAGE_SCHEMA'):
                source_stage_records([row(1,**changes)])

    def test_prior_correct_loss_and_control_changes_reject_even_with_high_precision(self):
        records=[row(i) for i in range(200)]
        for bad in [row(201,acquisition=False,expected='готов'),row(201,acquisition=False,expected='готов',control=True)]:
            self.assertIsNone(select_source_policy(records+[bad],required_precision=.95))

    def test_minimum_volume_and_threshold_abstention_cannot_borrow_old_gains(self):
        self.assertIsNone(select_source_policy([row(i) for i in range(99)],required_precision=1.0))
        metrics=source_metrics([row(i) for i in range(100)],dict(minimumScore=.7,minimumMargin=.2))
        self.assertEqual(0,metrics['newCorrect']);self.assertEqual(0,metrics['installedCorrectLosses'])


if __name__ == '__main__':unittest.main()
