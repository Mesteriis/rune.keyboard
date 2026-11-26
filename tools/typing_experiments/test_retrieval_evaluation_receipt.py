import copy
import json
from pathlib import Path
import subprocess
import sys
from temporary_test_build import temporary_build_directory
import unittest

import retrieval_evaluation_receipt as binding

ROOT=binding.HERE.parents[1]


class RetrievalReceiptTest(unittest.TestCase):
    def setUp(self):
        self.temp=temporary_build_directory(ROOT);self.addCleanup(self.temp.cleanup)
        self.project=Path(self.temp.name);self.source=self.project/'build/export';self.source.mkdir(parents=True)
        assets=self.project/'app/src/main/assets/smarttyping/experiments';assets.mkdir(parents=True)
        for name in ('ru-ranker.bin','ru-ranking-context.bin'):(assets/name).write_bytes(b'synthetic receipt fixture')
        self.row=dict(id='unit',language='ru',split='holdout',partition='test',articleId='1',prefix='контекст',
            typed='слво',expectedSpelling='слово',cohort='typo',noAuto=False,errorCount=1)
        generation=dict(original='слво',alternatives=[],completion='COMPLETE',inspectedStates=1,verifiedTerminals=0)
        self.observation=dict(index=0,generation=generation,manual=None,baseline=None,generationMs=1.,manualMs=0.)
        code=self.project/'source.kt';code.write_text('public synthetic source fixture')
        self.sources={str(code):binding.sha(code.read_bytes())}
        self.save()

    def save(self):
        (self.source/'rows.jsonl').write_text(json.dumps(self.row)+'\n')
        (self.source/'observations.jsonl').write_text(json.dumps(self.observation)+'\n')
        (self.source/'inputs.tsv').write_text('public synthetic envelope')
        (self.source/'source-freeze.json').write_text(json.dumps(self.sources))
        self.receipt=dict(scope='host-production-manual-retrieval',sources=self.sources,
            files={str(p):binding.sha(p.read_bytes()) for p in self.source.iterdir() if p.name!='receipt.json'})
        self.write_receipt()

    def write_receipt(self):(self.source/'receipt.json').write_text(json.dumps(self.receipt))
    def freeze(self,**kwargs):return binding.freeze(self.source,True,self.project,**kwargs)

    def test_default_refuses_before_optional_scoring_or_export_access_even_optimized(self):
        for flags in ([],['-O']):
            result=subprocess.run([sys.executable,*flags,str(binding.HERE/'evaluate_retrieval.py'),
                '--export',str(self.source/'absent'),'--output',str(self.source/'report.json')],capture_output=True,text=True)
            self.assertNotEqual(0,result.returncode)
            self.assertIn('NEW_HOLDOUT_REGISTRY_COVERAGE_INCOMPLETE',result.stderr)
        self.assertFalse((self.source/'report.json').exists())

    def test_export_sources_files_models_and_code_are_captured_and_drift_refused(self):
        frozen=self.freeze();self.assertEqual('historical-disclosed-regression',frozen['receipt']['corpusRole'])
        for path,raw in frozen['files'].items():
            path.write_bytes(raw+b' changed')
            with self.assertRaisesRegex(ValueError,'EVALUATION_INPUT_DRIFT'):binding.shared.verify(frozen)
            path.write_bytes(raw)
        for name in ('evaluate_retrieval.py','export_retrieval.py','rank_refinement.py','neural_refinement.py',
                     'prepare_word_ranking.py'):
            self.assertIn('tools/typing_experiments/'+name,frozen['receipt']['sourceBindings'])

    def test_detached_or_changed_export_members_fail(self):
        path=self.source/'inputs.tsv';self.receipt['files'].pop(str(path));self.write_receipt()
        with self.assertRaisesRegex(ValueError,'CONSUMED_FILE_BINDING'):self.freeze()
        self.save();(self.source/'observations.jsonl').write_text('{}\n')
        with self.assertRaisesRegex(ValueError,'BOUND_FILE_CHANGED'):self.freeze()
        self.save();self.receipt['sources']={str(self.project/'source.kt'):'a'*64};self.write_receipt()
        with self.assertRaisesRegex(ValueError,'RETRIEVAL_SOURCE_FREEZE'):self.freeze()

    def test_manual_identity_budget_and_latency_are_not_just_hashes(self):
        for field,value,code in [('original','иное','RETRIEVAL_ORIGINAL'),('inspectedStates',True,'SEARCH_BUDGET'),
                                  ('verifiedTerminals',65,'SEARCH_BUDGET')]:
            self.observation['manual']=copy.deepcopy(self.observation['generation'])
            self.observation['manual'][field]=value;self.save()
            with self.assertRaisesRegex(ValueError,code):self.freeze()
        self.observation['manual']=None
        for value in (True,-1,float('nan'),float('inf')):
            self.observation['manualMs']=value;self.save()
            with self.assertRaisesRegex(ValueError,'RETRIEVAL_LATENCY'):self.freeze()

    def test_cohort_boolean_or_control_relabelling_cannot_change_denominators(self):
        for changes,code in [({'errorCount':True},'WORD_ERROR_COUNT'),({'errorCount':0},'WORD_TYPO_COHORT'),
                            ({'errorCount':2},'WORD_EDIT_DISTANCE'),
                            ({'cohort':'correct','noAuto':True,'errorCount':0},'CORRECT_CONTROL_MUTATED')]:
            row=self.row.copy();self.row.update(changes);self.save()
            with self.assertRaisesRegex(ValueError,code):self.freeze()
            self.row=row

    def make_fresh(self):
        data=self.project/'build/data';data.mkdir();path=data/'test-rows.jsonl';path.write_bytes((self.source/'rows.jsonl').read_bytes())
        lock=ROOT/'tools/model/rune-text-0.2/source-lock.json'
        target=self.project/'tools/model/rune-text-0.2/source-lock.json';target.parent.mkdir(parents=True);target.write_bytes(lock.read_bytes())
        manifest=dict(containsPersonalMessages=False,sourceSha256=json.loads(lock.read_text())['wikipediaContext']['files']['ru-0007.parquet']['sha256'],
            articles=['1'],files={'test-rows.jsonl':binding.sha(path.read_bytes())})
        manifest_path=data/'manifest.json';manifest_path.write_text(json.dumps(manifest))
        selection_path=data/'selection.json';selection=dict(frozenBeforeFreshEvaluation=True,
            freshManifestSha256=binding.sha(manifest_path.read_bytes()),files={str(self.project/'source.kt'):self.sources[str(self.project/'source.kt')]})
        selection_path.write_text(json.dumps(selection));return manifest_path,selection_path

    def test_declared_fresh_manifest_and_selection_are_bound_but_stay_disclosed(self):
        manifest,selection=self.make_fresh();frozen=self.freeze(manifest_path=manifest,selection_path=selection)
        self.assertEqual(binding.sha(selection.read_bytes()),frozen['receipt']['selectionSha256'])
        self.assertFalse(frozen['receipt']['independentQualification'])
        changed=json.loads(selection.read_text());changed['frozenBeforeFreshEvaluation']=1;selection.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError,'FROZEN_SELECTION_REQUIRED'):self.freeze(manifest_path=manifest,selection_path=selection)
        with self.assertRaisesRegex(ValueError,'FRESH_BINDINGS_REQUIRED'):self.freeze(manifest_path=manifest)

    def test_report_role_and_payload_cannot_be_tampered(self):
        frozen=self.freeze();report=dict(modelHashes=frozen['receipt']['modelHashes'],metric=1)
        binding.finish_report(frozen,report);binding.verify_report(report,frozen)
        for key in ('metric','independentQualification','productionQualified'):
            altered=copy.deepcopy(report);altered[key]=2 if key=='metric' else True
            with self.assertRaisesRegex(ValueError,'EVALUATION_REPORT_'):binding.verify_report(altered,frozen)


if __name__=='__main__':unittest.main()
