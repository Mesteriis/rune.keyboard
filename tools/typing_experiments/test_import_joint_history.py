import unittest
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
from holdout_ledger import keys_for
import import_joint_history as importer
import import_joint_source_windows as window_importer
import import_joint_article_segments as segment_importer
import audit_joint_family_closure as family_audit
from import_joint_history import partition_entries
from recover_legacy_families import sha


class Dictionary:
    def analyses(self,word):
        return [SimpleNamespace(lemma='стать'),SimpleNamespace(lemma='сталь')] if word=='стали' else []


class JointHistoryTest(unittest.TestCase):
    def test_article_segments_bind_history_and_refuse_input_drift(self):
        from test_holdout_ledger import ledger
        from import_word_epoch_text_segments import segment_keys
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);corpus='followup-corpus';directory=root/'data'/corpus
            directory.mkdir(parents=True);source=root/'data/0020.parquet';source.write_bytes(b'public')
            files={};parents=[]
            for part,article in [('calibration','123'),('holdout','124')]:
                row=dict(id=part,source='0020.parquet',article=article,split=part,language='ru')
                path=directory/(part+'.jsonl');path.write_text(json.dumps(row)+'\n');files[path.name]=sha(path)
                bindings={f'data/{corpus}/{part}.jsonl':files[path.name]}
                for prefix in ('public-joint-history-','public-joint-source-windows-'):
                    parents.append(dict(id=f'{prefix}{corpus}-{part}',usage='historical-exclusion',rowCount=1,
                        bindings=bindings,keys={'article':sorted(keys_for([row],'article'))},missingAxes=['family','sentence','context']))
            manifest=directory/'manifest.json';manifest.write_text(json.dumps({'files':files}))
            base=ledger(False);base['entries'].extend(parents)
            code=('import_joint_article_segments.py','import_word_epoch_article_segments.py','import_word_epoch_text_segments.py',
                  'import_joint_history.py','holdout_ledger.py','recover_ranker_sources.py','recover_legacy_families.py')
            for name in code:
                target=root/'tools/typing_experiments'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text('fixture')
            def batches(_):return [(['123','124'],['Один. Второй.','Третий.'])]
            with patch.object(segment_importer,'BASE','data'),patch.object(segment_importer,'MANIFESTS',{corpus:sha(manifest)}), \
                 patch.object(segment_importer,'SOURCES',{'data/0020.parquet':sha(source)}):
                result,receipt=segment_importer.build(root,base,batches)
                entry=next(e for e in result['entries'] if e['id']==segment_importer.PREFIX+corpus+'-calibration')
                self.assertEqual(segment_keys('Один. Второй.'),set(entry['keys']['sentence']))
                self.assertEqual(2,receipt['counts'][corpus+'-calibration']['distinctSegments'])
                missing=dict(base,entries=[e for e in base['entries'] if e['id']!='public-joint-source-windows-'+corpus+'-holdout'])
                with self.assertRaisesRegex(ValueError,'JOINT_SEGMENTS_PARENT'):
                    segment_importer.build(root,missing,batches)
                target=directory/'calibration.jsonl';before=target.read_bytes();target.write_bytes(before+b' ')
                with self.assertRaisesRegex(ValueError,'JOINT_SEGMENTS_ROWS_IDENTITY'):
                    segment_importer.build(root,base,batches)
                target.write_bytes(before)
                def drift(_):
                    yield ['123','124'],['Один. Второй.','Третий.']
                    source.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'JOINT_SEGMENTS_INPUT_DRIFT'):
                    segment_importer.build(root,base,drift)

    def test_joint_family_closure_resolves_protected_word_and_checks_all_analyses(self):
        from test_holdout_ledger import ledger
        class Lexicon(Dictionary):
            def receipt(self): return {'dictionaryOnly':True}
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);corpus='followup-corpus';directory=root/'data'/corpus;directory.mkdir(parents=True)
            files={};rows={}
            for part in ('calibration','holdout'):
                rows[part]=[dict(id=part,split=part,language='ru',word='стали',cohort='protected',group='protected',
                                 typed='@стали',expectedSpelling='@стали',noAuto=True)]
                path=directory/(part+'.jsonl');path.write_text(json.dumps(rows[part][0])+'\n');files[path.name]=sha(path)
            manifest=directory/'manifest.json';manifest.write_text(json.dumps({'files':files,'counts':{p:{'rows':1} for p in rows}}))
            manifest_name=f'data/{corpus}/manifest.json';base=ledger(False)
            for part in rows:
                path=f'data/{corpus}/{part}.jsonl';bindings={path:files[part+'.jsonl'],manifest_name:sha(manifest)}
                base['entries'].extend([
                    dict(id=f'public-joint-history-{corpus}-{part}',usage='historical-exclusion',rowCount=1,bindings=bindings,
                         keys={'article':['a'*64]},missingAxes=['family','sentence','context']),
                    dict(id=f'public-joint-history-{corpus}-{part}-families',usage='historical-family-exclusion',bindings=bindings,
                         keys={'family':sorted(keys_for([dict(families=['стать','сталь'])],'family'))},missingAxes=[]),
                    dict(id=f'public-joint-source-windows-{corpus}-{part}',usage='historical-source-exclusion',bindings=bindings,
                         keys={'article':['a'*64],'sentence':['b'*64]},missingAxes=[])])
            with patch.object(family_audit,'BASE','data'), patch.object(family_audit,'MANIFESTS',{corpus:sha(manifest)}):
                history={corpus+'/'+part:{'unresolvedRows':[part]} for part in rows}
                receipt=family_audit.audit(root,base,Lexicon(),history)
                self.assertEqual(1,receipt['counts'][corpus+'/calibration']['protectedRows'])
                self.assertEqual(0,receipt['counts'][corpus+'/calibration']['unresolvedRows'])
                history[corpus+'/calibration']['unresolvedRows']=[]
                with self.assertRaisesRegex(ValueError,'JOINT_FAMILY_HISTORICAL_MISMATCH'):
                    family_audit.audit(root,base,Lexicon(),history)
                target=next(e for e in base['entries'] if e['id'].endswith('calibration-families'))
                target['keys']['family'].pop()
                with self.assertRaisesRegex(ValueError,'JOINT_FAMILY_INCOMPLETE'):
                    family_audit.audit(root,base,Lexicon())
                (directory/'calibration.jsonl').write_text('{}\n')
                with self.assertRaisesRegex(ValueError,'JOINT_FAMILY_BINDING'):
                    family_audit.audit(root,base,Lexicon())

    def test_source_window_import_binds_inputs_and_refuses_source_drift(self):
        from test_holdout_ledger import ledger
        class Generator:
            @staticmethod
            def bounded_prefix(text): return text
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);corpus='followup-corpus';directory=root/'data'/corpus
            directory.mkdir(parents=True);source=root/'data/0020.parquet';source.write_bytes(b'public')
            files={};parents=[];rows_by_part={}
            for part,article in [('calibration','123'),('holdout','124')]:
                row=dict(id=part,source='0020.parquet',article=article,split=part,language='ru',word='стали',prefix='Они')
                path=directory/(part+'.jsonl');path.write_text(json.dumps(row)+'\n');files[path.name]=sha(path);rows_by_part[part]=row
            manifest=directory/'manifest.json';manifest.write_text(json.dumps({'files':files,'counts':{p:{'rows':1} for p in rows_by_part}}))
            source_name='data/0020.parquet';manifest_name=f'data/{corpus}/manifest.json'
            for part in rows_by_part:
                path=f'data/{corpus}/{part}.jsonl'
                parents.append(dict(id=f'public-joint-history-{corpus}-{part}',usage='historical-exclusion',rowCount=1,
                    bindings={path:files[part+'.jsonl'],manifest_name:sha(manifest),source_name:sha(source)},
                    keys={'article':sorted(keys_for([rows_by_part[part]],'article'))},missingAxes=['family','sentence','context']))
            base=ledger(False);base['entries'].extend(parents)
            for path in ('tools/typing_experiments/import_joint_source_windows.py','tools/typing_experiments/import_legacy_context_history.py',
                         'tools/typing_experiments/recover_legacy_holdout.py','tools/typing_experiments/right_context_sentence_audit.py'):
                target=root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_text('fixture')
            batches=lambda _: [(['123','124'],['Они стали здесь.','Они стали там.'])]
            with patch.object(window_importer,'BASE','data'), patch.object(window_importer,'MANIFESTS',{corpus:sha(manifest)}), \
                 patch.object(window_importer,'SOURCES',{source_name:sha(source)}), patch.object(window_importer,'load_generator',return_value=Generator()):
                result,receipt=window_importer.build(root,base,batches)
                self.assertEqual(2,len([e for e in result['entries'] if e['id'].startswith(window_importer.PREFIX)]))
                self.assertEqual(1,receipt['counts'][corpus+'/calibration']['windows'])
                def drift(_):
                    yield ['123','124'],['Они стали здесь.','Они стали там.']
                    source.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'JOINT_WINDOWS_INPUT_DRIFT'):
                    window_importer.build(root,base,drift)
                source.write_bytes(b'public')
                source.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'JOINT_WINDOWS_SOURCE_HASH'):
                    window_importer.build(root,base,batches)

    def entries(self,part='train',**changes):
        rows=[dict(id='r',source='source.parquet',article='123',split=part,language='ru',
                   family='999999',prefix='Они',typed='стмли',expectedSpelling='стали')|changes]
        return partition_entries('corpus',part,rows,1,'source.parquet',{'123'},Dictionary(),{'manifest':'a'*64})

    def test_article_and_typo_independent_context_are_imported(self):
        entries,_=self.entries()
        self.assertEqual(keys_for([dict(article='123')],'article'),set(entries[0]['keys']['article']))
        self.assertEqual(keys_for([dict(prefix='Они',typed='иная',expectedSpelling='стали')],'context'),set(entries[0]['keys']['context']))

    def test_native_numeric_ids_are_never_imported_as_canonical_lemmas(self):
        entries,_=self.entries()
        self.assertEqual(keys_for([dict(families=['стать','сталь'])],'family'),set(entries[1]['keys']['family']))
        self.assertEqual('supervised',entries[1]['usage'])
        self.assertEqual('historical-family-exclusion',self.entries('holdout')[0][1]['usage'])

    def test_unknown_targets_remain_pending_and_correct_controls_keep_target(self):
        entries,counts=self.entries(expectedSpelling='неизвестно')
        self.assertEqual(1,len(entries));self.assertEqual(['r'],counts['unresolvedRows'])
        self.assertIn('family',entries[0]['missingAxes'])
        self.assertEqual(1,self.entries(cohort='correct',typed='стали')[1]['resolvedRows'])

    def test_changed_source_article_partition_language_id_count_and_target_fail(self):
        for changes in (dict(source='other'),dict(article='124'),dict(split='holdout'),dict(language='en'),dict(id=None),dict(expectedSpelling=None)):
            with self.assertRaises(ValueError):self.entries(**changes)
        with self.assertRaisesRegex(ValueError,'ROW_COUNT'):
            partition_entries('corpus','train',[],1,'source.parquet',{'123'},Dictionary(),{'manifest':'a'*64})

    def test_changed_public_source_bytes_are_rejected_before_reading_articles(self):
        from test_holdout_ledger import ledger
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'source.parquet').write_bytes(b'changed')
            with patch.object(importer,'SOURCES',{'source.parquet':'0'*64}):
                with self.assertRaisesRegex(ValueError,'PUBLIC_SOURCE_IDENTITY'):
                    importer.build(Path(folder),ledger(False),Dictionary(),lambda _:self.fail('unverified source read'))

    def test_archived_joint_builder_hashes_match_their_manifest(self):
        directory=Path(__file__).with_name('frozen_sources')
        sources=json.loads((directory/'manifest.json').read_text())['sources']
        for digest in ('cfa5777d2a2ac53ffb339aa56b34d57c4a4a6a0ec1a712b1867b857d85043728',
                       'b9cc4859e08021f851711bcabff12d329d6219312d3d988157b9716a1af574b6'):
            self.assertEqual(digest,sha(directory/sources[digest]['file']))


if __name__=='__main__':unittest.main()
