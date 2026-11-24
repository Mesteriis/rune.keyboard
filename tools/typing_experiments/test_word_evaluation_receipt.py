import copy
import json
from pathlib import Path
import subprocess
import sys
from temporary_test_build import temporary_build_directory
import unittest
from unittest import mock

import word_evaluation_receipt as binding
import evaluate_word_ranking as evaluation

ROOT=binding.HERE.parents[1]


class WordEvaluationReceiptTest(unittest.TestCase):
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

    def test_default_refuses_before_optional_libraries_or_data_reads_even_optimized(self):
        for flags in ([],['-O']):
            r=subprocess.run([sys.executable,*flags,str(binding.HERE/'evaluate_word_ranking.py'),
                              '--source-root',str(self.source/'missing')],capture_output=True,text=True)
            self.assertNotEqual(0,r.returncode)
            self.assertIn('NEW_HOLDOUT_REGISTRY_COVERAGE_INCOMPLETE',r.stderr)
        self.assertFalse((self.source/'evaluation.json').exists())

    def test_selection_flags_hashes_and_model_containment(self):
        for key,value in [('testAccess',0),('testAccess',True),('selectionFrozenBeforeTest',1)]:
            original=dict(self.selection);self.selection[key]=value;self.save()
            with self.assertRaisesRegex(ValueError,'FROZEN_DEV_SELECTION_REQUIRED'):binding.freeze(self.source,True,ROOT)
            self.selection=original
        self.save();(self.source/'training/metrics.json').write_text('{"drift":true}')
        with self.assertRaisesRegex(ValueError,'SELECTION_BINDING'):binding.freeze(self.source,True,ROOT)
        (self.source/'training/metrics.json').write_text('{}')
        self.selection['selectedPath']=str(self.source/'outside.bin');self.save()
        with self.assertRaisesRegex(ValueError,'EVALUATION_INPUT_PATH'):binding.freeze(self.source,True,ROOT)

    def test_historical_limits_cannot_be_bool_or_zero(self):
        for limit in (True,0,-1,1.5):
            with self.assertRaisesRegex(ValueError,'WORD_REGRESSION_LIMIT'):binding.freeze(self.source,True,ROOT,regression_row_limit=limit)

    def test_controls_and_typed_error_counts_cannot_change_denominators(self):
        control=dict(cohort='correct',errorCount=0,noAuto=True,typed='слово',expectedSpelling='слово')
        typo=dict(cohort='typo',errorCount=2,noAuto=False,typed='слв',expectedSpelling='слово')
        binding.validate_rows([control,typo])
        for row in (control|{'errorCount':False},typo|{'errorCount':True}):
            with self.assertRaisesRegex(ValueError,'WORD_ERROR_COUNT'):binding.validate_rows([row])
        for row in (control|{'noAuto':1},control|{'expectedSpelling':'иное'}):
            with self.assertRaisesRegex(ValueError,'CORRECT_CONTROL_MUTATED'):binding.validate_rows([row])
        for row in (typo|{'errorCount':0},typo|{'errorCount':4},typo|{'noAuto':True}):
            with self.assertRaisesRegex(ValueError,'WORD_TYPO_COHORT'):binding.validate_rows([row])
        with self.assertRaisesRegex(ValueError,'WORD_EDIT_DISTANCE'):
            binding.validate_rows([typo|{'errorCount':1}])
        binding.validate_rows([typo|{'typed':'слоов','errorCount':1}])

    def test_disclosed_retrieval_rows_preserve_edit_distances(self):
        path=ROOT/'tools/typing_experiments/retrieval-history-v1/rows.jsonl'
        rows=[json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual(1800,len(rows))
        binding.validate_rows(rows)

    def test_dev_score_rows_denominators_counts_models_and_shapes(self):
        observed=[dict(row=dict(id='dev',cohort='typo',noAuto=False),
                       observation=dict(generation=dict(alternatives=[dict(text='слово')])))]
        groups={'newDev':observed,'oldDev':observed}
        summary=dict(typoRows=1,controls=0,expectedAvailable=1,combinedTop1=1,neuralTop1=1)
        models={n:dict(sha256=self.selection[k],newDev=summary.copy(),oldDev=summary.copy())
                for n,k in [('original','originalSha256'),('fixture','selectedSha256')]}
        report=dict(testAccess=False,planSha256=self.selection['planSha256'],models=models)
        scores={k:dict(rowIds=['dev'],models={'original':[[.1]],'fixture':[[.1]]}) for k in groups}
        binding.validate_dev(self.selection,report,scores,groups)
        for field,value,code in [('typoRows',True,'WORD_DEV_DENOMINATOR'),('controls',1,'WORD_DEV_DENOMINATOR'),
                                  ('combinedTop1',2,'WORD_DEV_COUNT'),('expectedAvailable',0,'WORD_DEV_COUNT')]:
            changed=copy.deepcopy(report);changed['models']['fixture']['newDev'][field]=value
            with self.assertRaisesRegex(ValueError,code):binding.validate_dev(self.selection,changed,scores,groups)
        for values,code in [([], 'WORD_DEV_SCORE_SHAPE'),([[float('nan')]],'WORD_DEV_SCORE_FINITE')]:
            changed=copy.deepcopy(scores);changed['newDev']['models']['fixture']=values
            with self.assertRaisesRegex(ValueError,code):binding.validate_dev(self.selection,report,changed,groups)
        changed=copy.deepcopy(scores);changed['oldDev']['rowIds']=['test']
        with self.assertRaisesRegex(ValueError,'WORD_DEV_SCORE_ROWS'):binding.validate_dev(self.selection,report,changed,groups)
        changed=copy.deepcopy(report);changed['models']['fixture']['sha256']='a'*64
        with self.assertRaisesRegex(ValueError,'WORD_DEV_MODEL_IDENTITY'):binding.validate_dev(self.selection,changed,scores,groups)

    def test_passing_disclosed_metrics_cannot_grant_acceptance(self):
        receipt=dict(historicalReproduction=True,independentDataEvaluation=False,
            dataManifestSha256='a'*64,selectionSha256='b'*64,observationsSha256='c'*64)
        frozen=dict(receipt=receipt)
        with mock.patch.object(binding.shared,'verify'):result=binding.finish_report(frozen,{},True)
        self.assertTrue(result['observedGatePassed']);self.assertFalse(result['accepted'])
        binding.shared.verify_report(result,frozen)
        result['accepted']=True
        with self.assertRaisesRegex(ValueError,'EVALUATION_REPORT_PAYLOAD'):binding.shared.verify_report(result,frozen)

    def test_bounded_capture_is_exactly_from_original_disclosed_word_test(self):
        old_path=sys.path[:]
        try:
            sys.path.insert(0,str(ROOT/'tools/ci'))
            import word_evaluation_smoke as smoke
            fixture=json.loads((ROOT/'tools/ci/fixtures/word-ranking-bounded-capture.json').read_text())
            smoke.validate_capture(fixture)
            for key in ('row','text','manifest'):
                changed=copy.deepcopy(fixture)
                if key=='row':changed['rows'][0]['typed']='unattributed'
                elif key=='text':changed['text']['text']='unattributed'
                else:changed['sourceManifestSha256']='a'*64
                with self.assertRaisesRegex(ValueError,'WORD_CAPTURE_ORIGIN'):smoke.validate_capture(changed)
        finally:sys.path[:]=old_path

    def test_single_hard_and_regression_gates_are_preserved(self):
        def result(before,after):return {'models':{'before':{'combinedCorrectTop1':before},'after':{'combinedCorrectTop1':after}}}
        improved=result(1,2);steady=result(1,1);lost=result(2,1)
        self.assertTrue(evaluation.accepts(improved,steady,improved,[steady]))
        for all_,single,hard,regression in [(steady,steady,improved,steady),(improved,lost,improved,steady),
                (improved,steady,steady,steady),(improved,steady,improved,lost)]:
            self.assertFalse(evaluation.accepts(all_,single,hard,[regression]))


if __name__=='__main__':unittest.main()
