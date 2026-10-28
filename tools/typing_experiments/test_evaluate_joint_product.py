import unittest
from evaluate_joint_product import evaluate


class JointProductTest(unittest.TestCase):
    def data(self, baseline='зочу', after='хочу', control=False, undo=True):
        r=dict(id='a',typed='зочу',prefix='я',expectedSpelling='хочу',family='1',noAuto=control)
        def observation(word):return dict(id='a',typed='зочу',prefix='я',status='COMPLETE',beforeBoundary={'text':'я зочу'},
            afterBoundary={'text':'я '+word+' '},restoredBeforeBoundaryExactly=undo)
        return r,observation(baseline),observation(after)

    def test_actual_applied_word_and_undo_are_measured(self):
        r,a,b=self.data();v=evaluate([r],[a],[b])['short']
        self.assertEqual((1,1,0),(v['newCorrect'],v['correct'],v['undoFailures']))
        self.assertFalse(v['passed'])
        b['restoredBeforeBoundaryExactly']=False
        self.assertEqual(1,evaluate([r],[a],[b])['short']['undoFailures'])

    def test_correct_baseline_abstention_and_wrong_change_are_distinct(self):
        r,a,b=self.data('хочу','зочу');v=evaluate([r],[a],[b])['short']
        self.assertEqual((1,0),(v['baselineCorrectAbstained'],v['baselineCorrectToWrong']))
        b['afterBoundary']['text']='я зону '
        self.assertEqual(1,evaluate([r],[a],[b])['short']['baselineCorrectToWrong'])

    def test_controls_prefix_and_input_identity_fail_closed(self):
        r,a,b=self.data(control=True)
        self.assertEqual(1,evaluate([r],[a],[b])['short']['controlChanges'])
        b['afterBoundary']['text']='corrupt хочу '
        self.assertEqual(1,evaluate([r],[a],[b])['short']['prefixChanges'])
        b['typed']='other'
        with self.assertRaises(ValueError):evaluate([r],[a],[b])
