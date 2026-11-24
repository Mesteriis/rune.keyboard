import unittest
import base64
import bz2
import hashlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
from copy import deepcopy
from local_spelling_stress import audit, cases, percentile, restore_source_ids, variants
import chat_corpus
import chat_corpus_report
import chat_corpus_dictionary_audit
import chat_control_review
import chat_guard_experiment
import chat_guard_extended_corpus
import chat_guard_extended_compare
from holdout_ledger import keys_for


class LocalSpellingStressTest(unittest.TestCase):
    def test_punctuation_checks_actual_boundary_change_and_undo(self):
        row, obs = self.fixture()
        for boundary in ('.', ':'):
            sample = deepcopy(obs)
            sample.pop('boundaryChangedBeyondInsertedSpace')
            sample.update(boundary=boundary, afterBoundary={'text': 'домой' + boundary},
                          boundaryChangedBeyondInsertion=True, afterBackspace={'text': 'ддмой'})
            self.assertEqual(1, audit([row], [sample], boundary)['slices']['all']['correct'])
            for corruption in ({'boundary': ' '}, {'boundaryChangedBeyondInsertion': False},
                               {'afterBackspace': {'text': 'домой'}}):
                with self.assertRaises(ValueError): audit([row], [sample | corruption], boundary)
            failed = sample | {'afterBackspace': {'text': 'домой'}, 'restoredBeforeBoundaryExactly': False}
            self.assertEqual(1, audit([row], [failed], boundary)['slices']['all']['undoFailures'])

    def test_current_product_identity_map_fails_closed(self):
        row, obs = self.fixture()
        identity = {'index': 0, 'id': 'replay-00000000', 'sourceId': 'one'}
        mapped = restore_source_ids([row], [obs | {'id': identity['id']}], [identity])
        self.assertEqual('one', mapped[0]['id'])
        for broken in ({**identity, 'sourceId': 'wrong'}, {**identity, 'index': 1},
                       {**identity, 'id': 'foreign'}):
            with self.assertRaises(ValueError):
                restore_source_ids([row], [obs | {'id': identity['id']}], [broken])
        with self.assertRaises(ValueError): restore_source_ids([row], [obs], [])

    def test_extended_overlay_comparison_reports_candidate_and_boundary_drift(self):
        rows=[];baseline=[];overlay=[]
        for profile,count in [('product-replay-v1',720),('product-replay-history-v1',4000),('reviewed',8)]:
            for _ in range(count):
                index=len(rows);row=dict(id=f'case-{index}',sourceProfile=profile,split='holdout',language='ru',prefix='ну',typed='слово')
                obs=dict(id=row['id'],index=index,status='COMPLETE',split='holdout',language='ru',prefix='ну',typed='слово',
                         afterBoundary={'text':'ну слово '},candidateView={'candidates':[]})
                rows.append(row);baseline.append(obs);overlay.append(obs|{'id':f'joint-replay-{index:08d}'})
        overlay[0]=overlay[0]|{'candidateView':{'candidates':['иная']}}
        overlay[-1]=overlay[-1]|{'afterBoundary':{'text':'ну другое '}}
        result=chat_guard_extended_compare.compare(rows,baseline,overlay)
        self.assertEqual(1,result['counts']['product-replay-v1DifferentRows'])
        self.assertEqual(1,result['differentFields']['product-replay-v1:candidateView'])
        self.assertEqual(1,result['counts']['reviewedDifferentBoundaryTexts'])
        with self.assertRaisesRegex(ValueError,'EXTENDED_COMPARE_COUNT'):
            chat_guard_extended_compare.compare(rows,baseline,overlay[:-1])

    def test_extended_chat_guard_inputs_do_not_invent_correctness_labels(self):
        review=dict(purpose='POSTHOC_DISCLOSED_REGRESSION_NOT_QUALIFICATION',cases=[
            dict(id=f'case-{i}',label='preserve') for i in range(8)])
        reviewed=[dict(id=f'case-{i}',cohort='correct',noAuto=True) for i in range(8)]
        projections=[dict(id='sample',status='COMPLETE',language='ru',split='holdout',prefix='мы',typed='слово'),
                     dict(id='english',status='COMPLETE',language='en',split='holdout',prefix='',typed='word')]
        rows,counts=chat_guard_extended_corpus.assemble([('fixture',projections)],review,reviewed)
        self.assertEqual({'fixture':1,'reviewed':8},counts)
        self.assertEqual('unlabeled',rows[0]['cohort'])
        self.assertEqual(rows[0]['typed'],rows[0]['expectedSpelling'])
        with self.assertRaisesRegex(ValueError,'EXTENDED_IDENTITIES'):
            chat_guard_extended_corpus.assemble([('fixture',projections)],review,reviewed[:-1])

    def test_chat_guard_overlay_is_scoped_and_rejects_unsafe_or_ambiguous_input(self):
        source='before\n'+chat_guard_experiment.MARKER+'after\n'
        changed=chat_guard_experiment.overlay(source,['админку','токсиков'])
        self.assertIn('setOf("админку", "токсиков")',changed)
        self.assertIn('else baseRareWords.lookup(key)',changed)
        for words in ([],['токсиков','админку'],['админку','админку'],['слово";code']):
            with self.assertRaisesRegex(ValueError,'CHAT_OVERLAY_WORDS'):
                chat_guard_experiment.overlay(source,words)
        with self.assertRaisesRegex(ValueError,'CHAT_OVERLAY_SOURCE'):
            chat_guard_experiment.overlay(source+chat_guard_experiment.MARKER,['админку'])

    def test_chat_guard_comparison_counts_preservation_and_checks_editor_flags(self):
        row=dict(id='public',split='holdout',language='ru',prefix='выдай',typed='админку',
                 expectedSpelling='админку',cohort='correct')
        common=dict(index=0,status='COMPLETE',split='holdout',language='ru',prefix='выдай',typed='админку',
                    beforeBoundary={'text':'выдай админку'},restoredBeforeBoundaryExactly=True)
        baseline=common|dict(id='public',afterBoundary={'text':'выдай спинку '},boundaryChangedBeyondInsertedSpace=True)
        updated=common|dict(id='joint-replay-00000000',afterBoundary={'text':'выдай админку '},boundaryChangedBeyondInsertedSpace=False)
        review={'cases':[dict(id='public',label='preserve')]}
        with tempfile.TemporaryDirectory() as folder:
            old=Path(folder)/'old';new=Path(folder)/'new'
            old.write_text(json.dumps(baseline)+'\n');new.write_text(json.dumps(updated)+'\n')
            counts=chat_guard_experiment.summarize([row],old,new,review)
            self.assertEqual((1,1,0),(counts['reviewedRows'],counts['reviewedPreserved'],counts['overlayControlChanges']))
            new.write_text(json.dumps(updated|{'boundaryChangedBeyondInsertedSpace':True})+'\n')
            with self.assertRaisesRegex(ValueError,'CHAT_OVERLAY_EDITOR'):
                chat_guard_experiment.summarize([row],old,new,review)

    def test_posthoc_chat_control_review_rejects_missing_and_mismatched_baselines(self):
        row=dict(id='one',typed='админку',prefix='выдай',expectedSpelling='админку',cohort='correct',
                 noAuto=True,edit_kind='control')
        obs=dict(id='one',typed='админку',prefix='выдай',status='COMPLETE',beforeBoundary={'text':'выдай админку'},
                 afterBoundary={'text':'выдай спинку '},boundaryChangedBeyondInsertedSpace=True,restoredBeforeBoundaryExactly=True)
        review=dict(schema=1,purpose='POSTHOC_DISCLOSED_REGRESSION_NOT_QUALIFICATION',cases=[
            dict(id='one',typed='админку',baseline='спинку',label='preserve')])
        report=chat_control_review.audit([row],[obs],review)
        self.assertEqual({'preserve':1},report['counts'])
        self.assertIs(False,report['independentQualification'])
        self.assertEqual(['one'],chat_control_review.compare([row],[obs],review)['failureIds'])
        retained=obs|dict(afterBoundary={'text':'выдай админку '},boundaryChangedBeyondInsertedSpace=False)
        self.assertEqual(1,chat_control_review.compare([row],[retained],review)['preserved'])
        from test_holdout_ledger import ledger
        article_row=row|dict(sourceRepository='tatoeba',language='ru',article='tatoeba:123')
        data=ledger(False)
        with self.assertRaisesRegex(ValueError,'CHAT_REVIEW_SOURCE_NOT_EXCLUDED'):
            chat_control_review.verify_exclusions([article_row],review,data)
        data['entries'][0]['keys']['article']=sorted(keys_for([article_row],'article'))
        chat_control_review.verify_exclusions([article_row],review,data)
        changed=deepcopy(review);changed['cases'][0]['baseline']='другое'
        with self.assertRaisesRegex(ValueError,'CHAT_REVIEW_BASELINE'):
            chat_control_review.audit([row],[obs],changed)
        changed=deepcopy(review);changed['cases'][0]['id']='absent'
        with self.assertRaisesRegex(ValueError,'CHAT_REVIEW_MISSING'):
            chat_control_review.audit([row],[obs],changed)
        second=row|dict(id='two');second_obs=obs|dict(id='two')
        with self.assertRaisesRegex(ValueError,'CHAT_REVIEW_INCOMPLETE'):
            chat_control_review.audit([row,second],[obs,second_obs],review)

    def test_chat_builder_binds_public_source_and_keeps_labels_out_of_inputs(self):
        from test_holdout_ledger import ledger
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();source=root/'source.bz2'
            source.write_bytes(bz2.compress('123\trus\tОн учится.\tauthor\n'.encode()))
            lock=root/'lock.json';lock.write_text(json.dumps(dict(url=chat_corpus.URL,license='CC0-1.0',
                compressedSha256=hashlib.sha256(source.read_bytes()).hexdigest())))
            data=ledger(False);data['entries'][0]['keys']['article']=sorted(keys_for([
                dict(sourceRepository='tatoeba',language='ru',article='tatoeba:123')],'article'))
            ledger_path=root/'ledger.json';ledger_path.write_text(json.dumps(data))
            with patch.object(chat_corpus,'ROOT',root),patch.object(chat_corpus,'CC0_LOCK_SHA',hashlib.sha256(lock.read_bytes()).hexdigest()):
                output=root/'build/corpus';manifest=chat_corpus.run(source,lock,ledger_path,output)
                rows=[json.loads(line) for line in (output/'rows.jsonl').read_text().splitlines()]
                inputs=(output/'inputs.tsv').read_text().splitlines()
                self.assertEqual(len(rows),len(inputs))
                self.assertIs(False,manifest['independentQualification'])
                self.assertIn('unverified source spelling',manifest['controlGroundTruth'])
                for row,line in zip(rows,inputs,strict=True):
                    fields=line.split('\t');self.assertEqual(6,len(fields))
                    self.assertEqual(row['typed'],base64.b64decode(fields[5]).decode())
                    self.assertNotIn(row['edit_kind'],line)
                source.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'CHAT_SOURCE_IDENTITY'):
                    chat_corpus.run(source,lock,ledger_path,root/'build/refused')
                self.assertFalse((root/'build/refused').exists())

    def test_chat_report_counts_correlated_controls_once_and_keeps_case_changes(self):
        row=dict(id='one',typed='слово',prefix='ну',expectedSpelling='слово',cohort='correct',noAuto=True,
                 language='ru',register='chat-shaped-lowercase',purpose='DISCLOSED_REGRESSION_NOT_QUALIFICATION',
                 clusterId='tatoeba:1',edit_kind='control')
        obs=dict(id='one',typed='слово',prefix='ну',status='COMPLETE',beforeBoundary={'text':'ну слово'},
                 afterBoundary={'text':'ну Слово '},boundaryChangedBeyondInsertedSpace=True,restoredBeforeBoundaryExactly=True)
        second=row|dict(id='two');second_obs=obs|dict(id='two',afterBoundary={'text':'ну слово '},boundaryChangedBeyondInsertedSpace=False)
        result=chat_corpus_report.report([row,second],[obs,second_obs])
        self.assertEqual((1,2),(result['controlRows']['changed'],result['controlRows']['total']))
        self.assertEqual((1,1),(result['controlClusters']['changed'],result['controlClusters']['total']))
        self.assertEqual(1,result['overall']['caseOnlyChanges'])
        self.assertIs(False,result['independentQualification'])
        self.assertTrue(any('not independently verified' in caveat for caveat in result['caveats']))
        class Lexicon:
            def analyses(self,word): return [object()] if word=='слово' else []
        dictionary=chat_corpus_dictionary_audit.audit([row,second],[obs,second_obs],Lexicon())
        self.assertEqual(1,dictionary['counts']['dictionary_known_case_only'])
        self.assertEqual(1,dictionary['counts']['dictionary_known_unchanged'])
        self.assertIn('not evidence',dictionary['caveat'])
        with self.assertRaisesRegex(ValueError,'CHAT_COHORT'):
            chat_corpus_report.report([row|dict(noAuto=False)],[obs])
        self.assertAlmostEqual(0.7934506856,chat_corpus_report.wilson(0,1)['upper'])

    def test_public_chat_regression_is_deterministic_and_excludes_unregistered_articles(self):
        lines=['10\trus\tОн учится.\towner\n','11\trus\tты вернёшься!\towner\n',
               '12\trus\tэто, пунктуация\towner\n']
        excluded=keys_for([dict(sourceRepository='tatoeba',language='ru',article='tatoeba:10')],'article')
        rows,counts=chat_corpus.generate(lines,excluded)
        self.assertEqual((rows,counts),chat_corpus.generate(lines,excluded))
        self.assertEqual(2,counts['eligibleSentences'])
        self.assertEqual(1,counts['unregisteredExcluded'])
        self.assertTrue(all(row['article']=='tatoeba:10' and row['language']=='ru' for row in rows))
        self.assertTrue(all(row['purpose']=='DISCLOSED_REGRESSION_NOT_QUALIFICATION' for row in rows))
        self.assertTrue(any(row['edit_kind']=='reflexive_suffix' for row in rows))
        self.assertTrue(any(row['edit_kind']=='double_consonant' for row in rows))
        self.assertEqual(len(rows),len({row['id'] for row in rows}))
        with self.assertRaisesRegex(ValueError,'CHAT_SOURCE_DUPLICATE'):
            chat_corpus.generate(lines+[lines[0]],excluded)
        with self.assertRaisesRegex(ValueError,'CHAT_SOURCE_ROW'):
            chat_corpus.generate(['bad\n'],excluded)

    def fixture(self):
        row = dict(id='one', typed='ддмой', prefix='', expectedSpelling='домой',
                   cohort='typo', noAuto=False, family='neighbour')
        obs = dict(id='one', typed='ддмой', prefix='', status='COMPLETE',
                   beforeBoundary={'text': 'ддмой'}, afterBoundary={'text': 'домой '},
                   boundaryChangedBeyondInsertedSpace=True, restoredBeforeBoundaryExactly=True,
                   hostStageNanos={'baselineSearch': 2_000_000})
        return row, obs

    def test_deterministic_unique_cases_cover_edits_and_controls(self):
        rows = cases()
        self.assertEqual(rows, cases())
        self.assertEqual(len(rows), len({row['id'] for row in rows}))
        self.assertEqual({'missing', 'repeated', 'transposed', 'neighbour', 'control'},
                         {row['family'] for row in rows})
        self.assertTrue(all(row['typed'] for row in rows))
        self.assertTrue(all(row['noAuto'] for row in rows if row['family'] == 'control'))
        self.assertIn('Анна', [row['typed'] for row in rows])

    def test_variants_preserve_edit_intent_and_deduplicate(self):
        values = list(variants('мама'))
        self.assertEqual(len(values), len({text for _, text in values}))
        self.assertNotIn('мама', [text for _, text in values])
        self.assertIn(('missing', 'ама'), values)
        self.assertIn(('repeated', 'ммама'), values)
        self.assertIn(('transposed', 'амма'), values)
        self.assertIn(('neighbour', 'иама'), values)

    def test_report_success_and_exact_undo(self):
        row, obs = self.fixture()
        report = audit([row], [obs])
        self.assertEqual(1, report['slices']['all']['correct'])
        self.assertEqual([], report['unintendedSpellingChanges'])
        self.assertEqual(2.0, report['hostTimingMs']['baselineSearch']['p95'])
        obs['restoredBeforeBoundaryExactly'] = False
        self.assertEqual(1, audit([row], [obs])['slices']['all']['undoFailures'])

    def test_valid_original_abstention_not_invented_callback(self):
        row, obs = self.fixture()
        obs.update(afterBoundary={'text': 'ддмой '}, boundaryChangedBeyondInsertedSpace=False,
                   actualRequestGeneration={'isValidWord': True})
        report = audit([row], [obs])
        self.assertEqual({'rows': 1, 'retained': 1, 'caseOnlyChanges': 0, 'spellingChanges': 0}, report['dictionaryValidSyntheticTypos'])
        self.assertEqual({'VALID_ORIGINAL': 1}, report['automaticAbstentions'])
        obs['actualRequestGeneration'] = {}
        self.assertEqual({'NO_ADMISSION_CALLBACK': 1}, audit([row], [obs])['automaticAbstentions'])

    def test_wrong_replacement_and_control_are_failures(self):
        row, obs = self.fixture()
        obs['afterBoundary']['text'] = 'думаю '
        self.assertEqual(1, len(audit([row], [obs])['unintendedSpellingChanges']))
        row.update(cohort='correct', noAuto=True, expectedSpelling='ддмой', family='control')
        self.assertEqual(1, audit([row], [obs])['slices']['all']['controlChanges'])

    def test_case_only_departure_is_not_a_spelling_substitution(self):
        row, obs = self.fixture()
        obs['afterBoundary']['text'] = 'Ддмой '
        report = audit([row], [obs])
        self.assertEqual([], report['unintendedSpellingChanges'])
        self.assertEqual(1, len(report['caseOnlyDepartures']))
        self.assertEqual(0, report['slices']['all']['correct'])
        row.update(cohort='correct', noAuto=True, expectedSpelling='ддмой', family='control')
        report = audit([row], [obs])
        self.assertEqual(1, report['slices']['all']['controlChanges'])
        self.assertEqual('Ддмой ', report['caseOnlyDepartures'][0]['actual'])

    def test_corruption_or_partial_timings_fail_closed(self):
        row, obs = self.fixture()
        for changes in [dict(id='other'), dict(status='ERROR'), dict(hostStageNanos={'a': -1})]:
            altered = deepcopy(obs); altered.update(changes)
            with self.assertRaises(ValueError): audit([row], [altered])
        row2 = dict(row, id='two'); obs2 = dict(obs, id='two', hostStageNanos={})
        with self.assertRaises(ValueError): audit([row, row2], [obs, obs2])

    def test_nearest_rank_percentiles(self):
        self.assertEqual(3, percentile([5, 1, 3, 2, 4], .5))
        self.assertEqual(5, percentile([5, 1, 3, 2, 4], .95))
