import copy
import unittest
from unittest.mock import patch

import chat_case_review as subject


class CaseReviewTest(unittest.TestCase):
    def setUp(self):
        self.rows = [{'id': 'case', 'edit_kind': 'control', 'cohort': 'correct',
                      'noAuto': True, 'typed': 'клавы', 'expectedSpelling': 'клавы'}]
        self.observations = [{'boundaryChangedBeyondInsertedSpace': True,
                              'beforeBoundary': {'text': 'нет клавы'},
                              'afterBoundary': {'text': 'нет Клавы '}}]
        self.review = {'schema': 1, 'purpose': subject.PURPOSE, 'cases': [
            {'id': 'case', 'typed': 'клавы', 'baseline': 'Клавы', 'label': 'lowercase_preserve'}]}
        self.validator = patch.object(subject, 'evaluate')
        self.validator.start()
        self.addCleanup(self.validator.stop)

    def test_review_counts_disclosed_case(self):
        result = subject.audit(self.rows, self.observations, self.review)
        self.assertEqual({'lowercase_preserve': 1}, result['counts'])
        self.assertFalse(result['independentQualification'])

    def test_missing_duplicate_and_unobserved_cases_fail(self):
        for cases in ([], self.review['cases'] * 2,
                      [{'id': 'other', 'typed': 'клавы', 'baseline': 'Клавы', 'label': 'lowercase_preserve'}]):
            review = {**self.review, 'cases': cases}
            with self.subTest(cases=cases), self.assertRaises(ValueError):
                subject.audit(self.rows, self.observations, review)

    def test_output_or_label_mutation_fails(self):
        for field, value in [('typed', 'дома'), ('baseline', 'Клава'), ('label', 'invented')]:
            review = copy.deepcopy(self.review)
            review['cases'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                subject.audit(self.rows, self.observations, review)
        obs = copy.deepcopy(self.observations)
        obs[0]['afterBoundary']['text'] = 'нет клава '
        with self.assertRaises(ValueError):
            subject.audit(self.rows, obs, self.review)

    def test_compare_requires_exact_case_but_accepts_fixed_output(self):
        result = subject.compare(self.rows, self.observations, self.review)
        self.assertEqual((1, 0, ['case']), (result['checked'], result['preserved'], result['failureIds']))
        fixed = copy.deepcopy(self.observations)
        fixed[0]['afterBoundary']['text'] = 'нет клавы '
        self.assertEqual(1, subject.compare(self.rows, fixed, self.review)['preserved'])
        missing = copy.deepcopy(self.review)
        missing['cases'][0]['id'] = 'missing'
        with self.assertRaises(ValueError):
            subject.compare(self.rows, self.observations, missing)

    def test_compare_tracks_apparent_names_and_excludes_ambiguous_cases(self):
        for key, label in [('name', 'proper_name'), ('uncertain', 'ambiguous')]:
            self.rows.append({'id': key, 'edit_kind': 'control', 'cohort': 'correct',
                              'noAuto': True, 'typed': 'моника', 'expectedSpelling': 'моника'})
            self.observations.append({'boundaryChangedBeyondInsertedSpace': True,
                                      'beforeBoundary': {'text': 'привет моника'},
                                      'afterBoundary': {'text': 'привет Моника '}})
            self.review['cases'].append({'id': key, 'typed': 'моника', 'baseline': 'Моника', 'label': label})
        result = subject.compare(self.rows, self.observations, self.review)
        self.assertEqual((1, 1, [], 1), (result['apparentNameChecked'],
            result['apparentNameSourceCaseMatched'], result['apparentNameFailureIds'], result['ambiguousExcluded']))
        self.observations[1]['afterBoundary']['text'] = 'привет моника '
        result = subject.compare(self.rows, self.observations, self.review)
        self.assertEqual((0, ['name']), (result['apparentNameSourceCaseMatched'], result['apparentNameFailureIds']))
        self.review['cases'][1]['baseline'] = 'другое'
        with self.assertRaisesRegex(ValueError, 'CASE_REVIEW_BASELINE'):
            subject.compare(self.rows, self.observations, self.review)

    def test_same_case_does_not_claim_case_change(self):
        obs = copy.deepcopy(self.observations)
        obs[0]['afterBoundary']['text'] = 'нет клавы '
        with self.assertRaises(ValueError):
            subject.audit(self.rows, obs, self.review)


if __name__ == '__main__':
    unittest.main()
