import struct
import sys
from temporary_test_build import temporary_build_directory
import unittest
import json
from pathlib import Path
from unittest import mock
import numpy as np
import train_joint_correction as joint
import joint_calibration_receipt as binding
from prepare_joint_correction import partition


class JointTrainingTest(unittest.TestCase):
    def test_independent_training_refuses_until_source_attestation_exists(self):
        root=Path(joint.__file__).resolve().parents[2]
        with temporary_build_directory(root) as tmp:
            out=Path(tmp)/'result';context=Path(tmp)/'context';context.write_bytes(b'test-context')
            frozen=dict(partitions={'train':[],'calibration':[]},observations={'train':[],'calibration':[]},
                context=context,files={context:context.read_bytes()},manifest={'files':{'holdout.jsonl':'a'*64}},
                bindings={'train/replay/receipt':'b'*64,'calibration/replay/receipt':'c'*64},
                receipt=dict(historicalReproduction=False,corpusRole='registry-checked-corpus-proposal',
                    independentQualification=False,productionQualified=False,corpusManifestSha256='d'*64))
            args=type('Args',(),dict(corpus='unused',train_export='unused',calibration_export='unused',output=out))()
            with mock.patch.object(binding,'freeze_training',return_value=frozen):
                with self.assertRaisesRegex(ValueError,'TRAINING_SOURCE_ATTESTATION_REQUIRED'):
                    joint.train_independent(args,{'test':True})
            self.assertFalse(out.exists())

    def test_historical_control_flow_marks_output_and_refuses_input_drift(self):
        root=Path(joint.__file__).resolve().parents[2]
        ref=json.loads((root/'tools/typing_experiments/historical_provenance_sources/joint-neighbor-receipts/joint-original-policy.json').read_text())
        with temporary_build_directory(root) as tmp:
            parent=Path(tmp);corpus=parent/'corpus';corpus.mkdir()
            manifest={'files':{'holdout.jsonl':ref['holdoutSha256']}}
            dirs=[]
            for part,key in [('train','trainExportReceiptSha256'),('calibration','calibrationExportReceiptSha256')]:
                rows=corpus/f'{part}.jsonl';rows.write_text('{}\n')
                manifest['files'][f'{part}.jsonl']=joint.sha(rows)
                directory=parent/part;directory.mkdir();dirs.append(directory)
                observations=directory/'observations.jsonl';observations.write_text('{}\n')
                (directory/'receipt.json').write_text(json.dumps({'rows':joint.sha(rows),'observations':joint.sha(observations)}))
            (corpus/'manifest.json').write_text(json.dumps(manifest))
            original_sha=joint.sha
            def fake_sha(path):
                path=Path(path)
                if path==corpus/'manifest.json':return ref['corpusManifestSha256']
                if path==dirs[0]/'receipt.json':return ref['trainExportReceiptSha256']
                if path==dirs[1]/'receipt.json':return ref['calibrationExportReceiptSha256']
                return original_sha(path)
            def exercise(out,drift):
                def fit(_rows,path):
                    path.write_bytes(b'test-only-model')
                    if drift:(corpus/'train.jsonl').write_text('changed\n')
                argv=['trainer',str(corpus),str(dirs[0]),str(dirs[1]),str(out),'--historical-reproduction']
                with mock.patch.object(sys,'argv',argv), mock.patch.object(joint,'sha',side_effect=fake_sha), \
                     mock.patch.object(joint,'groups',return_value=[]), mock.patch.object(joint,'fit',side_effect=fit), \
                     mock.patch.object(joint,'score',return_value=[]), mock.patch.object(joint,'calibrate',return_value={'qualifiedCalibration':False}):
                    joint.main()
            out=parent/'valid';exercise(out,False)
            policy=json.loads((out/'frozen-policy.json').read_text())
            self.assertEqual('historical-disclosed-calibration',policy['stage'])
            self.assertFalse(policy['independentQualification']);self.assertFalse(policy['productionQualified'])
            with self.assertRaisesRegex(ValueError,'HISTORICAL_INPUT_DRIFT'):
                exercise(parent/'drift',True)
            self.assertFalse((parent/'drift/frozen-policy.json').exists())

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
