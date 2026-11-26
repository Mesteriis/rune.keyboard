import json
from pathlib import Path
import subprocess
import sys
from temporary_test_build import temporary_build_directory
import unittest
from unittest import mock

import extra_epoch_evaluation_receipt as binding

ROOT=binding.HERE.parents[1]


class ExtraEpochEvaluationReceiptTest(unittest.TestCase):
    def setUp(self):
        self.temp=temporary_build_directory(ROOT);self.addCleanup(self.temp.cleanup)
        self.source=Path(self.temp.name);training=self.source/'training';training.mkdir()
        selected=training/'fixture.bin';selected.write_bytes(b'public model fixture')
        (training/'original.bin').write_bytes(selected.read_bytes())
        self.selection=dict(selectionFrozenBeforeTest=True,testAccess=False,selected='fixture',
            selectedPath=str(selected),selectedSha256=binding.sha(selected.read_bytes()),
            originalSha256=binding.sha(selected.read_bytes()),rankerSha256='a'*64)
        for name,key in [('plan.json','planSha256'),('metrics.json','metricsSha256'),
                ('dev-report.json','devReportSha256'),('dev-scores.json','devScoresSha256')]:
            path=training/name;path.write_text('{}');self.selection[key]=binding.sha(path.read_bytes())
        self.save()

    def save(self):(self.source/'training/selection.json').write_text(json.dumps(self.selection))

    def test_default_refuses_before_optional_libraries_and_input_reads_under_optimization(self):
        script=binding.HERE/'evaluate_extra_epochs.py'
        for flags in ([],['-O']):
            r=subprocess.run([sys.executable,*flags,str(script),'--source-root',str(self.source/'absent')],
                capture_output=True,text=True)
            self.assertNotEqual(0,r.returncode)
            self.assertIn('NEW_HOLDOUT_REGISTRY_COVERAGE_INCOMPLETE',r.stderr)
        self.assertFalse((self.source/'evaluation.json').exists())

    def test_dev_receipt_drift_is_rejected_before_model_or_corpus_access(self):
        (self.source/'training/metrics.json').write_text('{"changed":true}')
        with self.assertRaisesRegex(ValueError,'SELECTION_BINDING'):binding.freeze(self.source,True,ROOT)

    def test_frozen_selection_flags_are_typed(self):
        for key,value in [('selectionFrozenBeforeTest',1),('testAccess',0),('testAccess',True)]:
            with self.subTest(key=key,value=value):
                original=dict(self.selection);self.selection[key]=value;self.save()
                with self.assertRaisesRegex(ValueError,'FROZEN_DEV_SELECTION_REQUIRED'):binding.freeze(self.source,True,ROOT)
                self.selection=original

    def test_model_path_cannot_escape_training_root(self):
        self.selection['selectedPath']=str(self.source/'outside.bin');self.save()
        with self.assertRaisesRegex(ValueError,'EVALUATION_INPUT_PATH'):binding.freeze(self.source,True,ROOT)

    def test_passing_disclosed_metrics_cannot_grant_acceptance(self):
        receipt=dict(historicalReproduction=True,independentDataEvaluation=False,
            dataManifestSha256='a'*64,selectionSha256='b'*64,observationsSha256='c'*64)
        frozen=dict(receipt=receipt)
        with mock.patch.object(binding.shared,'verify'):
            result=binding.finish_report(frozen,{'models':{'fixture':1}},True)
        self.assertTrue(result['observedGatePassed']);self.assertFalse(result['accepted'])
        binding.shared.verify_report(result,frozen)
        result['accepted']=True
        with self.assertRaisesRegex(ValueError,'EVALUATION_REPORT_PAYLOAD'):binding.shared.verify_report(result,frozen)

    def test_impossible_dev_counts_or_nonfinite_losses_cannot_support_a_gate(self):
        selection=dict(selected='fixture',devTop1Before=1,devTop1After=2)
        report={'models':{'original':{'devCE':2.0},'fixture':{'devCE':1.0}}}
        binding.validate_dev_metrics(selection,report,3)
        for value in (True,-1,4,'2'):
            with self.assertRaisesRegex(ValueError,'EPOCH_DEV_COUNT'):
                binding.validate_dev_metrics(selection|{'devTop1After':value},report,3)
        for value in (float('nan'),float('inf'),-1,True):
            changed={'models':{'original':{'devCE':2.0},'fixture':{'devCE':value}}}
            with self.assertRaisesRegex(ValueError,'EPOCH_DEV_CROSS_ENTROPY'):
                binding.validate_dev_metrics(selection,changed,3)


if __name__=='__main__':unittest.main()
