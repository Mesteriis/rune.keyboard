import base64
import copy
import json
from pathlib import Path
import subprocess
import sys
from temporary_test_build import temporary_build_directory
import unittest

import joint_evaluation_receipt as binding
import replay_joint_correction as replay
from evaluate_joint_product import evaluate

ROOT=binding.ROOT

def write(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value)+'\n')
def length(text):return len(text.encode('utf-16-le'))//2

def observation(row,word):
    prefix=row['prefix']+' ' if row['prefix'] else '';text=prefix+row['typed'];after=prefix+word+' '
    def snapshot(value):return dict(text=value,caret=length(value),composingStart=-1,composingEnd=-1)
    return dict(index=0,id=row['id'],split=row['split'],language=row['language'],typed=row['typed'],prefix=row['prefix'],
        status='COMPLETE',inputExpected=text,inputChangedByTyping=False,beforeBoundary=snapshot(text),
        afterBoundary=snapshot(after),afterBackspace=snapshot(text),boundaryChangedBeyondInsertedSpace=after!=text+' ',
        restoredBeforeBoundaryExactly=True,autoEdit=None)


class JointReceiptTest(unittest.TestCase):
    def setUp(self):
        self.temp=temporary_build_directory(ROOT);self.addCleanup(self.temp.cleanup)
        self.project=Path(self.temp.name);self.base=self.project/'build/eval';self.base.mkdir(parents=True)
        self.row=dict(id='unit-source-label',split='holdout',language='ru',prefix='😀 я',typed='зочу',
                      expectedSpelling='хочу',family='unit-family',noAuto=False)
        self.left=observation(self.row,'зочу');self.right=observation(self.row,'хочу')
        self.rows=self.base/'rows.jsonl';write(self.rows,self.row)
        self.runner=self.project/'tools/typing_experiments/replay_joint_correction.py'
        self.runner.parent.mkdir(parents=True);self.runner.write_bytes((binding.HERE/'replay_joint_correction.py').read_bytes())
        self.assets=self.project/'app/src/main/assets/smarttyping/experiments';self.assets.mkdir(parents=True)
        (self.assets/'ru-joint-ranker.bin').write_bytes(b'synthetic unit model; never executed')
        (self.assets/'ru-ranking-context.bin').write_bytes(b'synthetic unit context; never executed')
        threshold=dict(minimumScore=.1,minimumMargin=.2)
        self.meta=dict(model={'sha256':binding.sha((self.assets/'ru-joint-ranker.bin').read_bytes())},
            short={'thresholds':threshold},long={'thresholds':{'acquisition':threshold,'retention':threshold}})
        write(self.assets/'joint-correction-provenance.json',self.meta)
        self.policy=dict(fixtureOnly=True,stage='frozen-before-independent-holdout',holdoutSha256=binding.sha(self.rows.read_bytes()),
            modelSha256=self.meta['model']['sha256'],contextSha256=binding.sha((self.assets/'ru-ranking-context.bin').read_bytes()),
            thresholds=dict(short=threshold,long=dict(acquisition=threshold,retention=threshold)))
        self.policy_path=self.base/'policy.json';write(self.policy_path,self.policy)
        self.source_names=[f'app/src/main/unit-source-{i}.kt' for i in range(21)]
        self.manifest=self.project/'tools/eval/smart-typing-0.3/pipeline/final_product_replay_sources.json'
        write(self.manifest,dict(schemaVersion=1,sources=self.source_names))
        self.source_names+=['app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/diagnostics/TypingDiagnostics.kt',
                            'tools/eval/smart-typing-0.3/pipeline/FinalProductSpellingReplay.kt']
        for name in self.source_names:
            p=self.project/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('synthetic unit source; no execution claimed')
        self.save_replays()

    def save_replay(self,role,observed,mode):
        directory=self.base/role;directory.mkdir(exist_ok=True)
        raw=dict(observed,id='joint-replay-00000000')
        write(directory/'controller-observations.jsonl',raw);write(directory/'observations.jsonl',observed)
        write(directory/'input-identities.jsonl',dict(index=0,id=raw['id'],sourceId=self.row['id']))
        enc=lambda v:base64.b64encode(v.encode()).decode()
        (directory/'inputs.tsv').write_text('\t'.join(['0',enc(raw['id']),self.row['split'],self.row['language'],enc(self.row['prefix']),enc(self.row['typed'])])+'\n')
        (directory/'compile.log').write_text('synthetic unit receipt; never a compiler execution')
        (directory/'final-product-spelling-replay.jar').write_bytes(b'synthetic unit receipt; not executable')
        paths=[self.runner,self.rows,self.manifest,*[self.project/n for n in self.source_names],*self.assets.iterdir()]
        receipt=dict(schemaVersion=2,fixtureOnly=True,status='COMPLETE',exitCode=0,mode=mode,opaqueControllerIds=True,
            inputFieldsSent=list(replay.INPUT_FIELDS),rowsSha256=binding.sha(self.rows.read_bytes()),
            observationsSha256=binding.sha((directory/'observations.jsonl').read_bytes()),runnerSha256=binding.sha(self.runner.read_bytes()),
            files={str(p.relative_to(self.project)):binding.sha(p.read_bytes()) for p in paths},
            sources={n:binding.sha((self.project/n).read_bytes()) for n in self.source_names},
            outputBindings={p.name:binding.sha(p.read_bytes()) for p in directory.iterdir() if p.name!='receipt.json'},
            jarSha256=binding.sha((directory/'final-product-spelling-replay.jar').read_bytes()))
        write(directory/'receipt.json',receipt)

    def save_replays(self):
        self.save_replay('baseline',self.left,'joint-primary-only');self.save_replay('product',self.right,'joint-production')
    def freeze(self,**kwargs):return binding.freeze(self.rows,self.base/'baseline/observations.jsonl',self.base/'product/observations.jsonl',
        self.policy_path,True,self.project,**kwargs)

    def test_both_cli_guards_run_before_data_or_scientific_imports_even_optimized(self):
        for name in ('evaluate_joint_product.py','evaluate_joint_followup.py'):
            for flags in ([],['-O']):
                result=subprocess.run([sys.executable,*flags,str(binding.HERE/name),*[x for key in
                    ('rows','baseline','product','policy','output') for x in ('--'+key,str(self.base/'absent'))]],capture_output=True,text=True)
                self.assertNotEqual(0,result.returncode);self.assertIn('NEW_HOLDOUT_REGISTRY_COVERAGE_INCOMPLETE',result.stderr)

    def test_every_bound_resource_source_and_replay_file_rejects_drift(self):
        frozen=self.freeze();self.assertTrue(frozen['editorIntegrity']['short']['passed'])
        for path,raw in frozen['files'].items():
            path.write_bytes(raw+b' drift')
            with self.assertRaisesRegex(ValueError,'EVALUATION_INPUT_DRIFT'):binding.shared.verify(frozen)
            path.write_bytes(raw)

    def test_old_receipts_or_incomplete_resources_cannot_masquerade_as_current(self):
        path=self.base/'product/receipt.json';receipt=json.loads(path.read_text());receipt['schemaVersion']=1;write(path,receipt)
        with self.assertRaisesRegex(ValueError,'BOUND_JOINT_REPLAY_REQUIRED'):self.freeze()
        self.save_replays();receipt=json.loads(path.read_text());receipt['files'].pop(str((self.assets/'ru-joint-ranker.bin').relative_to(self.project)));write(path,receipt)
        with self.assertRaisesRegex(ValueError,'JOINT_REPLAY_RESOURCE_SCOPE'):self.freeze()
        self.save_replays();receipt=json.loads(path.read_text());receipt['sources'].pop(self.source_names[0]);write(path,receipt)
        with self.assertRaisesRegex(ValueError,'JOINT_REPLAY_SOURCE_SCOPE'):self.freeze()

    def test_opaque_envelope_and_restored_observation_identity_are_checked(self):
        path=self.base/'product/inputs.tsv';path.write_text('unbound labels\n')
        receipt_path=path.parent/'receipt.json';receipt=json.loads(receipt_path.read_text());receipt['outputBindings'][path.name]=binding.sha(path.read_bytes());write(receipt_path,receipt)
        with self.assertRaisesRegex(ValueError,'JOINT_REPLAY_ENVELOPE'):self.freeze()
        self.save_replays();self.right['index']=True;self.save_replays()
        with self.assertRaisesRegex(ValueError,'JOINT_REPLAY_IDENTITY_MAP'):self.freeze()

    def test_forged_undo_boolean_is_rejected_and_real_undo_failure_is_counted(self):
        self.right['restoredBeforeBoundaryExactly']=False
        with self.assertRaisesRegex(ValueError,'EDITOR_FLAGS_DIVERGE'):binding.editor_metrics([self.row],[self.left],[self.right])
        self.right['afterBackspace']['text']='сломано';self.right['afterBackspace']['caret']=0
        metrics=binding.editor_metrics([self.row],[self.left],[self.right])['short']
        self.assertEqual(1,metrics['undoTextFailures']);self.assertFalse(metrics['passed'])

    def test_new_case_only_control_change_is_visible_and_existing_case_is_separate(self):
        row=dict(self.row,typed='слово',expectedSpelling='слово',noAuto=True)
        before=observation(row,'слово');after=observation(row,'Слово')
        self.assertEqual(0,evaluate([row],[before],[after])['long']['controlChanges'])
        metrics=binding.editor_metrics([row],[before],[after])['long']
        self.assertEqual(1,metrics['introducedControlChangesExact']);self.assertFalse(metrics['passed'])
        metrics=binding.editor_metrics([row],[after],[after])['long']
        self.assertEqual((1,1,0),(metrics['baselineControlChangesExact'],metrics['controlChangesExact'],metrics['introducedControlChangesExact']))
        self.assertTrue(metrics['passed'])

    def test_utf16_snapshot_positions_and_caret_undo_are_not_text_only(self):
        self.assertTrue(binding.editor_metrics([self.row],[self.left],[self.right])['short']['passed'])
        self.right['afterBackspace']['caret']-=1
        metric=binding.editor_metrics([self.row],[self.left],[self.right])['short']
        self.assertEqual(1,metric['undoCaretFailures']);self.assertFalse(metric['passed'])
        self.right['afterBoundary']['caret']=10000
        with self.assertRaisesRegex(ValueError,'EDITOR_SNAPSHOT'):binding.editor_metrics([self.row],[self.left],[self.right])

    def test_policy_model_threshold_and_short_chain_must_match_execution(self):
        self.policy['thresholds']['short']['minimumScore']=.9;write(self.policy_path,self.policy)
        with self.assertRaisesRegex(ValueError,'JOINT_POLICY_THRESHOLDS'):self.freeze()
        self.policy['thresholds']['short']['minimumScore']=.1;self.policy['modelSha256']='a'*64;write(self.policy_path,self.policy)
        with self.assertRaisesRegex(ValueError,'JOINT_POLICY_MODEL'):self.freeze()

    def test_explicit_config_thresholds_are_bound_to_the_model_and_policy(self):
        config=self.base/'config.tsv';model=self.assets/'ru-joint-ranker.bin'
        def save(values):
            config.write_text('\t'.join([str(model),self.policy['modelSha256'],*map(str,values)])+'\n')
            path=self.base/'product/receipt.json';receipt=json.loads(path.read_text())
            receipt.update(mode='joint-ready',configSha256=binding.sha(config.read_bytes()))
            receipt['files'][str(config.relative_to(self.project))]=binding.sha(config.read_bytes());write(path,receipt)
        save([.1,.2,.1,.2,.1,.2]);self.assertEqual([.1,.2]*3,self.freeze()['receipt']['executionThresholds'])
        save([.1,.2,.9,.2,.1,.2])
        with self.assertRaisesRegex(ValueError,'JOINT_POLICY_THRESHOLDS'):self.freeze()

    def test_followup_short_policy_chain_is_mandatory_and_hash_bound(self):
        short_path=self.base/'short-policy.json';write(short_path,self.policy)
        self.policy['shortPolicySha256']=binding.sha(short_path.read_bytes())
        long=self.policy['thresholds']['long'];self.policy['thresholds']=dict(acquisition=long['acquisition'],retention=long['retention'])
        write(self.policy_path,self.policy)
        with self.assertRaisesRegex(ValueError,'JOINT_SHORT_POLICY_REQUIRED'):self.freeze()
        frozen=self.freeze(short_policy_path=short_path);raw=short_path.read_bytes();short_path.write_bytes(raw+b' ')
        with self.assertRaisesRegex(ValueError,'EVALUATION_INPUT_DRIFT'):binding.shared.verify(frozen)
        with self.assertRaisesRegex(ValueError,'JOINT_SHORT_POLICY_IDENTITY'):self.freeze(short_policy_path=short_path)

    def test_passing_numbers_cannot_grant_disclosed_acceptance_or_skip_editor_gate(self):
        frozen=self.freeze();result=binding.finish_report(frozen,{},True)
        self.assertTrue(result['numericalGatePassed']);self.assertTrue(result['observedGatePassed']);self.assertFalse(result['passed'])
        binding.verify_report(result,frozen)
        altered=copy.deepcopy(result);altered['passed']=True
        with self.assertRaisesRegex(ValueError,'EVALUATION_REPORT_PAYLOAD'):binding.verify_report(altered,frozen)
        frozen['editorIntegrity']['short']['passed']=False
        result=binding.finish_report(frozen,{},True);self.assertFalse(result['observedGatePassed']);self.assertFalse(result['passed'])

    def test_corpus_manifest_must_describe_the_actual_holdout_not_another_coherent_file(self):
        directory=self.base/'corpus';directory.mkdir();holdout=directory/'holdout.jsonl';holdout.write_bytes(self.rows.read_bytes())
        path=directory/'manifest.json'
        def bind():
            write(path,dict(files={'holdout.jsonl':binding.sha(holdout.read_bytes())}))
            self.policy['corpusManifestSha256']=binding.sha(path.read_bytes());write(self.policy_path,self.policy)
        bind();self.freeze(corpus_manifest_path=path)
        write(holdout,dict(self.row,id='different-disclosed-row'));bind()
        with self.assertRaisesRegex(ValueError,'JOINT_CORPUS_ROWS_IDENTITY'):self.freeze(corpus_manifest_path=path)

    def test_controller_ids_are_opaque_and_only_host_side_restores_them(self):
        controller=replay.controller_records([self.row]);self.assertEqual('joint-replay-00000000',controller[0]['id'])
        self.assertEqual(set(replay.INPUT_FIELDS),set(controller[0]));self.assertNotIn('family',controller[0])
        raw=dict(self.right,id=controller[0]['id']);self.assertEqual(self.row['id'],replay.restore_identities([self.row],controller,[raw])[0]['id'])
        raw['typed']='other'
        with self.assertRaisesRegex(ValueError,'REPLAY_INPUT_IDENTITY'):replay.restore_identities([self.row],controller,[raw])
        with self.assertRaisesRegex(ValueError,'DUPLICATE_OR_EMPTY_ID'):replay.controller_records([self.row,self.row])


if __name__=='__main__':unittest.main()
