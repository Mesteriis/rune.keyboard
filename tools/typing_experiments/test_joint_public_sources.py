import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType,SimpleNamespace
import unittest
from unittest.mock import patch
import joint_public_sources as sources


class JointPublicSourcesTest(unittest.TestCase):
    def test_shared_joint_token_guard_rejects_partial_source_tokens(self):
        import prepare_joint_correction as joint
        for text in ('слово-часть', 'слово\u0301', 'слово\u200dчасть', 'слово’часть'):
            with self.subTest(text=text):
                match = joint.WORDS.search(text)
                self.assertIsNotNone(match)
                self.assertFalse(joint.source_token_is_whole(text, match, {}))
                self.assertTrue(joint.source_token_is_whole(text, match, None))
        text = 'слово отдельно'
        self.assertTrue(joint.source_token_is_whole(text, joint.WORDS.search(text), {}))

    def test_joint_collector_persists_checked_rows_and_refuses_source_drift(self):
        import prepare_joint_correction as joint
        class Generator:
            @staticmethod
            def bounded_prefix(value): return value
        dictionary_state = {'version': 1}
        class Lexicon:
            def __init__(self,cache_size): pass
            def analyses(self,word): return [SimpleNamespace(lemma=word)]
            def receipt(self): return {'version': dictionary_state['version']}
        class Column:
            def __init__(self,values): self.values=values
            def to_pylist(self): return self.values
        class Batch:
            def __init__(self,article,text): self.values=([article],[text])
            def column(self,index): return Column(self.values[index])
        texts={'ru-0011.parquet':('1','один два три четыре первый конец'),
               '0018.parquet':('2','один два три четыре второй конец'),
               '0019.parquet':('3','один два три четыре третий конец')}
        class ParquetFile:
            def __init__(self,path): self.name=Path(path).name
            def iter_batches(self,**kwargs): yield Batch(*texts[self.name])
        fake_arrow=ModuleType('pyarrow');fake_parquet=ModuleType('pyarrow.parquet');fake_parquet.ParquetFile=ParquetFile
        fake_arrow.parquet=fake_parquet;fake_ranker=ModuleType('ranker');fake_ranker.PymorphyLexicon=Lexicon
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();source_root=root/'build/joint';source_root.mkdir(parents=True)
            def put(name,data):
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);return target
            frequency=put('build/smart-typing-0.3/corpus-inputs/ru_50k.txt','первый 1\nвторой 1\nтретий 1\n'.encode())
            morph=put('app/src/main/assets/smarttyping/lexicon/ru.morph',b'morph')
            for name in ('tools/morphology/ranker.py','tools/typing_experiments/joint_exclusion_inputs.py',
                         'tools/typing_experiments/right_context_sentence_audit.py'):
                put(name,b'fixture')
            fake_ranker.__file__ = str(root/'tools/morphology/ranker.py')
            train=put('build/typing-ranker-v2/ru-0011.parquet',b'train')
            paths={'0018.parquet':put('build/joint/0018.parquet',b'calibration'),
                   '0019.parquet':put('build/joint/0019.parquet',b'holdout')}
            digest=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
            source_hashes={'build/typing-ranker-v2/ru-0011.parquet':digest(train),
                           **{sources.BASE+'/'+name:digest(path) for name,path in paths.items()}}
            lock={'repository':sources.REPOSITORY,'revision':sources.REVISION,'files':[
                {'path':'20231101.ru/train/'+name,'size':path.stat().st_size,'lfs':{'oid':digest(path)}} for name,path in paths.items()]}
            (source_root/'public-source-lock.json').write_text(json.dumps(lock))
            put('build/typing-ranker-v2/external-holdout-v6-ru0011/manifest.json',
                json.dumps({'source':{'sha256':digest(train),'bytes':train.stat().st_size}}).encode())
            def make_rows(pool,part,known):
                return [dict(items[0],id='row-'+part,split=part,language='ru',cohort='correct',
                             typed=items[0]['word'],expectedSpelling=items[0]['word'],noAuto=True,group='correct',band='long')
                        for items in pool.values()]
            def finish(snapshot,rows):
                self.assertEqual(3,len(rows))
                self.assertTrue(all(r['families']==[r['word']] and len(r['contextHash'])==64 for r in rows))
                return {'scope':'synthetic-test','historicalReproduction':False,'independentQualification':False}
            actual_snapshot=sources.snapshot
            def synthetic_snapshot(paths):
                paths=dict(paths)
                if 'morphology' in paths: paths['morphology']=(morph,digest(morph))
                return actual_snapshot(paths)
            modules={'pyarrow':fake_arrow,'pyarrow.parquet':fake_parquet,'ranker':fake_ranker}
            with patch.dict(sys.modules,modules),patch.object(sys,'path',sys.path[:]),patch.object(joint,'ROOT',root),patch.object(joint,'GENERATOR',Generator()), \
                 patch.object(joint,'morphology',return_value={'первый':'1','второй':'2','третий':'3'}), \
                 patch.object(joint,'partition',side_effect={'1':'train','2':'calibration','3':'holdout'}.get), \
                 patch.object(joint,'rows_from_pool',side_effect=make_rows),patch.object(joint.common,'FREQUENCY_SHA256',digest(frequency)), \
                 patch.object(sources,'SOURCES',source_hashes),patch.object(sources,'snapshot',side_effect=synthetic_snapshot), \
                 patch.object(joint.registry_guard,'begin',return_value={'synthetic':True}), \
                 patch.object(joint.registry_guard,'finish',side_effect=finish) as guard:
                output=root/'build/complete';joint.prepare(source_root,output)
                manifest=json.loads((output/'manifest.json').read_text())
                self.assertIs(False,manifest['containsPersonalMessages'])
                self.assertIs(False,manifest['independentQualification'])
                self.assertEqual(7,len(manifest['publicInputSha256']))
                self.assertIn('ranker.py', manifest['collectorHelperSha256'])
                for part in ('train','calibration','holdout'):
                    row=json.loads((output/(part+'.jsonl')).read_text())
                    self.assertEqual([row['word']],row['families'])
                texts['ru-0011.parquet'] = ('1', 'один два три четыре первый-часть конец')
                partial = root/'build/partial'
                with self.assertRaisesRegex(ValueError, 'JOINT_CANONICAL_SPLIT'):
                    joint.prepare(source_root, partial)
                self.assertFalse(partial.exists())
                texts['ru-0011.parquet'] = ('1', 'один два три четыре первый конец')
                def dictionary_drift(snapshot,rows):
                    result=finish(snapshot,rows);dictionary_state['version']=2;return result
                guard.side_effect=dictionary_drift;failed=root/'build/dictionary-drift'
                with self.assertRaisesRegex(ValueError,'JOINT_DICTIONARY_DRIFT'):
                    joint.prepare(source_root,failed)
                self.assertFalse(failed.exists())
                dictionary_state['version']=1
                def helper_drift(snapshot,rows):
                    result=finish(snapshot,rows);(root/'tools/morphology/ranker.py').write_bytes(b'changed');return result
                guard.side_effect=helper_drift;failed=root/'build/helper-drift'
                with self.assertRaisesRegex(ValueError,'JOINT_PUBLIC_INPUT_DRIFT'):
                    joint.prepare(source_root,failed)
                self.assertFalse(failed.exists())
                (root/'tools/morphology/ranker.py').write_bytes(b'fixture')
                def drift(snapshot,rows):
                    result=finish(snapshot,rows);train.write_bytes(b'changed');return result
                guard.side_effect=drift;failed=root/'build/drift'
                with self.assertRaisesRegex(ValueError,'JOINT_PUBLIC_INPUT_DRIFT'):
                    joint.prepare(source_root,failed)
                self.assertFalse(failed.exists())

    def test_followup_collector_excludes_partial_source_token_before_selection(self):
        import prepare_joint_followup as followup
        import prepare_joint_correction as joint
        from unittest.mock import patch
        class Column:
            def __init__(self, values): self.values = values
            def to_pylist(self): return self.values
        text = ['один два три четыре первый-часть конец']
        article = next(str(i) for i in range(1, 100)
                       if hashlib.sha256(('joint-followup:'+str(i)).encode()).digest()[0] < 128)
        class Batch:
            def column(self, index): return Column([article] if index == 0 else text)
        parquet = ModuleType('pyarrow.parquet')
        parquet.ParquetFile = lambda path: SimpleNamespace(iter_batches=lambda **kwargs: [Batch()])
        arrow = ModuleType('pyarrow'); arrow.parquet = parquet
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve(); source_root = root/'build/joint'; source_root.mkdir(parents=True)
            def put(name, raw):
                path = root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw); return path
            source = put('build/joint/0020.parquet', b'source')
            frequency = put('build/smart-typing-0.3/corpus-inputs/ru_50k.txt', 'первый 1\n'.encode())
            morph = put('app/src/main/assets/smarttyping/lexicon/ru.morph', b'morph')
            sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
            lock = {'files': [{'path':'20231101.ru/train/0020.parquet', 'size':source.stat().st_size,
                               'lfs':{'oid':sha(source)}}]}
            (source_root/'followup-source-lock.json').write_text(json.dumps(lock))
            prior = {'families':set(), 'articles':set(), 'manifestSha256':'a'*64}
            actual_snapshot = sources.snapshot
            def synthetic_snapshot(paths):
                paths = dict(paths); paths['morphology'] = (morph, sha(morph))
                return actual_snapshot(paths)
            observed = []
            def inspect_pool(pool, part, known):
                observed.append((part, list(pool)))
                raise ValueError('FOLLOWUP_POOL_CHECKED')
            with patch.dict(sys.modules, {'pyarrow':arrow, 'pyarrow.parquet':parquet}), \
                 patch.object(joint, 'ROOT', root), patch.object(joint, 'morphology', return_value={'первый':'1'}), \
                 patch.object(joint, 'partition', return_value='calibration'), \
                 patch.object(joint, 'independent_resources', return_value=({}, None, {})), \
                 patch.object(joint, 'rows_from_pool', side_effect=inspect_pool), \
                 patch.object(joint.common, 'FREQUENCY_SHA256', sha(frequency)), \
                 patch.object(sources, 'validate_lock'), \
                 patch.object(sources, 'SOURCES', {sources.BASE+'/0020.parquet':sha(source)}), \
                 patch.object(sources, 'snapshot', side_effect=synthetic_snapshot), \
                 patch.object(followup.exclusion_inputs, 'capture', return_value=prior), \
                 patch.object(followup.exclusion_inputs, 'verify_registered', return_value={}), \
                 patch.object(followup.exclusion_inputs, 'verify_public_origin', return_value='fixture'), \
                 patch.object(followup.registry_guard, 'begin', return_value={'synthetic':True, 'lexical':{}}):
                for value, expected in (('один два три четыре первый-часть конец', []),
                                        ('один два три четыре первый конец', ['1'])):
                    text[0] = value; observed.clear()
                    output = root/'build/out'
                    with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'FOLLOWUP_POOL_CHECKED'):
                        followup.prepare(source_root, output)
                    self.assertEqual(('calibration', expected), observed[0])
                    self.assertFalse(output.exists())

    def test_public_input_snapshot_rejects_wrong_identity_and_mid_run_drift(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source';path.write_bytes(b'public')
            digest=hashlib.sha256(b'public').hexdigest()
            captured=sources.snapshot({'source':(path,digest)})
            sources.verify(captured)
            with self.assertRaisesRegex(ValueError,'JOINT_PUBLIC_INPUT_IDENTITY'):
                sources.snapshot({'source':(path,'a'*64)})
            path.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'JOINT_PUBLIC_INPUT_DRIFT'):
                sources.verify(captured)

    def test_untrusted_lock_cannot_substitute_a_shard_revision_or_duplicate(self):
        entry={'path':'20231101.ru/train/0018.parquet','size':10,'lfs':{'oid':sources.SOURCES[sources.BASE+'/0018.parquet']}}
        lock={'repository':sources.REPOSITORY,'revision':sources.REVISION,'files':[entry]}
        sources.validate_lock(lock,('0018.parquet',))
        for mutate in ('revision','digest','duplicate','size','path'):
            value=copy.deepcopy(lock)
            if mutate=='revision':value['revision']='other'
            elif mutate=='digest':value['files'][0]['lfs']['oid']='a'*64
            elif mutate=='duplicate':value['files'].append(copy.deepcopy(value['files'][0]))
            elif mutate=='size':value['files'][0]['size']=True
            else:value['files'][0]['path']='other/0018.parquet'
            with self.subTest(mutate=mutate),self.assertRaisesRegex(ValueError,'JOINT_PUBLIC_SOURCE_LOCK'):
                sources.validate_lock(value,('0018.parquet',))

    def test_training_shard_requires_retained_identity(self):
        entry={'sha256':sources.SOURCES['build/typing-ranker-v2/ru-0011.parquet'],'bytes':10}
        sources.validate_training_entry(entry)
        with self.assertRaisesRegex(ValueError,'JOINT_PUBLIC_SOURCE_LOCK'):
            sources.validate_training_entry(entry|{'sha256':'a'*64})


if __name__=='__main__':unittest.main()
