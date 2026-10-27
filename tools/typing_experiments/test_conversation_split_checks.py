import unittest
from conversation_split_checks import context_key, check_separation


def row(prefix='мы', typed='поггорим', target='поговорим', article='tatoeba:1', **extra):
    return dict(prefix=prefix, typed=typed, expectedSpelling=target, article=article, **extra)


class ConversationSplitChecksTest(unittest.TestCase):
    def test_normalization_keeps_punctuation_and_rejects_nontext(self):
        self.assertEqual(context_key(row(' МЫ\t')), context_key(row('мы')))
        self.assertNotEqual(context_key(row('мы,')), context_key(row('мы')))
        with self.assertRaises(ValueError): context_key(dict(prefix='', typed=1, expectedSpelling='слово'))

    def test_disclosed_cases_and_same_target_context_cannot_be_training(self):
        disclosed = [row()]
        with self.assertRaisesRegex(ValueError, 'DISCLOSED_EVALUATION_REUSED'):
            check_separation({'train': [row(typed='погоорим', article='tatoeba:2')]}, iter(disclosed))
        for value in [row(), row(typed='погоорим', article='tatoeba:2'), row(prefix='ещё', article='tatoeba:1'),
                      row(prefix='завтра', article='tatoeba:3', purpose='REGRESSION_ONLY_NOT_TRAINING')]:
            with self.assertRaisesRegex(ValueError, 'DISCLOSED_EVALUATION_REUSED'):
                check_separation({'train': [value]}, disclosed)

    def test_sentence_or_prediction_context_overlap_fails(self):
        for other in [row(prefix='сегодня'), row(typed='погоорим', article='tatoeba:2')]:
            with self.assertRaises(ValueError): check_separation({'train': [row()], 'holdout': [other]}, [])

    def test_new_contexts_remain_separate_and_variants_stay_together(self):
        train = [row(), row(typed='погоорим')]
        check_separation({'train': train, 'calibration': [row(prefix='завтра', article='tatoeba:2')],
                          'holdout': [row(prefix='вечером', article='tatoeba:3')]}, [])
