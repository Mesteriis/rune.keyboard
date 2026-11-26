import copy
import unittest
import compare_packed_wordrank as compare


def sample():
    row=dict(id='one',language='ru',partition='test',cohort='typo',errorCount=2,articleId='123',prefix='я',typed='дми',expectedSpelling='домой')
    obs=dict(id='one',language='ru',prefix='я',typed='дми',status='COMPLETE',beforeBoundary={'text':'я дми'},afterBoundary={'text':'я домой '})
    candidate=copy.deepcopy(obs);candidate['id']='joint-replay-00000000';candidate['afterBoundary']['text']='я дми '
    return row,obs,candidate


class ComparePackedWordrankTest(unittest.TestCase):
    def test_counts_lost_synthetic_target_and_records_output(self):
        row,old,new=sample();metrics,values=compare.compare([row],[old],[new])
        self.assertEqual(1,metrics['operations_2:lost_match']);self.assertEqual('дми',values[0]['typed'])

    def test_input_divergence_and_malformed_observations(self):
        row,old,new=sample();new['beforeBoundary']['text']='иной дми'
        with self.assertRaisesRegex(ValueError,'PACKED_WORDRANK_INPUT_DIVERGED'):compare.compare([row],[old],[new])
        row,old,new=sample();new['id']='wrong'
        with self.assertRaises(ValueError):compare.compare([row],[old],[new])
        row,old,new=sample();new['afterBoundary']['text']='иной домой '
        with self.assertRaises(ValueError):compare.compare([row],[old],[new])
        with self.assertRaises(ValueError):compare.compare([row],[],[new])


if __name__=='__main__':unittest.main()
