"""Behavioral checks for retrieval evaluation denominators and trust boundaries."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import evaluate_retrieval as evaluation


def row(errors=1):
    return dict(id='test', typed='превет' if errors else 'привет', expectedSpelling='привет', prefix='он сказал ',
        cohort='typo' if errors else 'correct', noAuto=errors == 0, errorCount=errors)


def candidate(text):
    return dict(text=text, canonicalKey=text)


def generation(words):
    return dict(alternatives=[candidate(w) for w in words], completion='COMPLETE', inspectedStates=10, verifiedTerminals=2)


def observation(base, extra):
    return dict(generation=generation(base), manual=generation(extra) if extra is not None else None,
        baseline=None, generationMs=1., manualMs=2.)


class RetrievalEvaluationTest(unittest.TestCase):
    def summarize(self, rows, observations, values=None):
        with patch.object(evaluation.neural, 'load_model', return_value=object()), \
             patch.object(evaluation.neural, 'context_score', return_value=0.), \
             patch.object(evaluation.rank, 'scores', side_effect=lambda _, groups: [
                 values or list(range(len(groups[0][1])))]):
            return evaluation.summarize(rows, observations)

    def test_missing_gold_and_empty_pools_remain_in_denominator(self):
        result = self.summarize([row(), row(2), row(3)], [observation([], []),
            observation(['ответ'], ['ответ', 'привет']), observation(['ответ'], None)])
        all_rows = result['cohorts']['all']
        self.assertEqual(3, all_rows['rows'])
        self.assertEqual(0, all_rows['baseline']['goldAvailable'])
        self.assertEqual(1, all_rows['expanded']['goldAvailable'])
        self.assertEqual(1, all_rows['expanded']['combinedTop1'])
        self.assertEqual(0, result['cohorts']['3']['expanded']['goldAvailable'])

    def test_visible_two_is_separate_from_coverage_and_top_three(self):
        result = self.summarize([row()], [observation(['слово'], ['слово', 'ответ', 'привет'])], [3., 2., 1.])
        expanded = result['cohorts']['all']['expanded']
        self.assertEqual(1, expanded['goldAvailable'])
        self.assertEqual(0, expanded['combinedTop2'])
        self.assertEqual(1, expanded['combinedTop3'])

    def test_ties_preserve_baseline_first_order(self):
        result = self.summarize([row()], [observation(['привет'], ['привет', 'ответ'])], [1., 1.])
        self.assertEqual(1, result['cohorts']['all']['expanded']['combinedTop1'])

    def test_controls_are_excluded_and_report_supplemental_changes(self):
        result = self.summarize([row(0)], [observation([], [])])
        self.assertEqual(0, result['cohorts']['all']['rows'])
        self.assertEqual({'rows': 1, 'supplementalChanges': 0, 'localAutomaticProposals': 0}, result['correctControls'])
        wrong = row(0); wrong['typed'] = 'превет'
        with self.assertRaisesRegex(ValueError, 'CONTROL_MUTATED'):
            self.summarize([wrong], [observation([], [])])

    def test_lost_baseline_duplicate_and_overbudget_are_rejected(self):
        for obs, error in [(observation(['ответ'], ['привет']), 'BASELINE_LOST'),
            (observation([], ['привет', 'привет']), 'POOL_BOUND')]:
            with self.assertRaisesRegex(ValueError, error):
                self.summarize([row()], [obs])
        obs = observation([], [])
        obs['manual']['inspectedStates'] = 8193
        with self.assertRaisesRegex(ValueError, 'SEARCH_BUDGET'):
            self.summarize([row()], [obs])

    def test_fresh_evaluation_requires_prefrozen_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest, selection = [Path(directory) / n for n in ('manifest.json', 'selection.json')]
            manifest.write_text('{}')
            selection.write_text(json.dumps({'frozenBeforeFreshEvaluation': False}))
            with self.assertRaisesRegex(ValueError, 'FROZEN_SELECTION_REQUIRED'):
                evaluation.verify_fresh([], manifest, selection)


if __name__ == '__main__':
    unittest.main()
