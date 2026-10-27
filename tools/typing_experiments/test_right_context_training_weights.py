import unittest

from right_context_training_weights import strong_supervision_weight


def row(**changes):
    return dict(purpose='AUTHORED_RIGHT_CONTEXT_TRAINING_ONLY', split='train', language='ru',
                original='готв', applied='готова', expectedApplied='готов', kind='unknown_original') | changes


class TrainingWeightsTest(unittest.TestCase):
    def test_raw_acquisition_correct_retention_and_wrong_state_repair_have_equal_confidence(self):
        for applied in ('готв', 'готов', 'готова'):
            self.assertEqual(3., strong_supervision_weight(row(applied=applied)))

    def test_unresolved_and_correct_original_controls_keep_their_old_weight(self):
        for applied in ('готв', 'готов', 'готова'):
            self.assertEqual(1., strong_supervision_weight(row(kind='insufficient_right_evidence', applied=applied, expectedApplied=applied)))
        self.assertEqual(1., strong_supervision_weight(row(kind='correct_original', original='готов', applied='готов')))

    def test_weight_is_not_selected_by_scores_words_family_or_scenario(self):
        example = row(original='неивестн', applied='неизвестно', expectedApplied='неизвестен',
                      score=float('inf'), family='ignored', scenario='ignored')
        self.assertEqual(3., strong_supervision_weight(example))
        self.assertEqual(3., strong_supervision_weight(row(score=-1., family='other', scenario='other')))

    def test_holdout_incomplete_and_unlabelled_rows_cannot_enter_the_policy(self):
        for value in (None, {}, row(split='holdout'), row(language='en'), row(purpose='OTHER'),
                      row(original=''), row(applied=None), row(kind='other')):
            with self.assertRaises(ValueError):
                strong_supervision_weight(value)

    def test_inconsistent_retention_and_unknown_labels_fail_explicitly(self):
        for value in (row(kind='correct_original'), row(kind='insufficient_right_evidence'),
                      row(expectedApplied='готв')):
            with self.assertRaises(ValueError):
                strong_supervision_weight(value)


if __name__ == '__main__':
    unittest.main()
