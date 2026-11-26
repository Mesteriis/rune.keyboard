import copy
import unittest

import register_wordrank_replay as subject


def sample():
    row=dict(id='one',articleId='123',language='ru',partition='test',prefix='иду ',typed='дми',expectedSpelling='домой')
    obs=dict(id='one',language='ru',prefix='иду ',typed='дми',status='COMPLETE',
             beforeBoundary={'text':'иду дми'},afterBoundary={'text':'иду домой '})
    return row,obs


class WordrankReplayDisclosureTest(unittest.TestCase):
    def test_records_both_source_and_observed_forms(self):
        row,obs=sample();result=subject.capture([row],[obs])
        self.assertEqual({('иду','дми'),('иду','домой')},{(r['prefix'],r['typed']) for r in result})
        control,lexical=subject.entries(result)
        self.assertEqual(2,len(control['keys']));self.assertEqual(2,len(control['surfaceKeys']))
        self.assertEqual(1,len(control['articleKeys']));self.assertEqual(2,len(lexical['keys']['context']))

    def test_rejects_unidentified_or_changed_prefix_and_partial_results(self):
        row,obs=sample()
        for mutate in ('id','boundary','prefix','duplicate','length'):
            r,o=copy.deepcopy(row),copy.deepcopy(obs)
            if mutate=='id':o['id']='other'
            if mutate=='boundary':o['afterBoundary']['text']='чужой домой '
            if mutate=='prefix':o['prefix']='другой'
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):
                subject.capture([r,r] if mutate=='duplicate' else [r],
                                [] if mutate=='length' else [o,o] if mutate=='duplicate' else [o])


if __name__=='__main__':unittest.main()
