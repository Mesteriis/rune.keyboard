from copy import deepcopy
import unittest

from grammar_training_groups import select_groups


def evidence(no_auto=False):
    row = dict(id='one', prefix='ты', typed='учищься', expectedSpelling='учишься',
               noAuto=no_auto, contrastCandidates=['учиться', 'учишься'],
               purpose='AUTHORED_CONTRAST_TRAINING_ONLY', split='train')
    if no_auto:
        row['typed'] = row['expectedSpelling']
    forms = ['учиться', 'учишься'] if not no_auto else ['учиться']
    observation = dict(id=row['id'], prefix=row['prefix'], typed=row['typed'], status='COMPLETE',
                       fullTokenGeneration=dict(isValidWord=False, prohibitsAutoReplace=False, protectedReason=None),
                       jointSearch=dict(completion='COMPLETE', alternatives=[dict(text=s) for s in forms]))
    return row, observation


class GrammarTrainingGroupsTest(unittest.TestCase):
    def test_target_selected_from_retrieved_pool_only_and_input_not_mutated(self):
        row, observation = evidence()
        before = deepcopy(observation)
        groups, skipped = select_groups([row], [observation])
        self.assertFalse(skipped)
        self.assertEqual(groups[0]['candidates'][groups[0]['target']]['text'], 'учишься')
        self.assertEqual(observation, before)
        observation['jointSearch']['alternatives'] = [dict(text='учиться')]
        self.assertEqual(select_groups([row], [observation]), ([], {'missing_target': 1}))

    def test_known_or_protected_original_never_becomes_a_correction_group(self):
        for key, value in (('isValidWord', True), ('protectedReason', 'IDENTIFIER')):
            row, observation = evidence()
            observation['fullTokenGeneration'][key] = value
            self.assertEqual(select_groups([row], [observation]), ([], {'protected_original': 1}))

    def test_complete_joint_pool_can_follow_exhausted_baseline_search(self):
        row, observation = evidence()
        observation['fullTokenGeneration'].update(prohibitsAutoReplace=True, completion='VERIFIED_EXHAUSTED')
        groups, skipped = select_groups([row], [observation])
        self.assertEqual(len(groups), 1)
        self.assertFalse(skipped)

    def test_retention_can_use_complete_manual_pool_and_target_is_original(self):
        row, observation = evidence(True)
        observation['fullTokenGeneration']['isValidWord'] = True
        observation['manualSearchGeneration'] = observation.pop('jointSearch')
        groups, skipped = select_groups([row], [observation])
        self.assertFalse(skipped)
        self.assertEqual(groups[0]['target'], 0)
        self.assertEqual(groups[0]['source'], 'authored-contrast-manual-retention')

    def test_identity_schema_and_duplicate_candidates_fail_closed(self):
        row, observation = evidence()
        for key, value in [('id', 'different'), ('typed', 'другое'), ('status', 'ERROR')]:
            changed = dict(observation, **{key: value})
            with self.assertRaisesRegex(ValueError, 'CONTRAST_REPLAY_IDENTITY'):
                select_groups([row], [changed])
        with self.assertRaisesRegex(ValueError, 'CONTRAST_ROW_IDENTITY'):
            select_groups([row, row], [observation, observation])
        observation['jointSearch']['alternatives'].append(dict(text='УЧИШЬСЯ'))
        with self.assertRaisesRegex(ValueError, 'CONTRAST_CANDIDATE_POOL'):
            select_groups([row], [observation])

    def test_incomplete_pool_changed_input_and_missing_contrast_are_skipped(self):
        row, observation = evidence()
        observation['jointSearch']['completion'] = 'PARTIAL'
        self.assertEqual(select_groups([row], [observation]), ([], {'incomplete_pool': 1}))
        observation['jointSearch']['completion'] = 'COMPLETE'
        observation['jointSearch']['alternatives'] = [dict(text='учишься')]
        self.assertEqual(select_groups([row], [observation]), ([], {'missing_contrast': 1}))
        observation['inputChangedByTyping'] = True
        self.assertEqual(select_groups([row], [observation]), ([], {'input_changed': 1}))

    def test_missing_original_protection_evidence_is_an_error(self):
        row, observation = evidence()
        observation.pop('fullTokenGeneration')
        with self.assertRaisesRegex(ValueError, 'CONTRAST_GENERATION_SCHEMA'):
            select_groups([row], [observation])


if __name__ == '__main__':
    unittest.main()
