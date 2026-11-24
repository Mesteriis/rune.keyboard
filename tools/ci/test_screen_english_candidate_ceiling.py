import copy
import unittest

import generate_product_replay_v1 as corpus
import screen_english_candidate_ceiling as subject


def fixture():
    origin = dict(group=0, language='en', target={'word': 'nerd'}, context=[{'word': 'hello'}])
    inputs, observations = [], []
    for index, token in enumerate(corpus.variants('nerd')):
        row = dict(language='en', split='calibration', prefix='hello', typed=token)
        generation = dict(original=token, completion='STATES_EXHAUSTED', prohibitsAutoReplace=True,
                          alternatives=[dict(language='en', text='nerd')])
        if index == 2:
            generation.update(completion='COMPLETE', prohibitsAutoReplace=False,
                              alternatives=[dict(language='en', text='other')])
        inputs.append(row)
        observations.append(row | dict(index=index, fullTokenGeneration=generation))
    return inputs, [origin], observations


class CandidateCeilingTest(unittest.TestCase):
    def test_seen_candidate_and_search_refusal_are_separate(self):
        result = subject.screen(*fixture())
        self.assertEqual(1, result['delete-middle']['targetInAlternatives'])
        self.assertEqual(1, result['delete-middle']['targetSeenButSearchProhibitsAuto'])
        self.assertEqual(0, result['delete-middle']['targetSeenAndSearchAllowsAuto'])
        self.assertEqual(1, result['transpose-first']['targetAbsent'])
        self.assertEqual(0, result['transpose-first']['targetSeenAndSearchAllowsAuto'])

    def test_altered_row_and_observation_are_rejected(self):
        inputs, origins, observations = fixture()
        altered = copy.deepcopy(observations)
        altered[1]['index'] = 2
        with self.assertRaisesRegex(ValueError, 'EN_SCREEN_ALIGNMENT'):
            subject.screen(inputs, origins, altered)
        altered = copy.deepcopy(inputs)
        altered[1]['typed'] = 'other'
        observations[1]['typed'] = 'other'
        with self.assertRaisesRegex(ValueError, 'EN_SCREEN_TRANSFORM'):
            subject.screen(altered, origins, observations)

    def test_incomplete_or_malformed_generation_is_rejected(self):
        inputs, origins, observations = fixture()
        observations[1]['fullTokenGeneration']['prohibitsAutoReplace'] = None
        with self.assertRaisesRegex(ValueError, 'EN_SCREEN_GENERATION'):
            subject.screen(inputs, origins, observations)
        with self.assertRaisesRegex(ValueError, 'EN_SCREEN_COUNT'):
            subject.screen(inputs[:-1], origins, observations)


if __name__ == '__main__':
    unittest.main()
