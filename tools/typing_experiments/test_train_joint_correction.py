import struct
import unittest
import numpy as np
import train_joint_correction as joint
from prepare_joint_correction import partition


class JointTrainingTest(unittest.TestCase):
    def record(self, index, **changes):
        value=dict(id=str(index),family=str(index),band='short',topScore=.9,margin=.8,
            candidate='хочу',original='зочу',expected='хочу',baseline='зочу',control=False)
        return dict(value,**changes)

    def test_zero_regret_calibration_is_separate_for_short_words(self):
        result=joint.calibrate([self.record(i) for i in range(60)],'short')
        self.assertTrue(result['qualifiedCalibration'])
        self.assertEqual(60,result['metrics']['newCorrect'])

    def test_more_confident_wrong_change_prevents_promotion(self):
        rows=[self.record(i) for i in range(60)]
        rows.append(self.record(99,topScore=1.,margin=.9,candidate='зону'))
        self.assertFalse(joint.calibrate(rows,'short')['qualifiedCalibration'])

    def test_original_veto_cannot_silently_revoke_a_correct_baseline(self):
        rows=[self.record(i) for i in range(60)]
        rows.append(self.record(99,topScore=1.,margin=.9,candidate='зочу',baseline='хочу'))
        self.assertFalse(joint.calibrate(rows,'short')['qualifiedCalibration'])

    def test_calibration_requires_distinct_families_and_minimum_coverage(self):
        self.assertFalse(joint.calibrate([self.record(i,family='same') for i in range(60)],'short')['qualifiedCalibration'])
        self.assertFalse(joint.calibrate([self.record(i) for i in range(49)],'short')['qualifiedCalibration'])

    def test_vector_tree_uses_exact_float32_border_semantics(self):
        blob=b'RET2'+struct.pack('<IIff',95,1,1.,.1)+struct.pack('<IIf',1,0,.5)+struct.pack('<ff',0.,.75)
        x=np.zeros((2,95),dtype=np.float32);x[:,0]=[.5,.50001]
        result=joint.tree_matrix(blob,x)
        self.assertAlmostEqual(.1,result[0],places=6);self.assertAlmostEqual(.85,result[1],places=6)

    def test_family_partition_is_stable(self):
        first=[partition(str(i)) for i in range(100)]
        self.assertEqual(first,[partition(str(i)) for i in range(100)])
        self.assertEqual({'train','calibration','holdout'},set(first))

    def test_group_identity_checks_actual_input_and_status(self):
        row=dict(id='a',typed='зочу',prefix='я',noAuto=False,expectedSpelling='хочу')
        observation=dict(id='a',typed='зочу',prefix='я',status='ERROR')
        with self.assertRaises(ValueError):joint.groups([row],[observation])
