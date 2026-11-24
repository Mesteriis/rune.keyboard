import json
from pathlib import Path
import subprocess
import sys
import struct
from temporary_test_build import temporary_build_directory
import unittest

import promote_refinement as promotion


class PromotionTest(unittest.TestCase):
    def test_tree_validation_rejects_runtime_incompatible_or_nonfinite_payloads(self):
        raw=(promotion.ASSETS/'ru-ranker.bin').read_bytes()
        promotion.validate_tree(raw,95)
        mutants=[raw[:-1],raw+b'X',b'RET2',raw+b'X'*65536]
        for offset,fmt,value in [(4,'I',96),(8,'I',129),(12,'f',float('nan')),
                                 (20,'I',7),(24,'I',95),(28,'f',float('inf'))]:
            changed=bytearray(raw);struct.pack_into('<'+fmt,changed,offset,value);mutants.append(changed)
        for mutant in mutants:
            with self.assertRaisesRegex(ValueError,'PROMOTION_TREE_'):promotion.validate_tree(mutant,95)

    def setUp(self):
        self.temp=temporary_build_directory(promotion.ROOT)
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'input';self.output=self.root/'review'
        for name in ('ranker','neural','data'):(self.source/name).mkdir(parents=True,exist_ok=True)
        for key,blob in [('ranker',b'RET2 synthetic fixture'),('neural',b'synthetic network fixture')]:
            (self.source/key/'fixture.bin').write_bytes(blob)
        self.selection=dict(ranker='fixture',neural='fixture',blendGain=1,selectionFrozenBeforeTest=True,
            rankerSha256=promotion.sha((self.source/'ranker/fixture.bin').read_bytes()),
            neuralSha256=promotion.sha((self.source/'neural/fixture.bin').read_bytes()))
        self.save()
        (self.source/'data/manifest.json').write_text(json.dumps(dict(containsPersonalMessages=False)))

    def save(self):
        raw=json.dumps(self.selection).encode();(self.source/'selection.json').write_bytes(raw)
        (self.source/'test-report.json').write_text(json.dumps(dict(selectionSha256=promotion.sha(raw))))

    def request(self):return promotion.prepare_request(self.source,self.output,True)

    def test_default_refuses_even_with_optimized_python_and_preserves_packaged_files(self):
        before={p:p.read_bytes() for p in promotion.ASSETS.iterdir() if p.is_file()}
        for flags in ([],['-O']):
            result=subprocess.run([sys.executable,*flags,str(Path(promotion.__file__)),
                '--source-root',str(self.root/'absent')],capture_output=True,text=True)
            self.assertNotEqual(0,result.returncode)
            self.assertIn('NEW_HOLDOUT_REGISTRY_COVERAGE_INCOMPLETE',result.stderr)
        self.assertEqual(before,{p:p.read_bytes() for p in before})

    def test_historical_review_requires_fresh_build_destination_and_creates_nothing_during_validation(self):
        request=self.request();self.assertTrue(request['historicalReproduction'])
        self.assertFalse(self.output.exists())
        with self.assertRaisesRegex(ValueError,'HISTORICAL_REVIEW_OUTPUT_REQUIRED'):
            promotion.prepare_request(self.source,None,True)
        for path in (self.source,promotion.ASSETS,self.root.parent.parent/'outside'):
            with self.assertRaisesRegex(ValueError,'FRESH_REVIEW_OUTPUT_REQUIRED'):
                promotion.prepare_request(self.source,path,True)

    def test_model_names_hashes_and_boolean_gain_cannot_bypass_receipt_checks(self):
        for key,value,error in [('ranker','../../escape','PROMOTION_MODEL_NAME'),
                ('rankerSha256','a'*64,'PROMOTION_MODEL_IDENTITY'),('blendGain',True,'PROMOTION_FROZEN_SELECTION')]:
            with self.subTest(key=key):
                original=dict(self.selection);self.selection[key]=value;self.save()
                with self.assertRaisesRegex(ValueError,error):self.request()
                self.selection=original
        self.assertFalse(self.output.exists())

    def test_mismatched_evaluation_is_rejected_under_optimized_python_before_optional_libraries(self):
        (self.source/'test-report.json').write_text(json.dumps(dict(selectionSha256='a'*64)))
        result=subprocess.run([sys.executable,'-O',str(Path(promotion.__file__)),
            '--source-root',str(self.source),'--historical-reproduction','--output',str(self.output)],
            capture_output=True,text=True)
        self.assertNotEqual(0,result.returncode)
        self.assertIn('PROMOTION_SELECTION_BINDING',result.stderr);self.assertFalse(self.output.exists())

    def test_all_bound_inputs_are_rechecked_before_any_write(self):
        request=self.request()
        for name in request['inputs']:
            path=self.source/name;raw=path.read_bytes();path.write_bytes(raw+b' changed')
            with self.assertRaisesRegex(ValueError,'PROMOTION_INPUT_DRIFT'):promotion.verify_request(request)
            path.write_bytes(raw)
        promotion.verify_request(request);self.assertFalse(self.output.exists())


if __name__=='__main__':unittest.main()
