import unittest
from copy import deepcopy
from local_spelling_stress import audit, cases, percentile, variants


class LocalSpellingStressTest(unittest.TestCase):
    def fixture(self):
        row = dict(id='one', typed='ддмой', prefix='', expectedSpelling='домой',
                   cohort='typo', noAuto=False, family='neighbour')
        obs = dict(id='one', typed='ддмой', prefix='', status='COMPLETE',
                   beforeBoundary={'text': 'ддмой'}, afterBoundary={'text': 'домой '},
                   boundaryChangedBeyondInsertedSpace=True, restoredBeforeBoundaryExactly=True,
                   hostStageNanos={'baselineSearch': 2_000_000})
        return row, obs

    def test_deterministic_unique_cases_cover_edits_and_controls(self):
        rows = cases()
        self.assertEqual(rows, cases())
        self.assertEqual(len(rows), len({row['id'] for row in rows}))
        self.assertEqual({'missing', 'repeated', 'transposed', 'neighbour', 'control'},
                         {row['family'] for row in rows})
        self.assertTrue(all(row['typed'] for row in rows))
        self.assertTrue(all(row['noAuto'] for row in rows if row['family'] == 'control'))
        self.assertIn('Анна', [row['typed'] for row in rows])

    def test_variants_preserve_edit_intent_and_deduplicate(self):
        values = list(variants('мама'))
        self.assertEqual(len(values), len({text for _, text in values}))
        self.assertNotIn('мама', [text for _, text in values])
        self.assertIn(('missing', 'ама'), values)
        self.assertIn(('repeated', 'ммама'), values)
        self.assertIn(('transposed', 'амма'), values)
        self.assertIn(('neighbour', 'иама'), values)

    def test_report_success_and_exact_undo(self):
        row, obs = self.fixture()
        report = audit([row], [obs])
        self.assertEqual(1, report['slices']['all']['correct'])
        self.assertEqual([], report['unintendedSpellingChanges'])
        self.assertEqual(2.0, report['hostTimingMs']['baselineSearch']['p95'])
        obs['restoredBeforeBoundaryExactly'] = False
        self.assertEqual(1, audit([row], [obs])['slices']['all']['undoFailures'])

    def test_valid_original_abstention_not_invented_callback(self):
        row, obs = self.fixture()
        obs.update(afterBoundary={'text': 'ддмой '}, boundaryChangedBeyondInsertedSpace=False,
                   actualRequestGeneration={'isValidWord': True})
        report = audit([row], [obs])
        self.assertEqual({'rows': 1, 'retained': 1, 'caseOnlyChanges': 0, 'spellingChanges': 0}, report['dictionaryValidSyntheticTypos'])
        self.assertEqual({'VALID_ORIGINAL': 1}, report['automaticAbstentions'])
        obs['actualRequestGeneration'] = {}
        self.assertEqual({'NO_ADMISSION_CALLBACK': 1}, audit([row], [obs])['automaticAbstentions'])

    def test_wrong_replacement_and_control_are_failures(self):
        row, obs = self.fixture()
        obs['afterBoundary']['text'] = 'думаю '
        self.assertEqual(1, len(audit([row], [obs])['unintendedSpellingChanges']))
        row.update(cohort='correct', noAuto=True, expectedSpelling='ддмой', family='control')
        self.assertEqual(1, audit([row], [obs])['slices']['all']['controlChanges'])

    def test_case_only_departure_is_not_a_spelling_substitution(self):
        row, obs = self.fixture()
        obs['afterBoundary']['text'] = 'Ддмой '
        report = audit([row], [obs])
        self.assertEqual([], report['unintendedSpellingChanges'])
        self.assertEqual(1, len(report['caseOnlyDepartures']))
        self.assertEqual(0, report['slices']['all']['correct'])

    def test_corruption_or_partial_timings_fail_closed(self):
        row, obs = self.fixture()
        for changes in [dict(id='other'), dict(status='ERROR'), dict(hostStageNanos={'a': -1})]:
            altered = deepcopy(obs); altered.update(changes)
            with self.assertRaises(ValueError): audit([row], [altered])
        row2 = dict(row, id='two'); obs2 = dict(obs, id='two', hostStageNanos={})
        with self.assertRaises(ValueError): audit([row, row2], [obs, obs2])

    def test_nearest_rank_percentiles(self):
        self.assertEqual(3, percentile([5, 1, 3, 2, 4], .5))
        self.assertEqual(5, percentile([5, 1, 3, 2, 4], .95))
