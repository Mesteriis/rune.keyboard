import copy
import unittest
from right_context_training_groups import query, select_groups


def row(key='one', **changes):
    result=dict(id=key,purpose='AUTHORED_RIGHT_CONTEXT_TRAINING_ONLY',split='train',
                leftContext='тогда ',rightContext=' будут они ',original='готв',applied='готов',
                expectedApplied='готовы',candidateForms=['готов','готовы'],kind='unknown_original')
    result.update(changes);return result


def observation(r):
    return dict(**query(r),status='COMPLETE',inputChangedByTyping=False,
                fullTokenGeneration=dict(isValidWord=False,protectedReason=None),
                jointSearch=dict(completion='COMPLETE',alternatives=[dict(text=w) for w in ['готов','готовы']]))


class RightTrainingGroupsTest(unittest.TestCase):
    def test_query_never_depends_on_expected_label_applied_word_or_future_suffix(self):
        r=row();changed=row(expectedApplied='готов',applied='готовы',rightContext=' будет он ')
        self.assertEqual(query(r),query(changed))
        groups,skips=select_groups([r,changed|{'id':'two'}],[observation(r)])
        self.assertFalse(skips);self.assertEqual([2,1],[g['target'] for g in groups])
        self.assertTrue(all(g['counterfactualApplied'] for g in groups))

    def test_absent_target_or_applied_is_not_injected(self):
        r=row();o=observation(r);o['jointSearch']['alternatives']=[dict(text='готов')]
        self.assertEqual(([],{'missing_target':1}),select_groups([r],[o]))
        r['applied']='другой'
        self.assertEqual(([],{'missing_applied':1}),select_groups([r],[o]))

    def test_protected_changed_or_incomplete_unknowns_do_not_supply_training_groups(self):
        r=row()
        for field,value,reason in [('isValidWord',True,'original_protected'),('protectedReason','IDENTIFIER','original_protected')]:
            o=observation(r);o['fullTokenGeneration'][field]=value
            self.assertEqual(([],{reason:1}),select_groups([r],[o]))
        o=observation(r);o['inputChangedByTyping']=True
        self.assertEqual(([],{'input_changed':1}),select_groups([r],[o]))
        o=observation(r);o['jointSearch']['completion']='STATES_EXHAUSTED'
        self.assertEqual(([],{'incomplete_pool':1}),select_groups([r],[o]))

    def test_correct_original_can_use_an_explicit_manual_retention_pool(self):
        r=row(kind='correct_original',original='готов',applied='готов',expectedApplied='готов')
        o=observation(r);o['fullTokenGeneration']['isValidWord']=True
        o['jointSearch']={};o['manualSearchGeneration']=dict(completion='COMPLETE',alternatives=[dict(text='готовы')])
        groups,skips=select_groups([r],[o]);self.assertFalse(skips)
        self.assertEqual('manual-retention',groups[0]['source']);self.assertEqual(0,groups[0]['target'])

    def test_no_holdout_labels_duplicate_queries_or_changed_replay_identity(self):
        r=row();o=observation(r)
        for rows,observations in [([r|{'split':'holdout'}],[o]),([r],[o,o]),([r],[o|{'prefix':'другое'}]),([r],[])]:
            with self.assertRaises(ValueError):select_groups(rows,observations)
        with self.assertRaises(ValueError):select_groups([r,r],[o])
        with self.assertRaises(ValueError):select_groups([r|{'kind':'correct_original'}],[o])

    def test_duplicate_pool_and_fabricated_weak_revision_fail_closed(self):
        r=row();o=observation(r);o['jointSearch']['alternatives'].append(copy.deepcopy(o['jointSearch']['alternatives'][0]))
        with self.assertRaisesRegex(ValueError,'RIGHT_CANDIDATE_POOL'):select_groups([r],[o])
        with self.assertRaisesRegex(ValueError,'RIGHT_RETENTION_LABEL'):
            select_groups([row(kind='insufficient_right_evidence')],[observation(row())])


if __name__ == '__main__':unittest.main()
