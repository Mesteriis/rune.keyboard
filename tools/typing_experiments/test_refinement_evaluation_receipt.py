import copy
import json
from pathlib import Path
import subprocess
import sys
from temporary_test_build import temporary_build_directory
import unittest
from unittest import mock

import refinement_evaluation_receipt as binding
import promote_refinement as promotion


class EvaluationReceiptTest(unittest.TestCase):
    def setUp(self):
        self.temp=temporary_build_directory(promotion.ROOT)
        self.addCleanup(self.temp.cleanup);self.source=Path(self.temp.name)
        for name in ('ranker','neural','data','verified-observations','candidates','app'):
            (self.source/name).mkdir()
        self.row=dict(id='public-fixture',language='ru',partition='test',typed='слво',expectedSpelling='слово',prefix='Контекст')
        files={}
        for part in ('train','dev','test'):
            for kind in ('rows','text'):
                name=f'{part}-{kind}.jsonl'
                raw=(json.dumps(self.row if kind=='rows' else {'text':'публичный пример'},ensure_ascii=False)+'\n').encode() if part=='test' else b''
                (self.source/'data'/name).write_bytes(raw);files[name]=binding.sha(raw)
        manifest=dict(containsPersonalMessages=False,files=files)
        (self.source/'data/manifest.json').write_text(json.dumps(manifest))
        for name,raw in [('ranker',b'RET2 synthetic fixture'),('neural',b'synthetic fixture')]:
            (self.source/name/'fixture.bin').write_bytes(raw)
        selection=dict(selectionFrozenBeforeTest=True,blendGain=1,ranker='fixture',neural='fixture',
            rankerSha256=binding.sha((self.source/'ranker/fixture.bin').read_bytes()),
            neuralSha256=binding.sha((self.source/'neural/fixture.bin').read_bytes()))
        (self.source/'selection.json').write_text(json.dumps(selection))
        observation=dict(row=self.row,observation=dict(generation=dict(original=self.row['typed'])))
        (self.source/'verified-observations/test.jsonl').write_text(json.dumps(observation)+'\n')
        file=self.source/'candidates/file';file.write_bytes(b'public export fixture')
        code=self.source/'app/ProductionCandidates.kt';code.write_bytes(b'public source fixture')
        export=dict(files={str(file):binding.sha(file.read_bytes())},sources={str(code):binding.sha(code.read_bytes())})
        export_path=self.source/'candidates/receipt.json';export_path.write_text(json.dumps(export))
        observed=dict(dataManifest=str(self.source/'data/manifest.json'),
            dataManifestSha256=binding.sha((self.source/'data/manifest.json').read_bytes()),
            partitions={'test':binding.sha((self.source/'verified-observations/test.jsonl').read_bytes())},
            exportReceipt=str(export_path),exportReceiptSha256=binding.sha(export_path.read_bytes()))
        (self.source/'verified-observations/manifest.json').write_text(json.dumps(observed))

    def freeze(self):return binding.freeze(self.source,True,promotion.ROOT,
        (promotion.ROOT/'tools/typing_experiments/baseline/ru-ranker.bin',promotion.ASSETS/'ru-context.bin'))

    def report(self,frozen):
        result={k:frozen['receipt'][k] for k in ('dataManifestSha256','selectionSha256','observationsSha256',
                   'historicalReproduction','independentDataEvaluation')}
        result.update(evaluationBinding=frozen['receipt'],fixtureOnly=True,models={'fixture':{'correctTop1':1}})
        result['reportPayloadSha256']=binding.seal(result);return result

    def make_legacy(self):
        root=self.source/'legacy';corpus=root/'tools/eval/smart-typing-0.3/qualification-v2/corpus'
        corpus.mkdir(parents=True)
        original=binding.HERE.parents[1]/'tools/eval/smart-typing-0.3/qualification-v2/corpus'
        for name in ('manifest.json','spelling-ru.jsonl'):(corpus/name).write_bytes((original/name).read_bytes())
        rows=[json.loads(line) for line in (corpus/'spelling-ru.jsonl').read_text().splitlines()][:2]
        export=root/'build/morphology-public-export-v3';export.mkdir(parents=True)
        (export/'rows.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
        (export/'observations.jsonl').write_text(''.join(json.dumps(dict(index=i,generation=dict(original=row['typed'])))+'\n' for i,row in enumerate(rows)))
        (export/'source-freeze.json').write_text('{}')
        files={str(p):binding.sha(p.read_bytes()) for p in export.iterdir()}
        sources={}
        for i in range(21):
            path=root/f'app/src/main/assets/smarttyping/lexicon/fixture-{i}.bin'
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'public source fixture')
            sources[str(path)]=binding.sha(path.read_bytes())
        (export/'receipt.json').write_text(json.dumps(dict(files=files,sources=sources)))
        return root,export

    def test_legacy_graph_is_bound_and_rehashed_bad_observations_are_rejected(self):
        root,export=self.make_legacy()
        frozen=binding.freeze(self.source,True,promotion.ROOT,legacy=root,legacy_row_limit=1)
        self.assertTrue(frozen['receipt']['legacyRegressionBound'])
        self.assertEqual(21,frozen['receipt']['legacyRegressionBinding']['checkedGeneratorSources'])
        self.assertEqual(2,len(frozen['legacyRows']))
        for path,raw in frozen['files'].items():
            if path.resolve().is_relative_to(root.resolve()):
                path.write_bytes(raw+b' changed')
                with self.assertRaisesRegex(ValueError,'EVALUATION_INPUT_DRIFT'):binding.verify(frozen)
                path.write_bytes(raw)
        path=export/'observations.jsonl';rows=[json.loads(line) for line in path.read_text().splitlines()]
        rows[0]['generation']['original']='wrong';path.write_text(''.join(json.dumps(row)+'\n' for row in rows))
        receipt=export/'receipt.json';meta=json.loads(receipt.read_text());meta['files'][str(path)]=binding.sha(path.read_bytes());receipt.write_text(json.dumps(meta))
        with self.assertRaisesRegex(ValueError,'EVALUATION_LEGACY_ROW_IDENTITY'):
            binding.freeze(self.source,True,promotion.ROOT,legacy=root)

    def test_legacy_corpus_cannot_be_relabelled_and_roots_cannot_escape(self):
        self.assertEqual(promotion.ROOT.resolve(),binding.legacy_root(promotion.ROOT,'.'))
        self.assertEqual((promotion.ROOT/'project').resolve(),binding.legacy_root(promotion.ROOT,'project'))
        root,_=self.make_legacy();path=root/'tools/eval/smart-typing-0.3/qualification-v2/corpus/manifest.json'
        path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'EVALUATION_LEGACY_CORPUS_MANIFEST'):
            binding.freeze(self.source,True,promotion.ROOT,legacy=root)
        for name in ('../outside','/outside','a//b','a/./b'):
            with self.assertRaisesRegex(ValueError,'EVALUATION_LEGACY_ROOT'):binding.legacy_root(promotion.ROOT,name)
        with self.assertRaisesRegex(ValueError,'EVALUATION_LEGACY_LIMIT'):
            binding.freeze(self.source,True,promotion.ROOT,legacy_row_limit=1)

    def test_historical_receipt_is_explicit_and_contains_no_local_root(self):
        frozen=self.freeze();binding.verify(frozen)
        self.assertTrue(frozen['receipt']['historicalReproduction'])
        self.assertFalse(frozen['receipt']['independentDataEvaluation'])
        self.assertEqual('rune-acceptance-registry-bindings-v1',frozen['receipt']['registryBindings']['schema'])
        self.assertEqual('rune-acceptance-registry-bindings-v2',binding.current_registries()['schema'])
        self.assertNotIn(str(self.source),json.dumps(frozen['receipt']))

    def test_independent_receipt_rejects_surface_binding_drift(self):
        frozen={'files':{}, 'boundaries':{}, 'receipt':{'historicalReproduction':False,
                'registryBindings':binding.current_registries(),'sourceBindings':{}}}
        binding.verify(frozen)
        frozen['receipt']['registryBindings']['englishSurfaceBindings']['ewt-surface-exclusions-v1.json']='0'*64
        with self.assertRaisesRegex(ValueError,'EVALUATION_REGISTRY_DRIFT'):
            binding.verify(frozen)

    def test_every_captured_input_and_registry_or_source_drift_is_rejected(self):
        frozen=self.freeze()
        for path,raw in frozen['files'].items():
            path.write_bytes(raw+b' changed')
            with self.assertRaisesRegex(ValueError,'EVALUATION_INPUT_DRIFT'):binding.verify(frozen)
            path.write_bytes(raw)
        with mock.patch.object(binding,'current_registries',return_value={}):
            with self.assertRaisesRegex(ValueError,'EVALUATION_REGISTRY_DRIFT'):binding.verify(frozen)
        key=next(iter(frozen['receipt']['sourceBindings']));frozen['receipt']['sourceBindings'][key]='a'*64
        with self.assertRaisesRegex(ValueError,'EVALUATION_SOURCE_DRIFT'):binding.verify(frozen)

    def test_metrics_mutation_or_resealed_false_independence_is_rejected(self):
        frozen=self.freeze();report=self.report(frozen);binding.verify_report(report,frozen)
        changed=copy.deepcopy(report);changed['models']['fixture']['correctTop1']=2
        with self.assertRaisesRegex(ValueError,'EVALUATION_REPORT_PAYLOAD'):binding.verify_report(changed,frozen)
        changed=copy.deepcopy(report);changed['independentDataEvaluation']=True
        changed['reportPayloadSha256']=binding.seal(changed)
        with self.assertRaisesRegex(ValueError,'EVALUATION_REPORT_ROLE'):binding.verify_report(changed,frozen)

    def test_observation_substitution_is_rejected_even_with_updated_outer_hash(self):
        path=self.source/'verified-observations/test.jsonl';observed=json.loads(path.read_text())
        observed['observation']['generation']['original']='other'
        path.write_text(json.dumps(observed)+'\n')
        meta=self.source/'verified-observations/manifest.json';data=json.loads(meta.read_text())
        data['partitions']['test']=binding.sha(path.read_bytes());meta.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'EVALUATION_ROW_IDENTITY'):self.freeze()

    def test_promotion_reconstructs_report_and_rechecks_all_evaluation_inputs(self):
        frozen=self.freeze();report=self.report(frozen)
        (self.source/'test-report.json').write_text(json.dumps(report))
        request=promotion.prepare_request(self.source,self.source/'review',True)
        promotion.verify_request(request)
        path=self.source/'verified-observations/test.jsonl';path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'EVALUATION_INPUT_DRIFT'):promotion.verify_request(request)
        self.assertFalse((self.source/'review').exists())

    def test_default_evaluation_refuses_before_optional_libraries_even_under_optimization(self):
        script=Path(binding.__file__).with_name('evaluate_refinement.py')
        for flags in ([],['-O']):
            result=subprocess.run([sys.executable,*flags,str(script),'--source-root',str(self.source/'absent')],
                capture_output=True,text=True)
            self.assertNotEqual(0,result.returncode)
            self.assertIn('NEW_HOLDOUT_REGISTRY_COVERAGE_INCOMPLETE',result.stderr)
        self.assertFalse((self.source/'test-report.json').exists())


if __name__=='__main__':unittest.main()
