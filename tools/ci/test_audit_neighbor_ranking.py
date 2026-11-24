import copy
import unittest

import audit_neighbor_ranking as subject


def fixture():
    row = {'id': 'x', 'typed': 'опч', 'expected': 'очь'}
    disclosed = {'sourceId': 'x', 'prefix': 'пример', 'typed': 'ночь'}
    obs = {'id': 'x', 'status': 'COMPLETE', 'beforeBoundary': {'text': 'пример опч'},
           'afterBoundary': {'text': 'пример ночь '}, 'afterBackspace': {'text': 'пример опч'},
           'autoEdit': {'correctionGeneration': {'alternatives': [{'text': 'ночь', 'unitDistance': 1}, {'text': 'очь', 'unitDistance': 2}]}},
           'automaticAdmissionCandidate': 'ночь',
           'jointSearch': {'alternatives': [{'text': 'ночь'}, {'text': 'очь'}]},
           'jointModelScores': [0.0, 1.0, 2.0],
           'jointSourceAdmission': {'очь': False}, 'jointSourceRefusals': {'очь': 'RIVAL_UNKNOWN'}}
    return (row, disclosed), obs


class NeighborRankingTest(unittest.TestCase):
    def test_distinguishes_search_score_and_hypothetical_refusal(self):
        pair, obs = fixture()
        result = subject.analyze([pair], [obs])
        self.assertEqual(1, result['rows'])
        self.assertEqual(1, result['target_in_joint_pool'])
        self.assertEqual(1, result['target_highest_raw_joint_score'])
        self.assertEqual(1, result['hypothetical_target_refused_RIVAL_UNKNOWN'])
        self.assertEqual(0, result['target_highest_raw_score_and_admitted'])

    def test_corrupted_output_undo_pool_score_or_guard_is_rejected(self):
        pair, obs = fixture()
        for key, value in [('afterBackspace', {'text': 'wrong'}), ('jointModelScores', [0.0]),
                           ('jointSourceAdmission', {'очь': True}),
                           ('automaticAdmissionCandidate', 'missing')]:
            changed = copy.deepcopy(obs)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                subject.analyze([pair], [changed])
        with self.assertRaises(ValueError):
            subject.analyze([pair, pair], [obs, obs])


if __name__ == '__main__':
    unittest.main()
