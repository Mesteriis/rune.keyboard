"""Public synthetic contracts; never load real corpus rows or model scores."""
import copy
import importlib
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest import mock


def engine():
    return {'id':'fixture','language':'en','split':'holdout','prefix':'ordinary left',
            'variants':[{'id':i,'boundary':b,'continuation':b+('Word' if i>=4 else 'word')}
                        for i,b in enumerate([' ', ', ', ': ', '; ', '. ', '? ', '! '])]}


def request():
    return {'prefix':'ordinary left','candidateIds':list(range(7)),
            'continuations':[' word',', word',': word','; word','. Word','? Word','! Word']}


def response():
    return {'id':'fixture','durationMillis':12,'scores':[
        {'id':i,'sumLogProbability':-1.0 if i==1 else -10.0,'scoredTokenCount':1} for i in range(7)]}


def metric_row(identifier, chosen=0, observed=' ', status='NO_CONTEXTUAL_REQUEST', tap=False):
    return {'id':identifier,'language':'en','split':'holdout','observedBoundary':observed,
            'routing':'CONTEXTUAL_REQUEST' if status=='EXACT_CACHE_OK' else 'PROTECTED',
            'bindingStatus':status,'decisionId':chosen,'offer':chosen not in (None,0),
            'tapAttempted':tap,'tapSuccess':tap,'deliveredDecisionId':chosen if tap else 0,
            'engineExcluded':False,'engineDecisionId':0,'inputChanged':False,
            'forbiddenEdits':0,'unsolicitedEdits':0,'harnessError':None}


class AttributionTest(unittest.TestCase):
    def setUp(self):
        self.assertTrue(Path(__file__).with_name('contextual_controller_attribution.py').is_file(),
                        'bounded contextual adapter is not implemented')
        self.tool=importlib.import_module('contextual_controller_attribution')

    def test_exact_payload_positive_and_no_query_are_distinct(self):
        self.assertEqual('EXACT_CACHE',self.tool.payload_status(request(),engine()))
        self.assertEqual('NO_CONTEXTUAL_REQUEST',self.tool.payload_status(None,engine()))

    def test_whitespace_case_and_candidate_order_are_not_normalized(self):
        for field,value in [('prefix','ordinary  left'),('continuations',[' Word']+request()['continuations'][1:]),
                            ('candidateIds',[1,0,2,3,4,5,6]),('continuations',list(reversed(request()['continuations'])))]:
            actual=request();actual[field]=value
            with self.subTest(field=field,value=value):
                self.assertEqual('PAYLOAD_MISMATCH',self.tool.payload_status(actual,engine()))

    def test_engine_exclusion_cannot_adopt_an_unrelated_score(self):
        old=engine();old['variants']=[]
        self.assertEqual('NEW_CONTEXTUAL_REQUEST',self.tool.payload_status(request(),old))
        self.assertEqual('NEW_CONTEXTUAL_REQUEST',self.tool.admit_response(request(),old,response())['status'])

    def test_exact_numeric_scores_are_preserved(self):
        result=self.tool.admit_response(request(),engine(),response())
        self.assertEqual('EXACT_CACHE_OK',result['status'])
        self.assertEqual(response(),result['response'])

    def test_payload_mismatch_is_refused_before_numeric_adoption(self):
        actual=request();actual['prefix']='different'
        self.assertEqual('PAYLOAD_MISMATCH',self.tool.admit_response(actual,engine(),response())['status'])

    def test_error_and_missing_payload_remain_explicit(self):
        self.assertEqual('EXACT_CACHE_ERROR',self.tool.admit_response(request(),engine(),
            {'id':'fixture','error':'SCORING_FAILED'})['status'])
        self.assertEqual('MISSING_RESPONSE',self.tool.admit_response(request(),engine(),None)['status'])

    def test_zero_256_and_reordered_reply_are_not_coerced(self):
        for counts in [0,256]:
            reply=response();reply['scores'][0].update(scoredTokenCount=counts,sumLogProbability=0 if counts==0 else -10)
            self.assertEqual('UNREPRESENTABLE_REPLY',self.tool.admit_response(request(),engine(),reply)['status'])
        reply=response();reply['scores'].reverse()
        self.assertEqual('UNREPRESENTABLE_REPLY',self.tool.admit_response(request(),engine(),reply)['status'])

    def test_malformed_response_never_becomes_abstention(self):
        for mutate in [lambda r:r.update(id='wrong'),lambda r:r.update(extra=True),
                       lambda r:r['scores'][0].update(sumLogProbability=math.nan),
                       lambda r:r['scores'][0].update(scoredTokenCount=True)]:
            reply=response();mutate(reply)
            with self.assertRaises(ValueError):self.tool.admit_response(request(),engine(),reply)

    def test_complete_denominators_and_manual_action_counts(self):
        rows=[metric_row('excluded'),metric_row('error',0,', ','EXACT_CACHE_ERROR'),
              metric_row('offer',1,', ','EXACT_CACHE_OK',True)]
        actual=self.tool.build_metrics(rows)
        self.assertEqual((3,1,1,1),(actual['rows'],actual['offers'],actual['tapAttempts'],actual['tapSuccesses']))
        self.assertEqual((2,3),(actual['sourceBoundaryAgreement']['numerator'],actual['sourceBoundaryAgreement']['denominator']))
        self.assertEqual(3,sum(actual['routingCounts'].values()))
        self.assertEqual(0,actual['automaticContextualEdits'])

    def test_unknown_payload_is_not_measured_original(self):
        actual=self.tool.build_metrics([metric_row('known'),metric_row('unknown',None,' ','PAYLOAD_MISMATCH')])
        self.assertFalse(actual['attributionComplete'])
        self.assertEqual(1,actual['unscoredPayloads'])
        self.assertIsNone(actual['sourceBoundaryAgreement'])
        self.assertEqual((1,2),(actual['knownSourceMatchesPerAllRows']['numerator'],actual['knownSourceMatchesPerAllRows']['denominator']))

    def test_zero_taps_return_null_rate(self):
        self.assertIsNone(self.tool.build_metrics([metric_row('none')])['tapSuccessRate']['value'])

    def test_duplicate_missing_and_unknown_host_rows_fail(self):
        rows=[{'id':'a'},{'id':'b'}]
        values=[{'schemaVersion':1,'scope':self.tool.SCOPE,'index':i,'id':row['id']} for i,row in enumerate(rows)]
        # Envelope validator must reject every incomplete/duplicate identity, before detailed parsing.
        for bad in [values[:1],values+[values[0]],[values[0],dict(values[1],id='unknown')]]:
            with self.assertRaises(ValueError):self.tool.validate_envelopes(bad,rows)

    def test_fresh_output_refuses_orphan_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'orphan';out.mkdir();(out/'complete.json').write_text('{}')
            with self.assertRaises(ValueError):self.tool.fresh_output(out,build_root=Path(tmp))
            self.assertEqual('{}',(out/'complete.json').read_text())

    def test_bound_file_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'bound';file.write_text('original')
            bound={str(file):self.tool.sha(file)}
            self.tool.verify_files(bound)
            file.write_text('changed')
            with self.assertRaises(ValueError):self.tool.verify_files(bound)

    def test_strict_export_admission_failure_cannot_fall_back(self):
        with mock.patch.object(self.tool.cq,'load_export',side_effect=ValueError('EXPORT_CORPUS_REPLAY')):
            with self.assertRaisesRegex(ValueError,'EXPORT_CORPUS_REPLAY'):
                self.tool.admit_inputs(*([Path('/synthetic')]*6))

    def test_metric_row_duplicates_and_invalid_boundary_fail(self):
        for rows in [[metric_row('same'),metric_row('same')],[dict(metric_row('bad'),observedBoundary='; ')]]:
            with self.assertRaises(ValueError):self.tool.build_metrics(rows)


class AdditionalGuardTest(unittest.TestCase):
    setUp=AttributionTest.setUp
    def test_unrepresentable_is_not_a_measured_abstention(self):
        row=metric_row('ipc',None,' ','UNREPRESENTABLE_REPLY')
        actual=self.tool.build_metrics([row])
        self.assertFalse(actual['attributionComplete'])
        self.assertIsNone(actual['sourceBoundaryAgreement'])

    def test_failure_and_unresolved_are_not_double_subtracted(self):
        row=metric_row('both',None,' ','PAYLOAD_MISMATCH')
        row['harnessError']={'type':'Failure'}
        self.assertEqual(0,self.tool.build_metrics([row])['abstentions'])

    def test_all_offers_require_an_attempt_and_success_for_clean_completion(self):
        row=metric_row('offer',1,', ','EXACT_CACHE_OK',False)
        self.assertFalse(self.tool.build_metrics([row])['attributionComplete'])
        row['tapAttempted']=True
        self.assertFalse(self.tool.build_metrics([row])['attributionComplete'])

    def test_tap_stage_failures_preserve_rows_without_negative_abstentions(self):
        for stage,attempted,succeeded in [('before-tap',False,False),
                ('refused-tap',True,False),('handled-tap',True,True),
                ('duplicate-tap',True,True)]:
            with self.subTest(stage=stage):
                row=metric_row(stage,None,', ','EXACT_CACHE_OK')
                row.update(offer=True,tapAttempted=attempted,tapSuccess=succeeded,
                           harnessError={'stage':stage})
                result=self.tool.build_metrics([row,metric_row('known-original')])
                self.assertEqual(2,result['rows'])
                self.assertEqual(1,result['offers'])
                self.assertEqual(1,result['abstentions'])
                self.assertEqual(1,result['harnessErrors'])
                self.assertEqual(int(attempted),result['tapAttempts'])
                self.assertEqual(int(succeeded),result['tapSuccesses'])
                self.assertEqual((1,2),(result['measuredAbstentionRate']['numerator'],
                                       result['measuredAbstentionRate']['denominator']))
                self.assertIsNone(result['sourceBoundaryAgreement'])
                self.assertFalse(result['attributionComplete'])

    def test_engine_comparison_uses_complete_rows_and_keeps_id_deltas(self):
        row=metric_row('blocked',0,', ')
        row['engineDecisionId']=1
        result=self.tool.build_metrics([row])
        self.assertEqual(1,result['engineOffers'])
        self.assertEqual(['blocked'],result['changedDecisionIds'])

    def test_verify_recompiles_sources_and_refuses_rehashed_false_observations(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary);protocol={'runtime':{'java':'java','gradleCache':'cache','androidJar':'stub'},'files':{'bound':'hash'}}
            prior=[{'actual':'request'}];actual=[{'actual':'tap'}]
            with mock.patch.object(self.tool,'compile_inputs',return_value=([],[],'version')), \
                 mock.patch.object(self.tool,'compile_host',return_value=['fresh-source-jar']) as compile_host, \
                 mock.patch.object(self.tool,'verify_files'), \
                 mock.patch.object(self.tool,'run_host',side_effect=[prior,actual]) as run:
                self.tool.verify_current_host(directory,protocol,directory,prior,actual)
                compile_host.assert_called_once()
                self.assertTrue(all(call.args[0]==['fresh-source-jar'] for call in run.call_args_list))
            with mock.patch.object(self.tool,'compile_inputs',return_value=([],[],'version')), \
                 mock.patch.object(self.tool,'compile_host',return_value=['fresh-source-jar']), \
                 mock.patch.object(self.tool,'verify_files'), \
                 mock.patch.object(self.tool,'run_host',return_value=[{'fabricated':'request'}]):
                with self.assertRaisesRegex(ValueError,'HOST_PREPARE_REPLAY'):
                    self.tool.verify_current_host(directory,protocol,directory,prior,actual)

    def test_secondary_reasons_are_exact_ordered_unique_and_source_consistent(self):
        self.tool.validate_secondary_reasons(['NO_OWNED_SPACE','ENGINE_EXCLUDED'])
        for bad in (None,['UNKNOWN'],['ENGINE_EXCLUDED','NO_OWNED_SPACE'],['ENGINE_EXCLUDED','ENGINE_EXCLUDED'],[True]):
            with self.assertRaisesRegex(ValueError,'HOST_SECONDARY_REASONS'):self.tool.validate_secondary_reasons(bad)
        import re
        source=Path(__file__).with_name('ContextualControllerAttribution.kt').read_text()
        declared=source.split('internal val secondaryReasonOrder = listOf(',1)[1].split(')\n',1)[0]
        self.assertEqual(self.tool.SECONDARY_REASONS,re.findall(r'"([A-Z_]+)"',declared))

    def test_runtime_error_names_include_digits_and_codes_are_source_bound(self):
        source='\n'.join(f'{name}({code}),' for name,code in self.tool.ERROR_MAP.items())
        self.tool.validate_runtime_error_codes(source)
        with self.assertRaisesRegex(ValueError,'RUNTIME_ERROR_CODES'):
            self.tool.validate_runtime_error_codes(source.replace('INVALID_UTF8(8)','INVALID_UTF8(9)'))

    def test_archived_command_is_not_a_compile_source_dependency(self):
        with tempfile.TemporaryDirectory() as temporary:
            android=Path(temporary)/'android.jar';android.touch()
            with mock.patch.object(self.tool,'read_json',side_effect=AssertionError('archive used as active input')), \
                 mock.patch.object(self.tool.cq,'toolchain',return_value=[]), \
                 mock.patch.object(self.tool.subprocess,'run',return_value=mock.Mock(stderr=b'version "17.0.1"')):
                sources,_,_=self.tool.compile_inputs('java','cache',android)
            self.assertEqual(49,len(sources))
            self.assertEqual(49,len(set(sources)))
            self.assertTrue(all(p.is_file() for p in sources))
            self.assertIn(self.tool.HERE/'ContextualControllerAttribution.kt',sources)

    def test_host_schema_cannot_silently_drop_or_add_a_field(self):
        for row in [{'scope':self.tool.SCOPE}, {'schemaVersion':1,'unexpected':True}]:
            with self.assertRaises(ValueError):self.tool.validate_host_records([row])

    def test_host_coverage_requires_every_named_case_exactly_once(self):
        for records in [[], [{'case':'anything','passed':True}],
                        [{'case':n,'passed':True} for n in self.tool.HOST_CASES]+[{'case':self.tool.HOST_CASES[0],'passed':True}]]:
            with self.assertRaises(ValueError):self.tool.validate_host_tests(records)
        self.tool.validate_host_tests([{'case':n,'passed':True} for n in self.tool.HOST_CASES])


class StrictAdapterFlowTest(unittest.TestCase):
    setUp=AttributionTest.setUp

    def fixture(self):
        # Existing public synthetic export fixture; this does not load a real corpus or score.
        support=importlib.import_module('test_contextual_v5_adapter')
        value=support.V5ReceiptFlowTest();value.setUp();self.addCleanup(value.doCleanups)
        return value,value.export()

    def test_actual_export_loader_failure_propagates_through_new_adapter(self):
        fixture,export=self.fixture()
        fixture.loader.load_corpus=lambda path:(_ for _ in ()).throw(ValueError('SELECTION_REPLAY_COUNTS'))
        with self.assertRaisesRegex(ValueError,'SELECTION_REPLAY_COUNTS'):
            self.tool.admit_inputs(fixture.corpus,export,*([fixture.root/'unused']*4))

    def test_self_rehashed_legacy_or_changed_labels_cannot_enter_new_adapter(self):
        fixture,export=self.fixture()
        receipt=json.loads((export/'provenance.json').read_text())
        original=(export/'rows.jsonl').read_text()
        for mutation in ('downgrade','label','mixed'):
            changed=copy.deepcopy(receipt);records=[json.loads(line) for line in original.splitlines()]
            if mutation=='downgrade':
                for record in records:
                    for key in ('corpusVersion','labelSemantics','observedBoundary'):record.pop(key)
                    record.update(ambiguous=False,expectedCandidate=0)
                for key in (*self.tool.cq.CORPUS_BINDING_KEYS,'corpusDirectory'):changed.pop(key)
            elif mutation=='label':records[0]['observedBoundary']='. '
            else:records[0]['ambiguous']=False
            (export/'rows.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
            changed['records']=self.tool.sha(export/'rows.jsonl')
            (export/'provenance.json').write_text(json.dumps(changed))
            with self.assertRaises(ValueError):
                self.tool.admit_inputs(fixture.corpus,export,*([fixture.root/'unused']*4))

    def test_split_cache_receipt_and_backend_links_are_exact(self):
        fixture,export=self.fixture();cq=self.tool.cq
        records=cq.load_export(export);binding=cq.records_binding(records)
        split='calibration';selected=cq.requests(records,split)
        identity={'protocol':'rune-score-jsonl-v1','runnerSha256':'synthetic-runner','modelSha256':'synthetic-model',
                  'corpusSha256':cq.evaluator().digest(selected)}
        frozen={'configSha256':'frozen','modelIdentity':identity}
        directory=fixture.root/'cache';directory.mkdir()
        replies=[dict(response(),id=r['id']) for r in selected]
        replies[0]={'id':selected[0]['id'],'error':'SCORING_FAILED'}
        cache=json.dumps({'cacheIdentity':identity})+'\n'+''.join(json.dumps(r)+'\n' for r in replies)
        (directory/'scores.jsonl').write_text(cache)
        header={**cq.policy_binding(),**binding,'scope':'contextual-calibration-scores','split':split,
                'requests':len(selected),'identity':identity,'exportReceiptSha256':self.tool.sha(export/'provenance.json'),
                'frozenConfigSha256':None}
        complete={**header,'scores':len(selected),'runtimeErrors':1,'scoresSha256':self.tool.sha(directory/'scores.jsonl')}
        def write(h,c):
            (directory/'run-input.json').write_text(json.dumps(h));(directory/'complete.json').write_text(json.dumps(c))
        write(header,complete)
        result=self.tool.admit_score_split(directory,records,binding,split,header['exportReceiptSha256'],frozen)
        self.assertEqual(len(replies),len(result[1]));self.assertEqual(1,result[0]['runtimeErrors'])
        for field,value in [('split','holdout'),('exportReceiptSha256','changed'),('frozenConfigSha256','changed'),
                            ('runtimeErrors',0),('identity',{**identity,'runnerSha256':'changed'})]:
            altered={**complete,field:value};h={k:v for k,v in altered.items() if k not in ('scores','runtimeErrors','scoresSha256')}
            write(h,altered)
            with self.assertRaises(ValueError):self.tool.admit_score_split(directory,records,binding,split,header['exportReceiptSha256'],frozen)
        write({**header,'requests':0},complete)
        with self.assertRaises(ValueError):self.tool.admit_score_split(directory,records,binding,split,header['exportReceiptSha256'],frozen)
        write(header,complete);(directory/'scores.jsonl').write_text(cache+'\n')
        with self.assertRaises(ValueError):self.tool.admit_score_split(directory,records,binding,split,header['exportReceiptSha256'],frozen)




class SupplementalAdmissionTest(unittest.TestCase):
    setUp=AttributionTest.setUp

    def test_supplement_admits_exact_ordered_errors_without_relabeling_old_cache(self):
        self.assertTrue(callable(getattr(self.tool,'validate_supplement_responses',None)),
                        'supplemental response boundary is absent')
        rows=[dict(id='cal-one',split='calibration',language='en',prefix='ordinary left',
                   candidateIds=list(range(7)),candidates=request()['continuations']),
              dict(id='cal-two',split='calibration',language='en',prefix='ordinary other',
                   candidateIds=list(range(7)),candidates=request()['continuations'])]
        replies=[dict(response(),id='cal-one'),{'id':'cal-two','error':'SCORING_FAILED'}]
        admitted=self.tool.validate_supplement_responses(rows,replies)
        self.assertEqual(['SUPPLEMENT_OK','SUPPLEMENT_ERROR'],[v['status'] for v in admitted])
        self.assertEqual(replies,[v['response'] for v in admitted])

    def test_missing_duplicate_unexpected_order_and_bad_numeric_responses_fail(self):
        self.assertTrue(callable(getattr(self.tool,'validate_supplement_responses',None)))
        rows=[dict(id=v,split='calibration',language='en',prefix='ordinary',
                   candidateIds=list(range(7)),candidates=request()['continuations']) for v in ('a','b')]
        good=[dict(response(),id=v) for v in ('a','b')]
        bad_numbers=copy.deepcopy(good);bad_numbers[0]['scores'][0]['sumLogProbability']=math.nan
        wrong_order=copy.deepcopy(good);wrong_order[0]['scores'].reverse()
        for bad in (good[:1],good+[good[0]],[good[0],good[0]],list(reversed(good)),
                    [dict(good[0],id='unexpected'),good[1]],bad_numbers,wrong_order):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):self.tool.validate_supplement_responses(rows,bad)
        zero=copy.deepcopy(good);zero[0]['scores'][0].update(scoredTokenCount=0,sumLogProbability=0)
        self.assertEqual('UNREPRESENTABLE_REPLY',self.tool.validate_supplement_responses(rows,zero)[0]['status'])

    def fixture(self):
        from types import SimpleNamespace
        temporary=tempfile.TemporaryDirectory(dir=self.tool.REPO/'build');self.addCleanup(temporary.cleanup)
        root=Path(temporary.name);prepared=root/'prepared';prepared.mkdir()
        runner=root/'runner';runner.write_text('synthetic executable');model=root/'model';model.write_text('synthetic weights')
        identity=dict(protocol='rune-score-jsonl-v1',runnerSha256=self.tool.sha(runner),modelSha256=self.tool.sha(model))
        for name,value in [('MODEL_SHA',identity['modelSha256']),('RUNNER_SHA',identity['runnerSha256'])]:
            patch=mock.patch.object(self.tool,name,value);patch.start();self.addCleanup(patch.stop)
        backend=root/'backend-config.json';backend.write_text(json.dumps(dict(model=str(model),runner=str(runner),
            modelBytes=model.stat().st_size,modelIdentity=identity)))
        original_protocol=root/'protocol.json';original_protocol.write_text('{}')
        config=root/'config.json';config.write_text('{}')
        protocol=dict(protocolSha256='prepared-protocol',locations=dict(config=str(config),protocol=str(original_protocol)),
                      files={str(backend):self.tool.sha(backend)})
        (prepared/'protocol.json').write_text(json.dumps(protocol));(prepared/'prepare-complete.json').write_text('{}')
        (prepared/'unscored-request-receipt.json').write_text('{}')
        rows=[];records=[];prior=[]
        for split in ('calibration','holdout'):
            for suffix in ('mismatch','exact','none'):
                identifier=split+'-'+suffix;rows.append(dict(id=identifier,split=split,language='en'))
                records.append(dict(engine(),id=identifier,split=split))
                q=dict(request(),prefix='changed left') if suffix=='mismatch' else request() if suffix=='exact' else None
                prior.append(dict(id=identifier,modelRequest=q,routing='CONTEXTUAL_REQUEST' if q else 'SPELLING_REQUEST'))
        bundle=dict(rows=rows,records=records,config=dict(configSha256='fixed-config'),
                    protocol=dict(backendIdentity=identity,policy=dict(originalMargin=0.5,rivalMargin=4.0)),
                    complete={split:dict(scoresSha256='synthetic-original-'+split) for split in ('calibration','holdout')},
                    scores={split:{r['id']:dict(response(),id=r['id']) for r in rows if r['split']==split}
                            for split in ('calibration','holdout')})
        # Only the expensive already-reviewed full-corpus boundary is substituted. All supplement files,
        # physical identity hashes, split ordering, numeric validation and replay binding selection are real.
        context=(prepared,protocol,bundle,prior)
        patch=mock.patch.object(self.tool,'load_prepared',return_value=context);patch.start();self.addCleanup(patch.stop)
        freeze=root/'freeze'
        self.tool.freeze_supplement(SimpleNamespace(prepared=prepared,output=freeze))
        return SimpleNamespace(root=root,prepared=prepared,freeze=freeze,context=context,runner=runner,model=model)

    def stage(self,f,split,calibration=None):
        from types import SimpleNamespace
        out=f.freeze/split
        self.tool.stage_supplement(SimpleNamespace(freeze=f.freeze,split=split,output=out,calibration=calibration))
        return out

    def external(self,run,error=False):
        rows=self.tool.read_jsonl(run/'requests.jsonl')
        self.tool.write_jsonl(run/'responses.jsonl',[
            dict(id=r['id'],error='SCORING_FAILED') if error else dict(response(),id=r['id']) for r in rows])
        (run/'stderr.log').write_text('synthetic native diagnostic')
        self.tool.write_json(run/'execution.json',dict(schemaVersion=1,attempts=1,exitCode=0,
            commandSha256=self.tool.sha(run/'command.json'),runInputSha256=self.tool.sha(run/'run-input.json'),
            requestsSha256=self.tool.sha(run/'requests.jsonl'),responsesSha256=self.tool.sha(run/'responses.jsonl'),
            stderrSha256=self.tool.sha(run/'stderr.log')))

    def complete(self,f,run):
        from types import SimpleNamespace
        self.tool.complete_supplement(SimpleNamespace(freeze=f.freeze,run=run))

    def test_split_chain_retains_error_and_only_overrides_unmatched_contextual_requests(self):
        self.assertTrue(callable(getattr(self.tool,'freeze_supplement',None)))
        f=self.fixture();cal=self.stage(f,'calibration');self.external(cal,error=True);self.complete(f,cal)
        hold=self.stage(f,'holdout',cal);self.external(hold);self.complete(f,hold)
        freeze,context=self.tool.load_supplement_freeze(f.freeze)
        supplied=self.tool.load_supplements(f.freeze,cal,hold,context)
        bindings=self.tool.make_response_bindings(context[2],context[3],supplied)
        self.assertEqual(['SUPPLEMENT_ERROR','EXACT_CACHE_OK','NO_CONTEXTUAL_REQUEST',
                          'SUPPLEMENT_OK','EXACT_CACHE_OK','NO_CONTEXTUAL_REQUEST'],[b['status'] for b in bindings])
        self.assertEqual('SCORING_FAILED',bindings[0]['response']['error'])
        self.assertEqual(['SUPPLEMENT_ERROR','EXACT_CACHE_OK','NO_CONTEXTUAL_REQUEST','SUPPLEMENT_OK','EXACT_CACHE_OK','NO_CONTEXTUAL_REQUEST'],
            [line.split('\t')[2] for line in self.tool.response_tsv(bindings).splitlines()])
        self.assertEqual('supplement',bindings[0]['provenance']['kind'])
        self.assertEqual('original-v5-cache',bindings[1]['provenance']['kind'])
        self.assertIsNone(bindings[2]['response'])
        self.assertEqual(['calibration-mismatch'],self.tool.read_json(cal/'complete.json')['errorIds'])
        self.assertEqual(self.tool.sha(cal/'complete.json'),self.tool.read_json(hold/'run-input.json')['calibrationCompleteSha256'])
        self.assertEqual('calibration-mismatch',self.tool.read_jsonl(cal/'requests.jsonl')[0]['id'])
        self.assertNotIn('split',self.tool.read_jsonl(cal/'requests.jsonl')[0])
        for mutate in ('prefix','candidateIds','no-query','exact-cache'):
            altered=copy.deepcopy(context[3])
            if mutate=='prefix':altered[0]['modelRequest']['prefix']='stale'
            elif mutate=='candidateIds':altered[0]['modelRequest']['candidateIds'].reverse()
            elif mutate=='no-query':altered[0]['routing']='SPELLING_REQUEST'
            else:altered[0]['modelRequest']=request()
            with self.assertRaises(ValueError):self.tool.make_response_bindings(context[2],altered,supplied)

    def test_holdout_needs_completed_calibration_and_orphan_run_is_refused(self):
        self.assertTrue(callable(getattr(self.tool,'freeze_supplement',None)))
        f=self.fixture()
        with self.assertRaises(ValueError):self.stage(f,'holdout')
        cal=self.stage(f,'calibration')
        from types import SimpleNamespace
        with self.assertRaises(ValueError):
            self.tool.stage_supplement(SimpleNamespace(freeze=f.freeze,split='calibration',output=f.root/'retry',calibration=None))
        with self.assertRaises((ValueError,FileNotFoundError)):self.stage(f,'holdout',cal)
        with self.assertRaises(ValueError):self.stage(f,'calibration')
        self.assertFalse((cal/'complete.json').exists())

    def test_admission_rejects_artifact_drift_nonzero_exit_and_partial_output(self):
        self.assertTrue(callable(getattr(self.tool,'freeze_supplement',None)))
        f=self.fixture();run=self.stage(f,'calibration');self.external(run)
        originals={p.name:p.read_bytes() for p in run.iterdir() if p.is_file()}
        mutations=[('execution.json',lambda x:x.update(exitCode=1)),('execution.json',lambda x:x.update(attempts=2)),('execution.json',lambda x:x.update(attempts=True)),
                   ('run-input.json',lambda x:x.update(split='holdout')),
                   ('identity.json',lambda x:x['backendIdentity'].update(modelSha256='0'*64)),
                   ('command.json',lambda x:x['argv'].reverse()),
                   ('execution.json',lambda x:x.update(responsesSha256='0'*64))]
        for name,mutation in mutations:
            value=json.loads(originals[name]);mutation(value);(run/name).write_text(json.dumps(value))
            with self.subTest(name=name):
                with self.assertRaises(ValueError):self.complete(f,run)
                self.assertFalse((run/'complete.json').exists())
            (run/name).write_bytes(originals[name])
        for bad in (b'',originals['responses.jsonl'].rstrip(b'\n'),originals['responses.jsonl']*2):
            (run/'responses.jsonl').write_bytes(bad)
            execution=json.loads(originals['execution.json']);execution['responsesSha256']=self.tool.sha(run/'responses.jsonl')
            (run/'execution.json').write_text(json.dumps(execution))
            with self.assertRaises(ValueError):self.complete(f,run)
        for name,value in originals.items():(run/name).write_bytes(value)
        self.complete(f,run)
        with self.assertRaises(ValueError):self.complete(f,run)

    def test_rehashed_freeze_cannot_change_policy_backend_universe_or_preparation(self):
        self.assertTrue(callable(getattr(self.tool,'freeze_supplement',None)))
        f=self.fixture();path=f.freeze/'freeze.json';original=path.read_bytes()
        for mutation in (lambda x:x['requests'][0].update(prefix='fabricated'),
                         lambda x:x['requests'][0].update(split='holdout'),
                         lambda x:x['requests'][0]['candidateIds'].reverse(),
                         lambda x:x['requests'].reverse(),lambda x:x['requests'].append(x['requests'][0]),
                         lambda x:x['policy'].update(originalMargin=0),
                         lambda x:x['backendIdentity'].update(runnerSha256='0'*64),
                         lambda x:x.update(preparedCompleteSha256='0'*64),
                         lambda x:x.update(configSha256='fabricated')):
            value=json.loads(original);mutation(value);value['freezeSha256']=self.tool.digest({k:v for k,v in value.items() if k!='freezeSha256'})
            path.write_text(json.dumps(value))
            with self.assertRaises(ValueError):self.tool.load_supplement_freeze(f.freeze)
        path.write_bytes(original);f.model.write_text('different weights')
        with self.assertRaises(ValueError):self.tool.load_supplement_freeze(f.freeze)


if __name__=='__main__':unittest.main()
