"""Synthetic v5 consumer contracts; no real corpus text, model or score cache."""
import base64
import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import contextual_quality as cq


FORMAT = 'contextual-v5'
LABEL = 'observed_wikipedia_boundary'


def row(identifier='fixture', boundary=', ', split='holdout', language='en', excluded=False):
    return {'corpusVersion':5,'id':identifier,'split':split,'language':language,
            'task':'punctuation','prefix':'fixture 2011' if excluded else 'ordinary fixture',
            'currentWord':'palabra' if language=='es' else 'слово' if language=='ru' else 'word',
            'observedBoundary':boundary,'labelSemantics':LABEL,'noAuto':True}


def protocol(rows):
    encoded=lambda text:base64.b64encode(text.encode()).decode()
    lines=[]
    for index,item in enumerate(rows):
        excluded=item['prefix'].endswith('2011')
        lines.append(f'R\t{index}\t{0 if excluded else 7}')
        if excluded:continue
        word=item['currentWord']
        for candidate,boundary in enumerate(cq.BOUNDARIES):
            continuation=boundary+(word[:1].upper()+word[1:] if candidate>=4 else word)
            lines.append(f'C\t{index}\t{candidate}\t{encoded(boundary)}\t{encoded(continuation)}')
    return '\n'.join(lines)+'\n'


def score(winner):
    return {'scores':[{'id':i,'sumLogProbability':-1 if i==winner else -10,
                      'scoredTokenCount':1} for i in range(7)]}


class V5AdapterTest(unittest.TestCase):
    def test_explicit_v5_uses_full_loader_and_propagates_admission_failure(self):
        self.assertTrue(hasattr(cq,'v5_loader'),'explicit strict v5 adapter is absent')
        rows=[row(str(i)) for i in range(1200)]
        admitted=mock.Mock(load_corpus=mock.Mock(return_value=(rows,{'corpusVersion':5,'labelSemantics':LABEL})))
        with tempfile.TemporaryDirectory() as directory,mock.patch.object(cq,'v5_loader',return_value=admitted):
            self.assertEqual(rows,cq.corpus_rows(Path(directory),FORMAT))
            admitted.load_corpus.assert_called_once_with(Path(directory).resolve())
            admitted.load_corpus.side_effect=ValueError('SELECTION_REPLAY_ROWS')
            with self.assertRaisesRegex(ValueError,'SELECTION_REPLAY_ROWS'):
                cq.corpus_rows(Path(directory),FORMAT)

    def test_default_legacy_loader_keeps_its_existing_full_corpus_validation(self):
        rows=[{'task':'punctuation','id':str(i)} for i in range(1200)]+[{'task':'spelling','id':'spelling'}]
        legacy=SimpleNamespace(load_corpus=mock.Mock(return_value=rows),validate=mock.Mock())
        with tempfile.TemporaryDirectory() as directory,mock.patch.object(cq,'evaluator',return_value=legacy), \
             mock.patch.object(cq,'v5_loader',side_effect=AssertionError('legacy must not enter v5')):
            self.assertEqual(rows[:-1],cq.corpus_rows(Path(directory)))
            legacy.load_corpus.assert_called_once_with(Path(directory).resolve())
            legacy.validate.assert_called_once_with(rows)

    def test_v5_protocol_preserves_source_labels_seven_variants_and_exclusions(self):
        rows=[row('ordinary'),row('excluded',' ',excluded=True)]
        parsed=cq.parse_output(protocol(rows),rows,FORMAT)
        self.assertEqual([7,0],[len(item['variants']) for item in parsed])
        for item,source in zip(parsed,rows):
            self.assertEqual((5,LABEL,source['observedBoundary']),
                             (item['corpusVersion'],item['labelSemantics'],item['observedBoundary']))
            self.assertNotIn('ambiguous',item);self.assertNotIn('expectedCandidate',item)
        self.assertEqual('. Word',parsed[0]['variants'][4]['continuation'])

    def test_v5_protocol_rejects_semantic_labels_and_changed_continuations(self):
        for key,value in (('ambiguous',False),('expectedCandidate',1),('expectedBoundary',', ')):
            rows=[{**row(),key:value}]
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'V5_ROW_SEMANTICS'):
                cq.parse_output(protocol(rows),rows,FORMAT)
        rows=[row()];text=protocol(rows)
        text=text.replace(base64.b64encode(b'. Word').decode(),base64.b64encode(b'. Other').decode())
        with self.assertRaisesRegex(ValueError,'V5_CONTINUATIONS'):
            cq.parse_output(text,rows,FORMAT)

    def test_observed_boundary_metrics_keep_errors_exclusions_and_complete_denominators(self):
        rows=[row('comma',', '),row('space',' '),row('period','. '),row('colon',': '),
              row('excluded',' ',excluded=True),row('error',', ')]
        parsed=cq.parse_output(protocol(rows),rows,FORMAT)
        scores={'comma':score(1),'space':score(3),'period':score(0),'colon':score(2),
                'error':{'error':'SCORING_FAILED'}}
        actual=cq.source_metrics(parsed,scores)
        rate=cq.evaluator().rate
        self.assertEqual(6,actual['rows'])
        self.assertEqual(rate(3,6),actual['sourceBoundaryAgreement'])
        self.assertEqual(rate(3,6),actual['suggestionCoverage'])
        self.assertEqual(rate(3,6),actual['abstention'])
        self.assertEqual(rate(1,2),actual['insertionAtObservedSpaces'])
        self.assertEqual(rate(1,6),actual['productionExclusionRate'])
        self.assertEqual(rate(1,6),actual['runtimeErrorRate'])
        self.assertEqual({'original':3,'comma':1,'colon':1,'semicolon':1,'period':0,'question':0,'exclamation':0},actual['decisionCounts'])
        self.assertEqual(rate(1,2),actual['byObservedBoundary']['comma']['sourceBoundaryAgreement'])
        self.assertEqual(rate(1,2),actual['byObservedBoundary']['comma']['runtimeErrorRate'])
        self.assertEqual(0,actual['automaticReplacements'])
        for forbidden in ('suggestionPrecision','ambiguousRows','unambiguousRows','qualityPass'):
            self.assertNotIn(forbidden,actual)

    def test_record_and_receipt_binding_rejects_mixing_downgrades_and_source_drift(self):
        parsed=cq.parse_output(protocol([row()]),[row()],FORMAT)
        binding=cq.records_binding(parsed)
        self.assertEqual((FORMAT,5,LABEL),(binding['corpusFormat'],binding['corpusVersion'],binding['labelSemantics']))
        self.assertEqual(4,len(binding['corpusLoaderSources']))
        for changed in ({}, {**binding,'corpusVersion':4}, {**binding,'labelSemantics':'unambiguous'},
                        {**binding,'corpusLoaderSources':{}}):
            with self.assertRaisesRegex(ValueError,'CORPUS_BINDING'):
                cq.require_corpus_binding(changed,binding)
        with self.assertRaisesRegex(ValueError,'CORPUS_BINDING'):
            cq.require_corpus_binding(binding,{})
        for legacy in ({'id':'legacy','variants':[]}, {**parsed[0],'ambiguous':False},
                       {**parsed[0],'corpusVersion':4}):
            with self.assertRaisesRegex(ValueError,'MIXED_CORPUS_RECORDS'):
                cq.records_binding([*parsed,legacy])


class V5ReceiptFlowTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='contextual-v5-unit-',dir=cq.shared.REPO/'build')
        self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.rows=[row(f'{language}-{split}-{boundary_index}-{i}',boundary,split,language,excluded=i!=0)
            for language in ('en','ru','es') for split in ('calibration','holdout')
            for boundary_index,boundary in enumerate((' ', ', ', ': ', '. ')) for i in range(50)]
        self.corpus=self.root/'corpus';self.corpus.mkdir()
        (self.corpus/'manifest.json').write_text(json.dumps({'corpusVersion':5,'labelSemantics':LABEL}))
        self.java=self.root/'java';self.java.write_bytes(b'synthetic Java')
        self.jars=[self.root/f'fixture-{i}.jar' for i in range(3)]
        for jar in self.jars:jar.write_bytes(b'synthetic jar')
        self.assertTrue(hasattr(cq,'v5_loader'),'explicit strict v5 adapter is absent')
        self.loader=SimpleNamespace(load_corpus=lambda directory:(self.rows,{'corpusVersion':5,'labelSemantics':LABEL}))
        for patch in (mock.patch.object(cq,'v5_loader',return_value=self.loader),
                      mock.patch.object(cq,'toolchain',return_value=self.jars)):
            patch.start();self.addCleanup(patch.stop)

    def fake_process(self,command,**kwargs):
        if command[-1]=='-version':return subprocess.CompletedProcess(command,0,b'',b'openjdk version "17.synthetic"\n')
        if 'org.jetbrains.kotlin.cli.jvm.K2JVMCompiler' in command:
            Path(command[command.index('-d')+1]).write_bytes(b'synthetic compiled exporter')
        else:kwargs['stdout'].write(protocol(self.rows).encode())
        return subprocess.CompletedProcess(command,0)

    def export(self):
        target=self.root/'export'
        with mock.patch.object(cq.subprocess,'run',side_effect=self.fake_process),redirect_stdout(io.StringIO()):
            cq.export_run(SimpleNamespace(output=target,corpus=self.corpus,corpus_format=FORMAT,
                                          java=str(self.java),gradle_cache=self.root))
        return target

    def test_export_reloads_strict_corpus_and_rejects_rehashed_record_or_label_tampering(self):
        target=self.export();records=cq.load_export(target)
        self.assertEqual(1200,len(records))
        self.assertEqual(24,sum(bool(item['variants']) for item in records))
        receipt=json.loads((target/'provenance.json').read_text())
        self.assertEqual(cq.records_binding(records),{key:receipt[key] for key in cq.CORPUS_BINDING_KEYS})
        raw=(target/'rows.jsonl').read_bytes()
        for change in ('observation','downgrade','loader'):
            changed=copy.deepcopy(receipt)
            if change=='observation':
                altered=copy.deepcopy(records);altered[0]['observedBoundary']='. '
                (target/'rows.jsonl').write_text(''.join(json.dumps(item)+'\n' for item in altered))
                changed['records']=cq.shared.sha(target/'rows.jsonl')
            elif change=='downgrade':
                for key in cq.CORPUS_BINDING_KEYS:changed.pop(key)
            else:changed['corpusLoaderSources']={}
            (target/'provenance.json').write_text(json.dumps(changed))
            with self.subTest(change=change),self.assertRaises(ValueError):cq.load_export(target)
            (target/'rows.jsonl').write_bytes(raw)
        (target/'provenance.json').write_text(json.dumps(receipt))
        self.loader.load_corpus=lambda directory:(_ for _ in ()).throw(ValueError('SELECTION_REPLAY_COUNTS'))
        with self.assertRaisesRegex(ValueError,'SELECTION_REPLAY_COUNTS'):cq.load_export(target)

    def test_full_export_admission_rejects_self_consistent_legacy_downgrade_without_location(self):
        target=self.export();records=cq.load_export(target)
        receipt=json.loads((target/'provenance.json').read_text())
        for item in records:
            observed=item.pop('observedBoundary')
            item.pop('corpusVersion');item.pop('labelSemantics')
            item.update({'ambiguous':False,'expectedCandidate':cq.BOUNDARIES.index(observed)})
        (target/'rows.jsonl').write_text(''.join(json.dumps(item)+'\n' for item in records))
        receipt['records']=cq.shared.sha(target/'rows.jsonl')
        for key in (*cq.CORPUS_BINDING_KEYS,'corpusDirectory'):receipt.pop(key)
        (target/'provenance.json').write_text(json.dumps(receipt))
        # All retained export digests and source-policy fields are valid. Removing
        # provenance must never route this v5 corpus into unchecked legacy admission.
        with self.assertRaisesRegex(ValueError,'EXPORT_CORPUS_LOCATION'):
            cq.load_export(target)

    def test_current_legacy_export_requires_corpus_manifest_and_full_replay(self):
        self.rows=[{key:value for key,value in item.items()
                    if key not in ('corpusVersion','labelSemantics','observedBoundary')}
                   | {'corpusVersion':4,'ambiguous':False,'expectedBoundary':item['observedBoundary']}
                   for item in self.rows]
        (self.corpus/'manifest.json').write_text(json.dumps({'corpusVersion':4}))
        legacy=cq.evaluator()
        legacy.load_corpus=mock.Mock(return_value=self.rows)
        legacy.validate=mock.Mock()
        target=self.root/'legacy-export'
        with mock.patch.object(cq,'evaluator',return_value=legacy), \
             mock.patch.object(cq.subprocess,'run',side_effect=self.fake_process),redirect_stdout(io.StringIO()):
            cq.export_run(SimpleNamespace(output=target,corpus=self.corpus,corpus_format='legacy-full',
                                          java=str(self.java),gradle_cache=self.root))
            records=cq.load_export(target)
            self.assertEqual(1200,len(records))
            original=(target/'rows.jsonl').read_bytes()
            receipt=json.loads((target/'provenance.json').read_text())
            for change in ('missing-manifest','wrong-manifest','changed-record'):
                changed=copy.deepcopy(receipt)
                if change=='missing-manifest':changed.pop('corpusManifest')
                elif change=='wrong-manifest':changed['corpusManifest']='0'*64
                else:
                    altered=copy.deepcopy(records);altered[0]['expectedCandidate']=6
                    (target/'rows.jsonl').write_text(''.join(json.dumps(item)+'\n' for item in altered))
                    changed['records']=cq.shared.sha(target/'rows.jsonl')
                (target/'provenance.json').write_text(json.dumps(changed))
                with self.subTest(change=change),self.assertRaises(ValueError):cq.load_export(target)
                (target/'rows.jsonl').write_bytes(original)
            (target/'provenance.json').write_text(json.dumps(receipt))
            legacy.load_corpus.reset_mock();legacy.validate.reset_mock()
            self.assertEqual(records,cq.load_export(target))
            legacy.load_corpus.assert_called_once_with(self.corpus.resolve())
            legacy.validate.assert_called_once_with(self.rows)

    def score_artifacts(self,records,split,export_hash,binding):
        selected=cq.requests(records,split);directory=self.root/f'{split}-scores';directory.mkdir()
        identity={'protocol':cq.evaluator().PROTOCOL,'corpusSha256':cq.evaluator().digest(selected),
                  'runnerSha256':'synthetic-runner','modelSha256':'synthetic-model'}
        cache=directory/'scores.jsonl'
        cache.write_text(json.dumps({'cacheIdentity':identity})+'\n'+''.join(json.dumps({
            'id':item['id'],'durationMillis':1,**score(1)})+'\n' for item in selected))
        info={**cq.policy_binding(),**binding,'scope':f'contextual-{split}-scores','split':split,
              'requests':len(selected),'identity':identity,'exportReceiptSha256':export_hash,
              'frozenConfigSha256':None}
        complete={**info,'scores':len(selected),'runtimeErrors':0,'scoresSha256':cq.shared.sha(cache)}
        (directory/'run-input.json').write_text(json.dumps(info));(directory/'complete.json').write_text(json.dumps(complete))
        return directory,complete

    def test_synthetic_freeze_and_report_bind_v5_and_never_create_semantic_metrics(self):
        export=self.export();records=cq.load_export(export);binding=cq.records_binding(records)
        export_hash=cq.shared.sha(export/'provenance.json')
        scoring,complete=self.score_artifacts(records,'calibration',export_hash,binding)
        self.assertEqual(12,len(cq.load_scores(scoring,cq.requests(records,'calibration'),binding)[1]))
        with self.assertRaisesRegex(ValueError,'CORPUS_BINDING'):
            cq.load_scores(scoring,cq.requests(records,'calibration'))
        verification=self.root/'verification';verification.mkdir()
        (verification/'verification.json').write_text('synthetic verification boundary')
        output=self.root/'freeze'
        with mock.patch.object(cq,'load_verification',return_value={}),redirect_stdout(io.StringIO()):
            cq.freeze_run(SimpleNamespace(policy_verification=verification,export=export,scoring=scoring,output=output))
            config=cq.load_frozen(output/'config.json',export_hash,binding)
            with self.assertRaisesRegex(ValueError,'CORPUS_BINDING'):
                cq.load_frozen(output/'config.json',export_hash)
            self.assertEqual(binding,{key:config[key] for key in cq.CORPUS_BINDING_KEYS})
            self.assertFalse(config['qualityGateEstablished'])
            original=(output/'config.json').read_bytes()
            changed={key:value for key,value in config.items() if key!='configSha256'}
            changed['qualityGateEstablished']=0
            (output/'config.json').write_text(json.dumps({**changed,'configSha256':cq.evaluator().digest(changed)}))
            with self.assertRaisesRegex(ValueError,'V5_METRIC_SEMANTICS'):
                cq.load_frozen(output/'config.json',export_hash,binding)
            (output/'config.json').write_bytes(original)
            holdout,receipt=self.score_artifacts(records,'holdout',export_hash,binding)
            receipt['frozenConfigSha256']=config['configSha256']
            (holdout/'complete.json').write_text(json.dumps(receipt))
            (holdout/'run-input.json').write_text(json.dumps({k:v for k,v in receipt.items()
                if k not in ('scores','runtimeErrors','scoresSha256')}))
            report_dir=self.root/'report'
            cq.report_run(SimpleNamespace(export=export,scoring=holdout,frozen_config=output/'config.json',output=report_dir))
        report=json.loads((report_dir/'report.json').read_text())
        self.assertEqual(binding,{key:report[key] for key in cq.CORPUS_BINDING_KEYS})
        self.assertFalse(report['qualityGateEstablished'])
        for language in ('en','ru','es'):
            self.assertEqual(200,report['languages'][language]['rows'])
            self.assertEqual(196,report['languages'][language]['productionExcludedRows'])
            self.assertNotIn('suggestionPrecision',report['languages'][language])
            self.assertEqual(4,len(report['languages'][language]['byObservedBoundary']))

    def test_score_run_binds_v5_before_only_synthetic_numeric_responses(self):
        export=self.export();records=cq.load_export(export);binding=cq.records_binding(records)
        runner=self.root/'runner';runner.write_bytes(b'synthetic executable, never launched')
        model=self.root/'model';model.write_bytes(b'synthetic model, never loaded')
        backend={'modelIdentity':{'runnerSha256':cq.shared.sha(runner),'modelSha256':cq.shared.sha(model)}}
        config=self.root/'backend.json'
        config.write_text(json.dumps({**backend,'configSha256':cq.evaluator().digest(backend)}))
        output=self.root/'score-output';requests_seen=[]
        def synthetic_responses(selected,runner_path,model_path,cache,ev,limit,model_sha,expected_bytes):
            requests_seen.extend(selected)
            identity=ev.cache_identity(selected,runner_path,model_path,model_sha,expected_bytes)
            cache.write_text(json.dumps({'cacheIdentity':identity})+'\n'+''.join(json.dumps({
                'id':item['id'],'durationMillis':1,**score(1)})+'\n' for item in selected))
        with mock.patch.object(cq,'score_requests',side_effect=synthetic_responses),redirect_stdout(io.StringIO()):
            cq.score_run(SimpleNamespace(export=export,output=output,model_config=config,runner=runner,model=model,
                split='calibration',limit=None,expected_model_bytes=model.stat().st_size))
        self.assertEqual(12,len(requests_seen))
        self.assertTrue(all(set(item)=={'id','split','prefix','candidates'} and len(item['candidates'])==7 for item in requests_seen))
        for name in ('run-input.json','complete.json'):
            receipt=json.loads((output/name).read_text())
            self.assertEqual(binding,{key:receipt[key] for key in cq.CORPUS_BINDING_KEYS})
        complete,scores=cq.load_scores(output,cq.requests(records,'calibration'),binding)
        self.assertEqual((12,0),(len(scores),complete['runtimeErrors']))
        # Even with a valid score-file digest, a fabricated measured error count fails.
        (output/'complete.json').write_text(json.dumps({**complete,'runtimeErrors':1}))
        with self.assertRaisesRegex(ValueError,'V5_RUNTIME_ERROR_COUNT'):
            cq.load_scores(output,cq.requests(records,'calibration'),binding)


if __name__=='__main__':unittest.main()
