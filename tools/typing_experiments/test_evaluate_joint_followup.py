import unittest
from evaluate_joint_followup import acquisition

class JointAcquisitionTest(unittest.TestCase):
    def test_correct_retention_cannot_mask_new_wrong_replacements(self):
        rows=[];baseline=[];product=[]
        for i in range(1001):
            rows.append(dict(typed='сдово',expectedSpelling='слово',noAuto=False))
            baseline.append(dict(afterBoundary={'text':'слово ' if i else 'сдово '}))
            product.append(dict(afterBoundary={'text':'слово ' if i else 'снова '}))
        result=acquisition(rows,baseline,product)
        self.assertEqual((0,1,0.),(result['correct'],result['wrong'],result['precision']))
        self.assertFalse(result['passed'])
    def test_no_acquisitions_are_not_a_precision_pass(self):
        self.assertIsNone(acquisition([],[],[])['precision'])
        self.assertFalse(acquisition([],[],[])['passed'])
