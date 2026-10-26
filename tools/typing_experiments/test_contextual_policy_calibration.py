import copy
import unittest

from contextual_policy_calibration import accepted, proposal_metrics, select_policy


POLICY = dict(minimumScore=0.0, minimumMargin=0.01)


def records(correct=100, wrong=0):
    return [dict(id=str(i), typed='исходное', expected='нужное', baseline='исходное', control=False,
                 reference=dict(candidate='исходное', score=0.5, margin=0.1),
                 experimental=dict(candidate='нужное' if i < correct else 'другое', score=0.5, margin=0.1))
            for i in range(correct + wrong)]


class ContextualPolicyCalibrationTest(unittest.TestCase):
    def test_stricter_calibration_ratio_rejects_barely_passing_final_ratio(self):
        rows = records(100, 3)
        self.assertIsNotNone(select_policy(rows, POLICY, required_precision=.95))
        self.assertIsNone(select_policy(rows, POLICY, required_precision=.975))
        self.assertIsNotNone(select_policy(records(100, 2), POLICY, required_precision=.975))

    def test_precision_recomputed_from_counts_and_minimum_volume_preserved(self):
        metrics = proposal_metrics(records(100, 6), POLICY, POLICY)
        metrics['precision'] = 1.0
        self.assertFalse(accepted(metrics, required_precision=.95))
        self.assertIsNone(select_policy(records(99), POLICY, required_precision=.975))

    def test_exact_precision_boundaries_and_net_count_integrity(self):
        for good, bad, ratio in ((95, 5, .95), (195, 5, .975)):
            metrics = proposal_metrics(records(good, bad), POLICY, POLICY)
            self.assertTrue(accepted(metrics, required_precision=ratio, minimum_new_correct=1))
            metrics = proposal_metrics(records(good - 1, bad + 1), POLICY, POLICY)
            self.assertFalse(accepted(metrics, required_precision=ratio, minimum_new_correct=1))
        metrics['netCorrectVsInstalled'] += 1
        with self.assertRaisesRegex(ValueError, 'INVALID_NET_COUNT'):
            accepted(metrics, required_precision=.95, minimum_new_correct=1)

    def test_no_fallback_for_empty_or_unqualified_calibration(self):
        self.assertIsNone(select_policy([], POLICY, required_precision=.975))
        self.assertIsNone(select_policy(records(100, 100), POLICY, required_precision=.975))

    def test_prior_correct_retention_is_independent_of_proposal_precision(self):
        rows = records()
        extra = copy.deepcopy(rows[0]);extra['id'] = 'prior'
        extra['baseline'] = extra['expected']
        extra['experimental']['candidate'] = extra['typed']
        rows.append(extra)
        metrics = proposal_metrics(rows, POLICY, POLICY)
        self.assertEqual(metrics['priorCorrectLosses'], 1)
        self.assertFalse(accepted(metrics, required_precision=.975))

    def test_installed_correct_loss_is_a_separate_refusal(self):
        rows = records()
        rows[0]['reference']['candidate'] = rows[0]['expected']
        rows[0]['experimental']['candidate'] = rows[0]['typed']
        metrics = proposal_metrics(rows, POLICY, POLICY)
        self.assertEqual(metrics['priorCorrectLosses'], 0)
        self.assertEqual(metrics['installedCorrectLosses'], 1)
        self.assertIsNone(select_policy(rows, POLICY, required_precision=.975, minimum_new_correct=1))

    def test_control_changes_refuse_policy_and_input_stays_unchanged(self):
        rows = records()
        control = copy.deepcopy(rows[0]);control.update(id='control', expected='исходное', control=True)
        rows.append(control);before = copy.deepcopy(rows)
        self.assertIsNone(select_policy(rows, POLICY, required_precision=.975))
        self.assertEqual(rows, before)

    def test_ties_and_quantile_grid_are_deterministic(self):
        rows = records()
        first = select_policy(rows, POLICY, required_precision=.975)
        self.assertEqual(first, select_policy(list(reversed(rows)), POLICY, required_precision=.975))
        self.assertEqual(first['minimumScore'], .5)
        self.assertEqual(first['minimumMargin'], .1)

    def test_schema_nonfinite_and_duplicate_ids_fail_closed(self):
        for field in ('score', 'margin'):
            for value in (float('nan'), float('inf'), True):
                rows = records();rows[0]['experimental'][field] = value
                with self.assertRaises(ValueError):
                    select_policy(rows, POLICY, required_precision=.975)
        rows = records();rows.append(rows[0])
        with self.assertRaisesRegex(ValueError, 'CALIBRATION_ROW_IDENTITY'):
            select_policy(rows, POLICY, required_precision=.975)
        for ratio in (0, 1.1, float('nan'), True):
            with self.assertRaises(ValueError):
                select_policy([], POLICY, required_precision=ratio)
        with self.assertRaises(ValueError):
            select_policy([], POLICY, required_precision=.975, grid_points=1)


if __name__ == '__main__':
    unittest.main()
