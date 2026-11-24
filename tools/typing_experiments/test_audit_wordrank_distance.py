import copy
import unittest
import audit_wordrank_distance as subject


def fixture():
    row=dict(id='one',language='ru',partition='test',errorCount=2,cohort='typo',
             prefix='иду ',typed='дми',expectedSpelling='домой')
    obs=dict(id='one',language='ru',prefix='иду ',typed='дми',status='COMPLETE',
             inputExpected='иду  дми',inputChangedByTyping=True,
             beforeBoundary={'text':'иду дми'},afterBoundary={'text':'иду домой '},
             restoredBeforeBoundaryExactly=True,automaticAdmissionCandidate='домой',
             autoEdit={'applied':' домой ','correctionGeneration':{'alternatives':[{'text':'домой','unitDistance':2}]}})
    return row,obs


class WordrankDistanceTest(unittest.TestCase):
    def test_counts_expected_multi_edit_and_changed_input_separately(self):
        row,obs=fixture();counts=subject.analyze([row],[obs])
        self.assertEqual(1,counts['operations_2:input_changed_by_typing'])
        self.assertEqual(1,counts['operations_2:distance_over_one_expected'])

    def test_wrong_prefix_input_undo_and_candidate_are_refused(self):
        row,obs=fixture()
        changes=(('prefix','other'),('inputChangedByTyping',False),('restoredBeforeBoundaryExactly',False))
        for key,value in changes:
            changed=copy.deepcopy(obs);changed[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):subject.analyze([row],[changed])
        changed=copy.deepcopy(obs);changed['autoEdit']['applied']=' другое '
        with self.assertRaises(ValueError):subject.analyze([row],[changed])
        with self.assertRaises(ValueError):subject.analyze([row,row],[obs,obs])

    def test_unattributed_is_not_counted_as_distance(self):
        row,obs=fixture();obs['automaticAdmissionCandidate']=None
        counts=subject.analyze([row],[obs])
        self.assertEqual(1,counts['operations_2:unattributed'])
        self.assertNotIn('operations_2:distance_over_one_expected',counts)


if __name__=='__main__':unittest.main()
