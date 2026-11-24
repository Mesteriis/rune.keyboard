import json
import math
from pathlib import Path
import unittest

import ewt_english_ranker_experiment as subject


def candidate(word,rank=5,cost=1.0):
    return dict(text=word,language='en',editCost=cost,frequencyRank=rank,unitDistance=1,
                lengthDifference=0,repeatedCharacterEdits=0,repetitionBonus=0.0)


def example(identity,part,target,other):
    split={'train':'train','dev':'calibration','test':'holdout'}[part]
    row=dict(id=identity,language='en',split=split,prefix='we see',typed='x')
    label=dict(id=identity,kind='annotated',part=part,expected=target)
    alt=[candidate(other,2),candidate(target,10)]
    observed=dict(language='en',split=split,prefix='we see',typed='x',
        candidateView={'candidates':[{'role':'ORIGINAL','text':'x'},{'role':'ALTERNATIVE','text':target}]},
        fullTokenGeneration={'completion':'COMPLETE','alternatives':alt})
    return row,label,observed


class EwtEnglishRankerExperimentTest(unittest.TestCase):
    def test_exact_target_leakage_is_excluded_and_visible_counts_remain(self):
        examples=[example('a','train','cat','cut'),example('b','dev','cat','cut'),
                  example('c','dev','dog','dig'),example('d','test','dog','dig'),
                  example('e','test','pig','big')]
        groups,counts=subject.build_groups(*map(list,zip(*examples,strict=True)))
        self.assertEqual(1,counts['dev']['seenTargetExcluded'])
        self.assertEqual(1,counts['test']['seenTargetExcluded'])
        self.assertEqual(2,counts['dev']['allTargetVisible'])
        self.assertEqual([1,1,1],[len(groups[p]) for p in ('train','dev','test')])

    def test_pairwise_training_is_deterministic_and_orders_winner(self):
        good=(1.0,0.0,0.0,0.0,0.0,0.0);bad=(0.0,0.0,0.0,0.0,0.0,0.0)
        groups=[((bad,good),1)]
        a=subject.train(groups,25);self.assertEqual(a,subject.train(groups,25))
        self.assertTrue(all(math.isfinite(x) for x in a))
        self.assertEqual(0,subject.measure(groups,None)['top1'])
        self.assertEqual(1,subject.measure(groups,a)['top1'])

    def test_selection_uses_dev_only_and_ties_prefer_baseline(self):
        good=(1.0,0,0,0,0,0);bad=(0.0,0,0,0,0,0)
        groups={'train':[((bad,good),1)],'dev':[((good,bad),0)],'test':[((bad,good),1)]}
        first=subject.experiment(groups)
        self.assertEqual(0,first['chosenEpochs'])
        groups['test']=[((good,bad),0)]
        second=subject.experiment(groups)
        self.assertEqual(first['chosenEpochs'],second['chosenEpochs'])
        self.assertFalse(first['productBehaviorChanged'])
        self.assertFalse(first['independentQualification'])

    def test_invalid_features_and_missing_partitions_fail_closed(self):
        for value in (float('nan'),float('inf'),-1,True):
            item=candidate('cat');item['editCost']=value
            with self.subTest(value=str(value)),self.assertRaisesRegex(ValueError,'EWT_RANK_FEATURE'):
                subject.features(item)
        with self.assertRaisesRegex(ValueError,'EWT_RANK_EMPTY_PARTITION'):
            subject.experiment({'train':[],'dev':[],'test':[]})
        row,label,obs=example('a','train','cat','cut');obs['fullTokenGeneration']['completion']='unknown'
        with self.assertRaisesRegex(ValueError,'EWT_RANK_GENERATION'):
            subject.build_groups([row],[label],[obs])
        row,label,obs=example('a','train','cat','cut');label['part']='test'
        with self.assertRaisesRegex(ValueError,'EWT_RANK_ALIGNMENT'):
            subject.build_groups([row],[label],[obs])

    def test_retained_aggregate_binds_source_and_experiment(self):
        path=subject.ROOT/'docs/acceptance/2026-11-03-u11-ewt-pairwise-ranker.json'
        value=json.loads(path.read_bytes())
        self.assertEqual(subject.replay.model.sha(Path(subject.__file__).read_bytes()),value['analyzerSha256'])
        self.assertEqual(subject.replay.model.sha(subject.contexts.FIXTURE.read_bytes()),value['sourceFixtureSha256'])
        self.assertEqual(subject.replay.model.sha(subject.candidates.FIXTURE.read_bytes()),value['candidateFixtureSha256'])
        self.assertEqual(51,value['results']['trainGroups'])
        self.assertEqual(5,value['results']['testSelected']['groups'])
        self.assertFalse(value['results']['independentQualification'])


if __name__=='__main__':unittest.main()
