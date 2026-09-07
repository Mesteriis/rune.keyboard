import unittest

import select_local_policy as select
import evaluate_local_holdout as holdout


def fixture(split='calibration', changed=True, undo=True, protected=False):
    row = {'id': split + '-1', 'split': split, 'language': 'en', 'typed': 'teh',
           'cohort': 'protected' if protected else 'typo', 'expectedSpelling': 'the', 'noAuto': protected}
    observation = {'id': row['id'], 'split': split, 'language': 'en', 'typed': 'teh', 'prefix': '',
        'status': 'COMPLETE', 'inputChangedByTyping': False, 'currentQualificationWithoutModel': False,
        'boundaryChangedBeyondInsertedSpace': changed, 'afterBoundary': {'text': 'the ' if changed else 'teh '},
        'restoredBeforeBoundaryExactly': undo, 'candidateView': {'candidates': [{'text': 'teh', 'role': 'ORIGINAL'}]},
        'fullTokenGeneration': {'alternatives': [{'text': 'the', 'kind': 'COMMON_CONFUSION'}], 'protectedReason': None}}
    return row, observation


class LocalQualificationTest(unittest.TestCase):
    def test_selection_rejects_a_protected_change_even_before_holdout(self):
        row, obs = fixture(protected=True)
        with self.assertRaises(ValueError): select.select([row], [obs], {})
    def test_existing_canonical_change_is_reported_separately_from_finite_spelling(self):
        row, obs = fixture('holdout')
        obs['fullTokenGeneration']['alternatives'][0]['kind'] = 'CANONICAL_CASE'
        result = holdout.metrics([row], [obs])
        self.assertEqual(0, result['replacements'])
        self.assertEqual(1, result['otherAutomaticChanges'])
    def test_selection_rejects_holdout_and_never_activates_general_ranking(self):
        row, obs = fixture()
        config = select.select([row], [obs], {'artifact': 'frozen'})
        self.assertFalse(config['generalLocalEnabled'])
        hr, ho = fixture('holdout')
        with self.assertRaises(ValueError):
            select.select([hr], [ho], {})

    def test_holdout_rejects_overlap_and_artifact_drift(self):
        row, obs = fixture()
        config = select.select([row], [obs], {'artifact': 'frozen'})
        hr, ho = fixture('holdout')
        with self.assertRaises(ValueError):
            holdout.evaluate(config, [hr], [ho], {'artifact': 'changed'})
        hr['id'] = ho['id'] = row['id']
        with self.assertRaises(ValueError):
            holdout.evaluate(config, [hr], [ho], {'artifact': 'frozen'})

    def test_one_protected_change_or_inexact_undo_or_missing_original_fails(self):
        for mutation in ('protected', 'undo', 'original'):
            row, obs = fixture('holdout', protected=mutation == 'protected', undo=mutation != 'undo')
            if mutation == 'original': obs['candidateView']['candidates'] = []
            self.assertFalse(holdout.metrics([row], [obs])['pass'])


if __name__ == '__main__': unittest.main()
