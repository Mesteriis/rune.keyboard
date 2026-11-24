import unittest

import screen_english_local_search as subject
from test_screen_english_candidate_ceiling import fixture


class EnglishLocalScreenTest(unittest.TestCase):
    def test_complete_local_result_distinguishes_unique_from_competing(self):
        inputs, origins, observations = fixture()
        observations[1]['fullTokenGeneration']['localSearch'] = dict(
            completion='COMPLETE', alternatives=[dict(language='en', text='nerd')])
        second = observations[2]['fullTokenGeneration']
        second.update(completion='STATES_EXHAUSTED', prohibitsAutoReplace=True,
                      localSearch=dict(completion='COMPLETE', alternatives=[
                          dict(language='es', text='otro'), dict(language='en', text='nerd')]))
        result = subject.screen(inputs, origins, observations)
        self.assertEqual(1, result['delete-middle']['targetOnlyInCompleteLocalPool'])
        self.assertEqual(1, result['delete-middle']['targetFirstInCompleteLocalPool'])
        self.assertEqual(1, result['transpose-first']['targetWithCompetitorsInCompleteLocalPool'])
        self.assertEqual(0, result['transpose-first']['targetFirstInCompleteLocalPool'])

    def test_partial_local_pool_is_not_counted_as_complete(self):
        inputs, origins, observations = fixture()
        observations[1]['fullTokenGeneration']['localSearch'] = dict(
            completion='STATES_EXHAUSTED', alternatives=[dict(language='en', text='nerd')])
        result = subject.screen(inputs, origins, observations)['delete-middle']
        self.assertEqual(1, result['localCompletion:STATES_EXHAUSTED'])
        self.assertNotIn('targetInCompleteLocalPool', result)

    def test_malformed_local_result_is_rejected(self):
        inputs, origins, observations = fixture()
        observations[1]['fullTokenGeneration']['localSearch'] = dict(completion='COMPLETE', alternatives=[{}])
        with self.assertRaisesRegex(ValueError, 'EN_LOCAL_SEARCH_SCHEMA'):
            subject.screen(inputs, origins, observations)


if __name__ == '__main__':
    unittest.main()
