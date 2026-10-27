import copy
import unittest

from right_context_continuation_calibration import path_metrics, select_path_policy, validate_paths


def path(key='one', first='готов', last='готовы', expected='готовы', control=False):
    return dict(id=key, original='готв', previous='готв', expected=expected, control=control,
                rightContext=' он .', steps=[
                    dict(prefixLength=4, completedWords=1, rightContext=' он ', proposed=first,
                         score=.8, margin=.5, sourceCertified=True),
                    dict(prefixLength=5, completedWords=1, rightContext=' он .', proposed=last,
                         score=.9, margin=.6, sourceCertified=True)])


POLICY = dict(minimumScore=.7, minimumMargin=.4)


class ContinuationCalibrationTest(unittest.TestCase):
    def test_first_wrong_is_not_hidden_by_correct_same_word_count_closure(self):
        row = path()
        validate_paths([row])
        metrics = path_metrics([row], POLICY)
        self.assertEqual(0, metrics['newCorrect'])
        self.assertEqual(1, metrics['newWrong'])
        self.assertEqual({'1': 1}, metrics['firstBoundaryActions'])
        metrics = path_metrics([row], dict(minimumScore=.85, minimumMargin=.55))
        self.assertEqual(1, metrics['newCorrect'])
        self.assertEqual(0, metrics['newWrong'])

    def test_only_recorded_actual_events_can_be_source_certified(self):
        for changes in ({'prefixLength': 3}, {'prefixLength': 4, 'rightContext': ' они '},
                        {'completedWords': 2}, {'sourceCertified': 1},
                        {'margin': float('nan')}, {'proposed': 'готв'}):
            row = path()
            row['steps'][0].update(changes)
            with self.assertRaises(ValueError):
                validate_paths([row])
        row = path()
        row['steps'].reverse()
        with self.assertRaises(ValueError):
            validate_paths([row])

    def test_first_action_and_original_control_losses_are_retained(self):
        row = path(expected='готв', control=True)
        metrics = path_metrics([row], POLICY)
        self.assertEqual(1, metrics['priorCorrectLosses'])
        self.assertEqual(1, metrics['installedCorrectLosses'])
        self.assertEqual(1, metrics['controlChanges'])

    def test_fitting_preserves_volume_requirement_and_actual_first_action(self):
        rows = [path(str(i)) for i in range(100)]
        self.assertIsNone(select_path_policy(rows, required_precision=1, minimum_correct=101))
        fitted = select_path_policy(rows, required_precision=1, minimum_correct=100)
        self.assertIsNotNone(fitted)
        self.assertEqual(100, fitted['calibrationMetrics']['newCorrect'])
        self.assertGreater(fitted['minimumScore'], .8)
        self.assertEqual(0, fitted['calibrationMetrics']['newWrong'])
        self.assertIsNone(select_path_policy(rows + [path('control', expected='готв', control=True)], required_precision=1))

    def test_bad_requirements_duplicates_and_empty_policy_fail_closed(self):
        for changes in ({'required_precision': 0}, {'required_precision': float('nan')},
                        {'required_precision': 1, 'minimum_correct': 0},
                        {'required_precision': 1, 'grid_points': 100}):
            with self.assertRaises(ValueError):
                select_path_policy([path()], **changes)
        with self.assertRaises(ValueError):
            validate_paths([path(), copy.deepcopy(path())])
        with self.assertRaises(ValueError):
            path_metrics([], dict(minimumScore=.5, minimumMargin=0))


if __name__ == '__main__':
    unittest.main()
