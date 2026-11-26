import json
import unittest
import replay_case_evidence_candidate as subject


class CaseCandidateTest(unittest.TestCase):
    def setUp(self):
        self.row = {'id': 'one', 'split': 'holdout', 'language': 'ru', 'prefix': 'нет',
                    'typed': 'клавы', 'expectedSpelling': 'клавы', 'cohort': 'correct'}
        self.old = {'id': 'one', 'index': 0, 'status': 'COMPLETE', **{k: self.row[k] for k in ('split', 'language', 'prefix', 'typed')},
                    'beforeBoundary': {'text': 'нет клавы'}, 'afterBoundary': {'text': 'нет Клавы '},
                    'boundaryChangedBeyondInsertedSpace': True, 'restoredBeforeBoundaryExactly': True}
        self.new = {**self.old, 'id': 'joint-replay-00000000', 'afterBoundary': {'text': 'нет клавы '},
                    'boundaryChangedBeyondInsertedSpace': False}
        self.review = {'purpose': subject.PURPOSE, 'cases': [
            {'id': 'one', 'typed': 'клавы', 'baseline': 'Клавы', 'label': 'lowercase_preserve'}]}

    def check(self, old=None, new=None, review=None):
        return subject.summarize([self.row], [json.dumps(old or self.old)],
                                 [json.dumps(new or self.new)], review or self.review)

    def test_overlay_is_narrow_and_refuses_bad_inputs(self):
        result = subject.overlay('before\n' + subject.MARKER + '\nafter', ['клавы', 'читы'])
        self.assertIn('original?.copy(unambiguous = false)', result)
        self.assertIn('language == KeyboardLanguage.RUSSIAN', result)
        for words in ([], ['читы', 'клавы'], ['клавы', 'клавы'], ['x"']):
            with self.subTest(words=words), self.assertRaises(ValueError):
                subject.overlay(subject.MARKER, words)
        with self.assertRaises(ValueError):
            subject.overlay('absent', ['клавы'])

    def test_real_boundary_comparison_and_review(self):
        result = self.check()
        self.assertEqual(1, result['differentBoundaryRows'])
        self.assertEqual(1, result['review_lowercase_preserved'])
        self.assertEqual(0, result['candidateControlChanges'])

    def test_name_contrast_counts_lost_source_case(self):
        row = {**self.row, 'split': 'calibration', 'article': '7', 'cohort': 'name_contrast',
               'purpose': 'DISCLOSED_NAME_CONTRAST_NOT_QUALIFICATION', 'expectedSpelling': 'Клавы'}
        old = {**self.old, 'split': 'calibration'}
        new = {**self.new, 'split': 'calibration'}
        result = subject.summarize_name_contrasts([row], [json.dumps(old)], [json.dumps(new)])
        self.assertEqual((1, 1, 0), (result['lostSourceCaseMatches'], result['baselineSourceCaseMatches'], result['candidateSourceCaseMatches']))
        with self.assertRaises(ValueError):
            subject.summarize_name_contrasts([{**row, 'expectedSpelling': 'клавы'}], [json.dumps(old)], [json.dumps(new)])

    def test_collision_requires_same_inputs_and_reports_opposing_senses(self):
        rows = [{**self.row, 'id': sense, 'split': 'calibration', 'cohort': 'case_collision',
                 'purpose': 'DISCLOSED_CONTEXT_COLLISION_NOT_QUALIFICATION', 'sense': sense,
                 'expectedSpelling': spelling} for sense, spelling in [('common', 'клавы'), ('name', 'Клавы')]]
        old = [{**self.old, 'id': row['id'], 'index': i, 'split': 'calibration'} for i, row in enumerate(rows)]
        new = [{**self.new, 'id': f'joint-replay-{i:08d}', 'index': i, 'split': 'calibration'} for i in range(2)]
        result = subject.summarize_context_collision(rows, map(json.dumps, old), map(json.dumps, new))
        self.assertEqual((0, 1, 1, 0), (result['baseline_common_matches'], result['baseline_name_matches'],
                                      result['candidate_common_matches'], result['candidate_name_matches']))
        with self.assertRaisesRegex(ValueError, 'COLLISION_INPUTS_DIFFER'):
            subject.summarize_context_collision([rows[0], {**rows[1], 'prefix': 'жду'}], map(json.dumps, old), map(json.dumps, new))
        with self.assertRaisesRegex(ValueError, 'COLLISION_UNEXPECTED_NONDETERMINISM'):
            altered = [new[0], {**new[1], 'afterBoundary': {'text': 'нет Клавы '}, 'boundaryChangedBeyondInsertedSpace': True}]
            subject.summarize_context_collision(rows, map(json.dumps, old), map(json.dumps, altered))

    def test_refuses_missing_identity_or_bad_boundary(self):
        with self.assertRaises(ValueError):
            self.check(new={**self.new, 'id': 'other'})
        with self.assertRaises(ValueError):
            self.check(new={**self.new, 'boundaryChangedBeyondInsertedSpace': True})
        with self.assertRaises(ValueError):
            self.check(review={**self.review, 'cases': [{**self.review['cases'][0], 'id': 'missing'}]})


if __name__ == '__main__':
    unittest.main()
