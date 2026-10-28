import unittest
import calibrate_joint_source as policy


class JointArbitrationTest(unittest.TestCase):
    def record(self, **changes):
        r=dict(id='a',family='1',topScore=.8,margin=.6,candidate='хочу',original='зочу',expected='хочу',baseline='хочу',control=False)
        return dict(r,**changes)

    def test_low_confidence_abstention_is_separate_from_wrong_replacement(self):
        result=policy.full_metrics([self.record()],.9,.7)
        self.assertEqual(1,result['baselineCorrectAbstained'])
        self.assertEqual(0,result['baselineCorrectToWrong'])
        self.assertEqual(0,result['replacements'])

    def test_different_wrong_word_is_a_regression(self):
        result=policy.full_metrics([self.record(candidate='зону')],.5,.5)
        self.assertEqual(1,result['baselineCorrectToWrong'])
        self.assertEqual(1,result['wrong'])

    def test_original_veto_resolves_wrong_baseline_without_inventing_correctness(self):
        result=policy.full_metrics([self.record(candidate='зочу',baseline='зону')],.5,.5)
        self.assertEqual(1,result['wrongResolved'])
        self.assertEqual(0,result['correct'])

    def test_inadmissible_scored_word_does_not_gain_automatic_authority(self):
        record=self.record(scores=[0.,1.],candidate='зону')
        obs=dict(id='a',jointSearch={'alternatives':[{'text':'зону'}]},jointAdmission={'зону':False})
        result=policy.normalized([record],[obs])
        self.assertEqual('хочу',result[0]['candidate'])
        obs['jointSearch']['alternatives']=[]
        with self.assertRaises(ValueError):policy.normalized([record],[obs])
