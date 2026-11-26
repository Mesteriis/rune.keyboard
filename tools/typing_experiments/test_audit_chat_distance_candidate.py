import unittest

import audit_chat_distance_candidate as screen


def pair(cohort='typo', distance=2, target='домой', chosen='другой'):
    row=dict(id='one',cohort=cohort,language='ru',prefix='иду',typed='дмои',expectedSpelling=target,edit_kind='vowel_oa')
    obs=dict(id='one',language='ru',prefix='иду',typed='дмои',status='COMPLETE',automaticAdmissionCandidate=chosen,
             autoEdit={'applied':' '+chosen+' ', 'correctionGeneration':{'alternatives':[{'text':chosen,'unitDistance':distance}]}})
    return row,obs


class DistanceScreenTest(unittest.TestCase):
    def test_counts_multiple_distance_and_unattributed_edits(self):
        row,obs=pair();result=screen.analyze([row],[obs])
        self.assertEqual(1,result['counts']['typo:distance_over_one:other'])
        row,obs=pair(target='другой');self.assertEqual(1,screen.analyze([row],[obs])['counts']['typo:distance_over_one:expected'])
        row,obs=pair();obs['automaticAdmissionCandidate']=None
        self.assertEqual(1,screen.analyze([row],[obs])['counts']['typo:unattributed'])

    def test_refuses_identity_length_and_candidate_mismatches(self):
        row,obs=pair();obs['id']='other'
        with self.assertRaises(ValueError):screen.analyze([row],[obs])
        row,obs=pair();obs['autoEdit']['applied']=' чужой '
        with self.assertRaises(ValueError):screen.analyze([row],[obs])
        row,obs=pair()
        with self.assertRaises(ValueError):screen.analyze([row],[])
        with self.assertRaises(ValueError):screen.analyze([row,row],[obs,obs])


if __name__=='__main__':unittest.main()
