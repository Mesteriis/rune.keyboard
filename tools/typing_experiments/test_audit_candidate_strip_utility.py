import unittest
from audit_candidate_strip_utility import measure


def fixture():
    row=dict(id='example',language='ru',prefix='нам',typed='готвы',split='holdout',cohort='typo',
             candidates=['готовы'],expectedCandidate=0,ambiguous=False)
    obs=dict(id='replay-00000000',language='ru',prefix='нам',typed='готвы',split='holdout',status='COMPLETE',
             candidateView={'candidates':[{'role':'CORRECTION','text':'готово'}]},
             actualOriginal='готвы',
             actualRequestGeneration={'alternatives':[{'text':'готово'}]},
             manualSearchGeneration={'alternatives':[{'text':'готово'},{'text':'готовы'}]})
    return row,obs,dict(index=0,id=obs['id'],sourceId=row['id'])


class StripUtilityTest(unittest.TestCase):
    def test_manual_pool_is_only_an_upper_bound(self):
        row,obs,identity=fixture();result=measure([row],[obs],[identity])['language']['ru']
        self.assertEqual(1,result['typoRows']);self.assertEqual(1,result['manualOnlyPoolUpperBound'])
        self.assertEqual(1,result['hiddenExpandedPoolUpperBound']);self.assertNotIn('targetVisible',result)
        obs['candidateView']['candidates'].append({'role':'CORRECTION','text':'ГОТОВЫ'})
        result=measure([row],[obs],[identity])['language']['ru']
        self.assertEqual(1,result['targetVisible']);self.assertNotIn('manualOnlyPoolUpperBound',result)

    def test_foreign_missing_and_invalid_observations_are_rejected(self):
        row,obs,identity=fixture()
        for args in (([row],[],[identity]),([row],[obs],[identity|{'sourceId':'foreign'}]),
                     ([row],[obs|{'status':'ERROR'}],[identity]),([row],[obs|{'actualOriginal':'foreign'}],[identity]),
                     ([row|{'expectedCandidate':2}],[obs],[identity])):
            with self.assertRaises(ValueError):measure(*args)


if __name__=='__main__':unittest.main()
