import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

import joint_calibration_receipt as binding
import test_joint_evaluation_receipt as fixtures
observation=fixtures.observation
write=fixtures.write

ROOT=binding.ROOT


class CalibrationReceiptTest(unittest.TestCase):
    def setUp(self):
        self.case=fixtures.JointReceiptTest('test_every_bound_resource_source_and_replay_file_rejects_drift')
        self.case.setUp();self.addCleanup(self.case.doCleanups)
        case=self.case;self.project=case.project;self.base=case.base;self.corpus=self.base/'corpus';self.corpus.mkdir()
        self.row=dict(case.row,split='calibration');case.row=self.row
        case.rows=self.corpus/'calibration.jsonl';write(case.rows,self.row)
        self.observed=observation(self.row,self.row['typed'])
        self.observed.update(jointSearch={'alternatives':[{'text':'хочу'}]},jointAdmission={'хочу':True})
        case.save_replay('calibration',self.observed,'joint-export');self.export=self.base/'calibration'
        (self.corpus/'holdout.jsonl').write_bytes(b'not JSON: calibration must only hash these held labels')
        self.manifest=dict(containsPersonalMessages=False,historicalReproduction=True,
            files={p.name:binding.file_hash(p) for p in self.corpus.iterdir()})
        write(self.corpus/'manifest.json',self.manifest)
        self.ranker=self.base/'ranker';self.ranker.mkdir();(self.ranker/'joint-ranker.bin').write_bytes((case.assets/'ru-joint-ranker.bin').read_bytes())
        self.parent=dict(case.policy,corpusManifestSha256=binding.file_hash(self.corpus/'manifest.json'),
                         holdoutSha256=self.manifest['files']['holdout.jsonl'])
        write(self.ranker/'frozen-policy.json',self.parent)

    def freeze(self):return binding.freeze('source',self.ranker,self.corpus,self.export,self.ranker/'frozen-policy.json',True,self.project)

    def record(self):return dict(id=self.row['id'],original=self.row['typed'].casefold(),expected='хочу',
        family=self.row['family'],control=False,band='short',baseline=self.row['typed'].casefold(),
        scores=[.1,.8],topScore=.8,margin=.8-.1,candidate='хочу')

    def test_all_three_cli_guards_precede_optional_libraries_or_data_access_even_optimized(self):
        commands=[['calibrate_joint_source.py','absent','absent','absent'],
                  ['calibrate_joint_followup.py','--root','absent','--export','absent','--output','absent'],
                  ['calibrate_joint_rescue.py','--source-root','absent','--work-root','absent']]
        for command in commands:
            for flags in ([],['-O']):
                result=subprocess.run([sys.executable,*flags,str(binding.HERE/command[0]),*command[1:]],capture_output=True,text=True)
                self.assertNotEqual(0,result.returncode);self.assertIn('NEW_HOLDOUT_REGISTRY_COVERAGE_INCOMPLETE',result.stderr)

    def test_rescue_import_is_safe_without_arguments_or_optional_dependencies(self):
        code='import sys;sys.path.insert(0,'+repr(str(binding.HERE))+');import calibrate_joint_rescue'
        result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True)
        self.assertEqual(0,result.returncode,result.stderr)

    def test_calibration_freezes_all_inputs_without_parsing_held_labels_or_old_score_cache(self):
        cache=self.ranker/'calibration-scores.json';cache.write_bytes(b'poisoned stale cache; never consumed')
        frozen=self.freeze();self.assertNotIn(cache,frozen['files'])
        self.assertIn(self.corpus/'holdout.jsonl',frozen['files'])
        for path,raw in frozen['files'].items():
            path.write_bytes(raw+b' changed')
            with self.assertRaisesRegex(ValueError,'EVALUATION_INPUT_DRIFT'):binding.shared.verify(frozen)
            path.write_bytes(raw)

    def test_parent_model_context_and_corpus_cannot_drift_coherently(self):
        for key,code in [('modelSha256','CALIBRATION_MODEL_IDENTITY'),('contextSha256','CALIBRATION_CONTEXT_IDENTITY'),
                         ('corpusManifestSha256','CALIBRATION_PARENT_CORPUS')]:
            parent=self.parent.copy();parent[key]='a'*64;write(self.ranker/'frozen-policy.json',parent)
            with self.assertRaisesRegex(ValueError,code):self.freeze()
        write(self.ranker/'frozen-policy.json',self.parent)

    def test_wrong_replay_mode_and_legacy_receipts_fail_before_scores(self):
        path=self.export/'receipt.json';data=json.loads(path.read_text());data['mode']='joint-production';write(path,data)
        with self.assertRaisesRegex(ValueError,'CALIBRATION_REPLAY_MODE'):self.freeze()
        data['mode']='joint-export';data['schemaVersion']=1;write(path,data)
        with self.assertRaisesRegex(ValueError,'BOUND_JOINT_REPLAY_REQUIRED'):self.freeze()

    def test_score_vectors_must_match_row_pool_and_finite_summaries(self):
        record=self.record();binding.validate_scores([record],[self.row],[self.observed])
        for key,value,code in [('control',0,'CALIBRATION_SCORE_ROW'),('family','other','CALIBRATION_SCORE_ROW'),
                              ('scores',[.8],'CALIBRATION_SCORE_POOL'),('scores',[.1,float('nan')],'CALIBRATION_SCORE_FINITE'),
                              ('margin',.1,'CALIBRATION_SCORE_SUMMARY')]:
            with self.assertRaisesRegex(ValueError,code):binding.validate_scores([record|{key:value}],[self.row],[self.observed])
        with self.assertRaisesRegex(ValueError,'CALIBRATION_SCORE_IDS'):binding.validate_scores([record,record],[self.row],[self.observed])
        with self.assertRaisesRegex(ValueError,'CALIBRATION_SCORE_SUMMARY'):
            binding.validate_scores([record|dict(scores=[0.,1.],topScore=True,margin=1.)],[self.row],[self.observed])

    def test_passing_historical_numbers_remain_unqualified_and_policy_seal_detects_tampering(self):
        frozen=self.freeze();policy=dict(modelSha256=self.parent['modelSha256'],thresholds={'fixture':.1})
        binding.seal_policy(frozen,policy,True);binding.verify_policy(policy,frozen)
        self.assertEqual('historical-disclosed-calibration',policy['stage'])
        self.assertFalse(policy['independentQualification']);self.assertFalse(policy['productionQualified'])
        changed=copy.deepcopy(policy);changed['thresholds']['fixture']=.9
        with self.assertRaisesRegex(ValueError,'CALIBRATION_POLICY_PAYLOAD'):binding.verify_policy(changed,frozen)

    def test_pinned_rescue_caches_cannot_change_and_legacy_runtime_stays_unverified(self):
        source=self.base/'rescue-source';work=self.base/'rescue-work'
        rows=source/'followup-corpus/calibration.jsonl';write(rows,self.row)
        observed=source/'followup-calibration-export-v2/observations.jsonl';write(observed,self.observed)
        primary=source/'followup-policy-v2/calibration-scores.json';write(primary,[self.record()])
        write(observed.parent/'receipt.json',dict(fixtureOnly=True,originalRuntimeNotExecuted=True))
        model=work/'rescue-model/ranker.bin';model.parent.mkdir(parents=True);model.write_bytes(b'synthetic rescue model; never executed')
        scores=work/'rescue-model/calibration-scores.json';write(scores,[self.record()])
        training=work/'rescue-model/receipt.json';write(training,dict(fixtureOnly=True))
        holdout=work/'fresh-corpus/holdout.jsonl';holdout.parent.mkdir();holdout.write_bytes(b'not JSON: hash only')
        published=dict(modelSha256=binding.file_hash(model),secondaryCalibrationScoresSha256=binding.file_hash(scores),
            trainingReceiptSha256=binding.file_hash(training),holdoutSha256=binding.file_hash(holdout))
        assets=self.case.assets;write(assets/'ru-joint-rescue-policy.json',published)
        write(assets/'joint-rescue-provenance.json',dict(policy={'sha256':binding.file_hash(assets/'ru-joint-rescue-policy.json')},
            model={'sha256':binding.file_hash(model)}))
        morph=assets.parent/'lexicon/ru.morph';morph.parent.mkdir();morph.write_bytes(b'synthetic morphology receipt; never parsed')
        pins={str(p.relative_to(source)):binding.file_hash(p) for p in (rows,observed,primary)}
        frozen=binding.freeze_rescue(source,work,pins,binding.file_hash(model),True,self.project)
        self.assertFalse(frozen['receipt']['originalGeneratorRuntimeVerified']);self.assertFalse(frozen['receipt']['parentTrainingRequalified'])
        scores.write_bytes(scores.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'RESCUE_SECONDARY_IDENTITY'):
            binding.freeze_rescue(source,work,pins,binding.file_hash(model),True,self.project)

    def test_publish_refuses_drift_before_directory_creation_and_preserves_an_existing_result(self):
        frozen=self.freeze();policy={};binding.seal_policy(frozen,policy,False)
        path=self.ranker/'joint-ranker.bin';raw=path.read_bytes();path.write_bytes(raw+b'changed')
        out=self.base/'output'
        with self.assertRaisesRegex(ValueError,'EVALUATION_INPUT_DRIFT'):binding.publish(frozen,out,policy,[])
        self.assertFalse(out.exists());path.write_bytes(raw)
        binding.publish(frozen,out,policy,[]);saved=(out/'frozen-policy.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'FRESH_CALIBRATION_OUTPUT'):binding.publish(frozen,out,policy,[])
        self.assertEqual(saved,(out/'frozen-policy.json').read_bytes())

    def test_training_freeze_binds_replays_and_rejects_partition_and_input_drift(self):
        case=self.case; bindings=binding.shared.current_registries(); snapshot={'registryBindings':bindings}
        self.row.update(article='101',contextHash='a'*64,sourceSegmentHash='b'*64,families=['кот'])
        case.row=self.row;case.rows=self.corpus/'calibration.jsonl';write(case.rows,self.row)
        observed=observation(self.row,self.row['typed'])
        case.save_replay('calibration',observed,'joint-export')
        train=dict(self.row,id='train-row',split='train',prefix='другое',article='102',contextHash='c'*64,
                   sourceSegmentHash='d'*64,families=['дом'],family='other-family')
        case.row=train;case.rows=self.corpus/'train.jsonl';write(case.rows,train)
        case.save_replay('train',observation(train,train['typed']),'joint-export')
        self.manifest.update(historicalReproduction=False,registryBindings=bindings)
        self.manifest['files']={p.name:binding.file_hash(p) for p in self.corpus.iterdir() if p.name!='manifest.json'}
        write(self.corpus/'manifest.json',self.manifest)
        role=dict(scope='registry-checked-corpus-proposal',registryBindings=bindings)
        def freeze():
            with mock.patch.object(binding.guard,'finish',return_value=role):
                return binding.freeze_training(self.corpus,self.base/'train',self.base/'calibration',snapshot,self.project)
        frozen=freeze()
        self.assertFalse(frozen['receipt']['independentQualification'])
        self.assertIn(self.corpus/'holdout.jsonl',frozen['files'])
        original=self.manifest['registryBindings']
        self.manifest['registryBindings']={k:v for k,v in original.items() if k!='englishSurfaceBindings'}
        self.manifest['registryBindings']['schema']='rune-acceptance-registry-bindings-v1'
        write(self.corpus/'manifest.json',self.manifest)
        with self.assertRaisesRegex(ValueError,'TRAINING_REGISTRY_BINDING'):freeze()
        self.manifest['registryBindings']=original
        write(self.corpus/'manifest.json',self.manifest)
        path=self.base/'train/observations.jsonl';raw=path.read_bytes();path.write_bytes(raw+b' ')
        with self.assertRaisesRegex(ValueError,'EVALUATION_INPUT_DRIFT'):binding.shared.verify(frozen)
        path.write_bytes(raw)
        with mock.patch.object(binding,'keys_for',return_value={'same'}):
            with self.assertRaisesRegex(ValueError,'TRAINING_PARTITION_OVERLAP'):freeze()


if __name__=='__main__':unittest.main()
