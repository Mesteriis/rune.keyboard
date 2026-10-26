from copy import deepcopy
import unittest

from grammar_revision_calibration import revision_metrics, select_revision_policy, stage_records


def rows(good=100, wrong=0):
    return [dict(id=str(i), original='опечатка', previous='учишься', proposed='учиться',
                 expected='учиться' if i < good else 'учишься', control=False,
                 score=.5, margin=.1) for i in range(good + wrong)]


class GrammarRevisionCalibrationTest(unittest.TestCase):
    def test_revisions_are_counted_from_installed_result_and_original_is_preserved(self):
        values = rows();before = deepcopy(values)
        policy = select_revision_policy(values, required_precision=.975)
        self.assertIsNotNone(policy)
        metrics = revision_metrics(values, policy)
        self.assertEqual(metrics['newCorrect'], 100)
        self.assertEqual(metrics['netCorrectVsInstalled'], 100)
        self.assertEqual(stage_records(values)[0]['editorOriginal'], 'опечатка')
        self.assertEqual(values, before)

    def test_prior_correct_loss_rejects_even_when_aggregate_precision_is_high(self):
        self.assertIsNone(select_revision_policy(rows(200, 1), required_precision=.975))

    def test_minimum_incremental_volume_is_not_satisfied_by_old_spelling_gains(self):
        self.assertIsNone(select_revision_policy(rows(99), required_precision=.975))
        self.assertIsNone(select_revision_policy([], required_precision=.975))

    def test_threshold_abstention_retains_installed_result(self):
        metrics = revision_metrics(rows(), dict(minimumScore=.6, minimumMargin=.1))
        self.assertEqual(metrics['newCorrect'], 0)
        self.assertEqual(metrics['installedCorrectLosses'], 0)

    def test_original_or_unchanged_proposals_are_not_revisions(self):
        for key, value in [('previous', 'опечатка'), ('proposed', 'опечатка'), ('proposed', 'учишься')]:
            values = rows(1);values[0][key] = value
            with self.assertRaisesRegex(ValueError, 'REVISION_STAGE_SCHEMA'):
                stage_records(values)


if __name__ == '__main__':
    unittest.main()
