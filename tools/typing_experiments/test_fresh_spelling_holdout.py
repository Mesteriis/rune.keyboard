from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parent))
from fresh_spelling_holdout import HoldoutSpec, build_rows  # noqa: E402
import independent_corpus_guard as guard
import fresh_spelling_holdout as subject


class FakeGenerator:
    @staticmethod
    def safe_typos(word, _language, _known, _seed):
        return [(word[:-1], "missing_letter")]


class FreshSpellingHoldoutTest(unittest.TestCase):
    def test_new_holdout_binds_source_and_all_analyses_without_guessing(self):
        from types import SimpleNamespace
        generator = subject.common.load_generator()
        class Lexicon:
            def analyses(self, word):
                return [SimpleNamespace(lemma=x) for x in ('домой', 'дом') if word == 'домой']
        lexicon = Lexicon()
        text = 'Мы теперь просто идём домой сегодня.'
        with mock.patch.object(guard, '_context_generator', return_value=generator):
            items = subject.source_bound_candidates('123', text, {'домой'}, set(), 42, generator, lexicon)
            self.assertEqual(1, len(items))
            self.assertEqual(1, len(subject.source_bound_candidates('123', text, {'домой', 'сегодня'}, set(), 42, generator, lexicon)))
            evidence = items[0]['sourceEvidence']
            self.assertEqual('123', evidence['article'])
            self.assertEqual(['дом', 'домой'], evidence['families'])
            self.assertEqual(guard.source_segment_hash(text), evidence['sourceSegmentHash'])
            self.assertEqual(64, len(evidence['contextHash']))
            self.assertEqual([], subject.source_bound_candidates('123', text+' '+text, {'домой'}, set(), 42, generator, lexicon))
            self.assertEqual([], subject.source_bound_candidates('123', text.replace('домой', 'домой-куда'), {'домой'}, set(), 42, generator, lexicon))
            with self.assertRaisesRegex(ValueError, 'FRESH_SOURCE_ARTICLE'):
                subject.source_bound_candidates('not-an-id', text, {'домой'}, set(), 42, generator, lexicon)
        seen = set()
        subject.register_source_article('00123', seen)
        with self.assertRaisesRegex(ValueError, 'FRESH_SOURCE_ARTICLE'):
            subject.register_source_article('123', seen)

    def test_new_holdout_emits_evidence_and_refuses_shared_canonical_family(self):
        spec = HoldoutSpec(7, '0012', 'a'*64, 1, 42)
        evidence = {'article': '123', 'sourceSegmentHash': 'b'*64, 'contextHash': 'c'*64,
                    'families': ['дом'], 'expectedSpelling': 'домой'}
        item = {'word': 'домой', 'family': 'домои', 'prefix': 'мы идём',
                'selectionHash': 'd'*64, 'sourceEvidence': evidence}
        rows = build_rows(spec, [item], set(), FakeGenerator(), typo_count=1, correct_count=0)
        self.assertEqual(evidence, {key: rows[0][key] for key in evidence})
        subject.require_disjoint_canonical_families(rows)
        with self.assertRaisesRegex(ValueError, 'FRESH_CANONICAL_FAMILY_OVERLAP'):
            subject.require_disjoint_canonical_families(rows + [dict(rows[0], families=['ДОМ'])])
        legacy = subject.common.build_rows([item], set(), FakeGenerator(), typo_count=1, correct_count=0)
        self.assertEqual(evidence, {key: legacy[0][key] for key in evidence})

    def test_selection_skips_ambiguous_family_overlap_across_cohorts(self):
        spec = HoldoutSpec(7, '0012', 'a'*64, 1, 42)
        pool = []
        for index, (word, families) in enumerate((('стали', ['стать', 'сталь']),
                                                   ('сталь', ['сталь']), ('домой', ['дом']))):
            pool.append({'word': word, 'family': word, 'prefix': 'мы видим', 'selectionHash': str(index),
                         'sourceEvidence': {'families': families, 'expectedSpelling': word}})
        for name, builder in (('v7', lambda: build_rows(spec, pool, set(), FakeGenerator(), typo_count=1, correct_count=1)),
                              ('v6', lambda: subject.common.build_rows(pool, set(), FakeGenerator(), typo_count=1, correct_count=1))):
            with self.subTest(builder=name):
                rows = builder()
                self.assertEqual(2, len(rows))
                subject.require_disjoint_canonical_families(rows)
                self.assertFalse({'стали', 'сталь'} <= {row['expectedSpelling'] for row in rows})

    def test_new_preparer_reaches_real_preflight_and_refuses_source_drift(self):
        from types import ModuleType, SimpleNamespace
        from test_holdout_ledger import ledger
        from holdout_ledger import keys_for
        from test_public_corpus_preparation_v1 import controls
        from public_corpus_preparation_v1 import preflight
        generator = subject.common.load_generator()
        known = {'домой', 'сегодня'}
        dictionary_state = {'changed': False}
        class Lexicon:
            def __init__(self, **kwargs): pass
            def analyses(self, word): return [SimpleNamespace(lemma=word)]
            def receipt(self): return {'fixture': 'changed' if dictionary_state['changed'] else 'dictionary'}
        class Batch:
            def column(self, index):
                values = ['999999'] if index == 0 else ['Мы уже давно хотим домой. Мы завтра вечером снова придём сегодня.']
                return SimpleNamespace(to_pylist=lambda: values)
        build_root = subject.ROOT/'build'
        existed = build_root.exists()
        build_root.mkdir(exist_ok=True)
        if not existed:
            self.addCleanup(build_root.rmdir)
        with tempfile.TemporaryDirectory(dir=build_root) as directory:
            root = Path(directory).resolve()
            source, frequency, script, exclusion = (root/name for name in ('source', 'frequency', 'collector.py', 'exclude.jsonl'))
            source.write_bytes(b'parquet-fixture'); frequency.write_text('fixture'); script.write_text('fixture')
            exclusion.write_text(json.dumps({'family': 'отсутствует'})+'\n')
            sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
            spec = HoldoutSpec(7, '0012', sha(source), source.stat().st_size, 42)
            mutated = ''
            def batches(**kwargs):
                yield Batch()
                if mutated == 'source':
                    source.write_bytes(b'changed')
                elif mutated == 'exclusion':
                    exclusion.write_text(json.dumps({'family': 'другое'})+'\n')
                elif mutated == 'dictionary':
                    dictionary_state['changed'] = True
            parquet = ModuleType('pyarrow.parquet')
            parquet.ParquetFile = lambda path: SimpleNamespace(iter_batches=batches)
            arrow = ModuleType('pyarrow'); arrow.parquet = parquet; arrow.__version__ = 'fixture'
            ranker = ModuleType('ranker'); ranker.PymorphyLexicon = Lexicon
            ranker.__file__ = str(subject.ROOT/'tools/morphology/ranker.py')
            seen = []
            def finish(snapshot, rows):
                result = preflight(rows, 'spelling', ledger(False), controls(), 'new-families')
                self.assertEqual([], result['identityErrors'])
                self.assertEqual('BLOCKED_COVERAGE', result['status'])
                prior = ledger(False)
                prior['entries'][0]['keys']['article'] = sorted(keys_for([rows[0]], 'article'))
                overlap = preflight(rows, 'spelling', prior, controls(), 'new-families')
                self.assertEqual('BLOCKED_OVERLAP', overlap['status'])
                self.assertGreater(overlap['lexicalOverlaps']['article'], 0)
                prior = ledger(False)
                prior['entries'][0]['keys']['family'] = sorted(keys_for([rows[0]], 'family'))
                overlap = preflight(rows, 'spelling', prior, controls(), 'new-families')
                self.assertEqual('BLOCKED_OVERLAP', overlap['status'])
                self.assertGreater(overlap['lexicalOverlaps']['family'], 0)
                seen.extend(rows)
                return {'independentQualification': False}
            original_build = subject.build_rows
            with mock.patch.dict(sys.modules, {'pyarrow': arrow, 'pyarrow.parquet': parquet, 'ranker': ranker}), \
                 mock.patch.object(subject, 'TYPO_ROWS', 1), \
                 mock.patch.object(subject, 'CORRECT_ROWS', 1), mock.patch.object(subject.common, 'FREQUENCY_SHA256', sha(frequency)), \
                 mock.patch.object(subject, 'build_rows', side_effect=lambda spec, pool, known, generator:
                                   original_build(spec, pool, known, generator, typo_count=1, correct_count=1)), \
                 mock.patch.object(subject.common, 'load_generator', return_value=generator), \
                 mock.patch.object(generator, 'vocabulary', return_value=known), \
                 mock.patch.object(guard, '_context_generator', return_value=generator), \
                 mock.patch.object(guard, 'begin', return_value={}), mock.patch.object(guard, 'finish', side_effect=finish):
                result = subject.prepare(spec, script, source, frequency, [exclusion], root/'first')
                self.assertEqual(2, result['counts']['total'])
                self.assertEqual(2, len(seen))
                self.assertTrue(all(row['article'] == '999999' and row['families'] for row in seen))
                self.assertEqual(sha(source), result['selectionInputBindings']['parquet'])
                self.assertEqual(sha(exclusion), result['selectionInputBindings']['exclusion-0'])
                mutated = 'source'
                with self.assertRaisesRegex(ValueError, 'JOINT_PUBLIC_INPUT_DRIFT'):
                    subject.prepare(spec, script, source, frequency, [exclusion], root/'second')
                self.assertFalse((root/'second').exists())
                source.write_bytes(b'parquet-fixture')
                mutated = 'exclusion'
                with self.assertRaisesRegex(ValueError, 'JOINT_PUBLIC_INPUT_DRIFT'):
                    subject.prepare(spec, script, source, frequency, [exclusion], root/'third')
                self.assertFalse((root/'third').exists())
                exclusion.write_text(json.dumps({'family': 'отсутствует'})+'\n')
                mutated = 'dictionary'
                with self.assertRaisesRegex(ValueError, 'FRESH_DICTIONARY_DRIFT'):
                    subject.prepare(spec, script, source, frequency, [exclusion], root/'fourth')
                self.assertFalse((root/'fourth').exists())
                dictionary_state['changed'] = False
                mutated = ''
                ranker.__file__ = str(root/'other-ranker.py')
                with self.assertRaisesRegex(ValueError, 'FRESH_DICTIONARY_HELPER_IDENTITY'):
                    subject.prepare(spec, script, source, frequency, [exclusion], root/'fifth')
                self.assertFalse((root/'fifth').exists())
                ranker.__file__ = str(subject.ROOT/'tools/morphology/ranker.py')
                v6 = subject.common
                original_v6 = v6.build_rows
                with mock.patch.object(v6, 'SOURCE_SHA256', sha(source)), \
                     mock.patch.object(v6, 'SOURCE_BYTES', source.stat().st_size), \
                     mock.patch.object(v6, 'TYPO_ROWS', 1), mock.patch.object(v6, 'CORRECT_ROWS', 1), \
                     mock.patch.object(v6, 'build_rows', side_effect=lambda pool, known, generator:
                                       original_v6(pool, known, generator, typo_count=1, correct_count=1)):
                    result = v6.prepare(source, frequency, [exclusion], root/'v6-first')
                    self.assertEqual(2, result['counts']['total'])
                    self.assertEqual(sha(source), result['selectionInputBindings']['parquet'])
                    mutated = 'source'
                    with self.assertRaisesRegex(ValueError, 'JOINT_PUBLIC_INPUT_DRIFT'):
                        v6.prepare(source, frequency, [exclusion], root/'v6-second')
                    self.assertFalse((root/'v6-second').exists())

    def test_selected_segment_is_bound_only_for_registry_checked_rows(self):
        from holdout_ledger import source_segment_hash, keys_for
        sentence='В начале  Фразы слово. И ещё текст'
        historical={'id':'old'}
        self.assertEqual({'id':'old'},guard.attach_selector_segment(historical,sentence,None))
        checked=guard.attach_selector_segment({'id':'new'},sentence,{})
        self.assertEqual(source_segment_hash(sentence),checked['sourceSegmentHash'])
        self.assertNotEqual(source_segment_hash('В начале Фразы слово.'),checked['sourceSegmentHash'])
        left=checked | {'contextHash':'a'*64}
        right={'contextHash':'b'*64,'sourceSegmentHash':source_segment_hash(sentence.lower())}
        self.assertTrue(keys_for([left],'sentence') & keys_for([right],'sentence'))
        with self.assertRaisesRegex(ValueError,'LEDGER_SOURCE_SEGMENT_TEXT'):
            guard.attach_selector_segment({},'   ',{})

    def test_selector_projection_binds_actual_article_and_source_window(self):
        import re
        from right_context_sentence_audit import _source_hash
        text='Первый текст.\nЗдесь идут ещё слова домой завтра!  Конец.'
        segments=list(guard.selector_segments(text))
        self.assertEqual(re.split(r'(?<=[.!?])\s+|\n+',text),[s for s,_ in segments])
        sentence,start=segments[1]
        match=re.search('домой',sentence)
        row={'articleId':'123','expectedSpelling':'домой'}
        generator=type('G',(),{'bounded_prefix':staticmethod(lambda x:x.lstrip())})
        with mock.patch.object(guard,'_context_generator',return_value=generator):
            guard.attach_selector_source(row,text,sentence,start,match,{})
            absolute=start+match.start()
            expected=_source_hash(text[:absolute].lstrip().rstrip(' \t'),'домой',text[absolute+5:absolute+5+128])
            self.assertEqual(expected,row['contextHash'])
            self.assertEqual('123',row['article'])
            with self.assertRaisesRegex(ValueError,'SELECTOR_SOURCE_MISMATCH'):
                guard.attach_selector_source(row,text,sentence,start+1,match,{})
        original={'articleId':'123','expectedSpelling':'домой'}
        self.assertEqual(original,guard.attach_selector_source(original,text,sentence,start,match,None))

    def test_independent_selectors_refuse_fragments_but_historical_mode_is_unchanged(self):
        import re
        cases=(('слово отдельно',True),('слово-часть',False),('слово‐часть',False),
               ('словоі',False),('слово2',False),('слово_имя',False),('слово\u0301',False),
               ('слово\u200dчасть',False),('часть\u200bслово',False),('слово\u2060часть',False),
               ('часть\u202eслово',False),
               ('prefixслово',False),('часть-слово',False),('часть‒слово',False),
               ('слово—часть',False),('слово — часть',True),
               ("слово'часть",False),('слово’часть',False),('частьʼслово',False),
               ("часть'слово",False),('часть’слово',False),
               ("'слово'",True),('’слово’',True))
        for text,expected in cases:
            match=re.search('слово',text)
            with self.subTest(text=text):
                self.assertEqual(expected,guard.whole_selector_token(text,text,0,match,{}))
                self.assertTrue(guard.whole_selector_token(text,text,0,match,None))
                if not expected:
                    with self.assertRaisesRegex(ValueError,'SELECTOR_PARTIAL_SOURCE_TOKEN'):
                        guard.attach_selector_source({'expectedSpelling':'слово'},text,text,0,match,{})
        text='слово отдельно';match=re.search('слово',text)
        with self.assertRaisesRegex(ValueError,'SELECTOR_SOURCE_MISMATCH'):
            guard.whole_selector_token(text,text,1,match,{})

    def test_all_unicode_dash_punctuation_blocks_adjacent_word_fragments(self):
        import re
        import unicodedata
        for codepoint in range(0x110000):
            char = chr(codepoint)
            if unicodedata.category(char) != 'Pd':
                continue
            for source in ('слово' + char + 'часть', 'часть' + char + 'слово'):
                match = re.search('слово', source)
                with self.subTest(codepoint=codepoint, source=source):
                    self.assertFalse(guard.whole_selector_token(source, source, 0, match, {}))
                    self.assertTrue(guard.whole_selector_token(source, source, 0, match, None))

    def test_selector_families_include_all_dictionary_analyses_and_refuse_leaks(self):
        from types import SimpleNamespace
        class Lexicon:
            def analyses(self,word):
                return [SimpleNamespace(lemma=x) for x in {'стали':['стать','сталь'],'сталь':['сталь'],'мир':['мир']}.get(word,[])]
        rows=[{'expectedSpelling':'стали','partition':'train'}, {'expectedSpelling':'мир','partition':'test'}]
        guard.project_selector_families(rows,Lexicon())
        self.assertEqual(['сталь','стать'],rows[0]['families'])
        with self.assertRaisesRegex(ValueError,'SELECTOR_CANONICAL_SPLIT_OVERLAP'):
            guard.project_selector_families(rows+[{'expectedSpelling':'сталь','partition':'test'}],Lexicon())
        with self.assertRaisesRegex(ValueError,'SELECTOR_CANONICAL_UNRESOLVED'):
            guard.project_selector_families([{'expectedSpelling':'неслово','partition':'test'}],Lexicon())

    def test_selector_source_snapshot_rejects_input_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            parquet=Path(directory)/'source';frequency=Path(directory)/'frequency'
            parquet.write_bytes(b'public source');frequency.write_bytes(b'public frequency')
            digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            snapshot=guard.selector_inputs({},parquet,digest(parquet),frequency,digest(frequency))
            self.assertIn('tools/typing_experiments/selector_text_format_v1.py', snapshot)
            guard.verify_selector_inputs(snapshot)
            parquet.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'JOINT_PUBLIC_INPUT_DRIFT'):
                guard.verify_selector_inputs(snapshot)

    def test_selector_rejects_source_reuse_across_partitions(self):
        base=dict(article='12',contextHash='a'*64,sourceSegmentHash='b'*64,partition='train')
        for field in ('article','contextHash','sourceSegmentHash'):
            other=dict(article='13',contextHash='c'*64,sourceSegmentHash='d'*64,partition='test')
            other[field]=base[field]
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'SELECTOR_SOURCE_SPLIT_OVERLAP'):
                guard.validate_selector_partitions([base,other])
        guard.validate_selector_partitions([base,base|{'partition':'train'}])

    def test_selector_admission_is_atomic_and_tracks_all_lemmas(self):
        from types import SimpleNamespace
        class Lexicon:
            def analyses(self,word):
                return [SimpleNamespace(lemma=value) for value in {
                    'стали':['сталь','стать'], 'сталь':['сталь'], 'мир':['мир'],
                }.get(word,[])]
        admission=guard.SelectorAdmission(Lexicon())
        def row(part,target,article,context,segment):
            return dict(partition=part,expectedSpelling=target,article=article,
                        contextHash=context,sourceSegmentHash=segment)
        first=row('train','стали','1','c1','s1')
        self.assertTrue(admission.accept(first))
        self.assertEqual(['сталь','стать'],first['families'])
        failed=row('test','сталь','2','c2','s2')
        self.assertFalse(admission.accept(failed))
        self.assertNotIn('2',admission.owners['article'])
        self.assertTrue(admission.accept(row('test','мир','2','c2','s2')))
        self.assertFalse(admission.accept(row('dev','мир','3','c3','s3')))
        self.assertFalse(admission.accept(row('dev','незнакомо','3','c3','s3')))
        self.assertEqual({'accepted':2,'unresolved':1,'overlap':2},admission.counts)

    def test_unchecked_text_corpus_cannot_inherit_word_row_clearance(self):
        guard.reject_unchecked_texts(None,{'train':[{'text':'historical'}]})
        guard.reject_unchecked_texts({}, {'train':[]})
        with self.assertRaisesRegex(ValueError,'SELECTOR_TEXT_CORPUS_UNCHECKED'):
            guard.reject_unchecked_texts({}, {'train':[{'text':'new public fragment'}]})

    def test_selected_text_format_is_checked_before_future_collection(self):
        guard.check_selected_source_text({}, 'слово часть', 'слово часть')
        for char in ('\u200b', '\u200d', '\u2060', '\u202e'):
            with self.subTest(codepoint=ord(char)):
                with self.assertRaisesRegex(ValueError, 'SELECTOR_TEXT_FORMAT_FRAGMENT'):
                    guard.check_selected_source_text({}, 'слово' + char + 'часть', 'слово часть')
                guard.check_selected_source_text(None, 'слово' + char + 'часть', 'слово часть')
        with self.assertRaisesRegex(ValueError, 'SELECTOR_TEXT_TRUNCATED'):
            guard.check_selected_source_text({}, 'длинное слово', 'длин')
        for source, fragment in (('сло\u0301во', 'сло во'), ('северо-запад', 'северо запад'),
                                 ('северо‒запад', 'северо запад'), ('северо—запад', 'северо запад'),
                                 ("д’артаньян", 'д артаньян'), ('слово123', 'слово'),
                                 ('словоLatin', 'слово')):
            with self.subTest(source=source):
                with self.assertRaisesRegex(ValueError, 'SELECTOR_TEXT_PARTIAL_SOURCE_TOKEN'):
                    guard.check_selected_source_text({}, source, fragment)
                guard.check_selected_source_text(None, source, fragment)
        with self.assertRaisesRegex(ValueError, 'SELECTOR_TEXT_SOURCE_MISMATCH'):
            guard.check_selected_source_text({}, 'слово часть', 'другой текст')
        with self.assertRaisesRegex(ValueError, 'SELECTOR_TEXT_CORPUS_UNCHECKED'):
            guard.reject_unchecked_texts({}, {'train': [{'text': 'слово часть'}]})

    def test_text_exposure_finds_collisions_without_certifying_corpus(self):
        from types import SimpleNamespace
        from audit_selector_text_exposure import audit
        from test_holdout_ledger import ledger
        from test_public_corpus_preparation_v1 import controls
        class Lexicon:
            def analyses(self,word):
                return [SimpleNamespace(lemma='готовый')] if word=='готовы' else []
        texts={'train':[{'articleId':'123','text':'мы готовы'}],
               'dev':[{'articleId':'124','text':'готовы'}],'test':[]}
        rows={part:[] for part in texts}
        sources={'123':'мы готовы потом','124':'готовы дальше'}
        result=audit(texts,rows,sources,Lexicon(),ledger(False),controls())
        self.assertEqual(2,result['records'])
        self.assertGreater(result['lexicalOverlaps']['article'],0)
        self.assertGreater(result['lexicalOverlaps']['family'],0)
        self.assertGreater(result['crossPartitionOverlaps']['family'],0)
        self.assertGreater(result['unresolvedSurfaces'],0)
        self.assertIs(False,result['qualified'])
        texts['train'][0]['text']='чужой текст'
        with self.assertRaisesRegex(ValueError,'TEXT_AUDIT_SOURCE_MISMATCH'):
            audit(texts,rows,sources,Lexicon(),ledger(False),controls())

    def test_text_exposure_reports_cross_partition_unknown_surface(self):
        from types import SimpleNamespace
        from audit_selector_text_exposure import audit
        from test_holdout_ledger import ledger
        from test_public_corpus_preparation_v1 import controls
        class Lexicon:
            def analyses(self, word):
                return [SimpleNamespace(lemma='дом')] if word == 'дом' else []
        texts = {'train': [{'articleId': '101', 'text': 'квазислово дом'}],
                 'dev': [{'articleId': '102', 'text': 'квазислово дом'}], 'test': []}
        rows = {part: [] for part in texts}
        result = audit(texts, rows, {'101': 'квазислово дом', '102': 'квазислово дом'},
                       Lexicon(), ledger(False), controls())
        self.assertEqual(1, result['crossPartitionOverlaps']['family'])
        self.assertEqual(2, result['crossPartitionOverlaps']['surface'])
        self.assertEqual(1, result['crossPartitionOverlaps']['unresolvedSurface'])
        self.assertFalse(result['qualified'])

    def test_text_exposure_counts_cleaned_contexts_and_ignores_partial_targets(self):
        from types import SimpleNamespace
        from audit_selector_text_exposure import audit
        from test_holdout_ledger import ledger
        from test_public_corpus_preparation_v1 import controls
        from control_ledger import key_for
        class Lexicon:
            def analyses(self, word):
                return [SimpleNamespace(lemma=word)]
        source = 'мы уже готовы потом'
        texts = {'train':[{'articleId':'123', 'text':'мы уже готовы'}],
                 'dev':[{'articleId':'124', 'text':'мы уже готовы'}], 'test':[]}
        sources = {'123':source, '124':source}
        rows = {part:[] for part in texts}
        registry = controls()
        registry['entries'].append(dict(id='cleaned-context',kind='regression',language='ru',rowCount=1,
            bindings={'file':'b'*64},keys=[key_for(dict(language='ru',prefix='мы уже ',typed='готовы'),'regression')]))
        result = audit(texts, rows, sources, Lexicon(), ledger(False), registry)
        self.assertEqual(1, result['textLexicalOverlaps']['context'])
        self.assertEqual(1, result['textControlContextOverlaps'])
        self.assertGreater(result['crossPartitionOverlaps']['context'], 0)
        self.assertGreater(result['crossPartitionOverlaps']['sourceContext'], 0)
        self.assertFalse(result['contextCoverageComplete'])
        for records in texts.values():
            if records: records[0]['text'] = 'мы уже гото'
        partial = audit(texts, rows, sources, Lexicon(), ledger(False), registry)
        self.assertEqual(2, partial['truncatedInsideWord'])
        self.assertEqual(0, partial['textLexicalOverlaps']['context'])
        self.assertEqual(0, partial['textControlContextOverlaps'])

    def test_text_exposure_matches_original_punctuation_and_case_context(self):
        from types import SimpleNamespace
        from audit_selector_text_exposure import audit
        from test_holdout_ledger import ledger
        from test_public_corpus_preparation_v1 import controls
        from holdout_ledger import keys_for
        from control_ledger import key_for
        class Lexicon:
            def analyses(self, word):
                return [SimpleNamespace(lemma=word)]
        texts = {'train':[{'articleId':'123', 'text':'мы уже готовы'}], 'dev':[], 'test':[]}
        rows = {part:[] for part in texts}
        context = dict(language='ru', prefix='Мы, уже ', typed='готовы', expectedSpelling='готовы')
        lexical=ledger(False)
        lexical['entries'][0]['keys']['context']=sorted(keys_for([context],'context'))
        registry=controls()
        registry['entries'].append(dict(id='source-context',kind='regression',language='ru',rowCount=1,
            bindings={'file':'b'*64},keys=[key_for(context,'regression')]))
        result=audit(texts, rows, {'123':'Мы, уже готовы потом'}, Lexicon(), lexical, registry)
        self.assertEqual(1,result['textLexicalOverlaps']['sourceContext'])
        self.assertEqual(1,result['textSourceControlContextOverlaps'])
        self.assertEqual(0,result['textLexicalOverlaps']['context'])
        self.assertEqual(0,result['unmappedSourceFragments'])
        self.assertFalse(result['contextCoverageComplete'])

    def test_all_current_cli_collectors_refuse_before_reading_sources_or_creating_output(self):
        directory=Path(__file__).resolve().parent
        for name in ['prepare_external_spelling_holdout.py',
                     *[f'prepare_external_spelling_holdout_v{i}.py' for i in range(7,13)],
                     'prepare_joint_correction.py','prepare_joint_followup.py',
                     'prepare_refinement.py','prepare_word_ranking.py',
                     'prepare_epoch_test.py','prepare_retrieval_test.py']:
            with self.subTest(name=name),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);output=root/'must-not-exist'
                args=['--source-root',str(root/'missing-source')] if 'joint' in name else [
                    '--parquet',str(root/'missing.parquet'),'--frequency',str(root/'missing-frequency')]
                if name.startswith('prepare_external'):
                    args+=['--exclude-rows',str(root/'missing-exclusions')]
                result=subprocess.run([sys.executable,str(directory/name),*args,'--output',str(output)],
                    capture_output=True,text=True)
                self.assertNotEqual(0,result.returncode)
                self.assertIn('NEW_HOLDOUT_REGISTRY_COVERAGE_INCOMPLETE',result.stderr)
                self.assertNotIn('FileNotFoundError',result.stderr)
                self.assertFalse(output.exists())

    def test_historical_mode_is_explicit_and_cannot_certify_freshness(self):
        for value in (None,1,'false'):
            with self.assertRaisesRegex(ValueError,'HISTORICAL_REPRODUCTION_BOOLEAN'):guard.begin(value)
        with mock.patch.object(Path,'read_bytes',side_effect=AssertionError('read ledger')):
            self.assertIsNone(guard.begin(True))
        receipt=guard.finish(None,[])
        self.assertEqual('historical-disclosed-regression',receipt['scope'])
        self.assertIs(False,receipt['newUnseenHoldout'])
        self.assertIs(False,receipt['independentQualification'])
        self.assertIs(True,receipt['historicalReproduction'])

    def test_final_gate_rechecks_rows_against_both_real_registries(self):
        snapshot=dict(lexical=json.loads((guard.HERE/'holdout-ledger.json').read_text()),
                      controls=json.loads((guard.HERE/'control-ledger.json').read_text()))
        row=dict(id='known-disclosed',language='ru',prefix='новый контекст',typed='зочу',expectedSpelling='хочу')
        with self.assertRaisesRegex(ValueError,'NEW_HOLDOUT_BLOCKED_OVERLAP'):
            guard.finish(snapshot,[row])

    def test_final_gate_rejects_changed_english_surface_snapshot(self):
        snapshot=dict(lexical={}, controls={}, registryBindings={'fake':'binding'},
                      englishSurfaceBindings={'ewt-surface-exclusions-v1.json':'0'*64})
        with mock.patch.object(guard, 'preflight', return_value={'status':'READY_TO_FREEZE'}), \
                mock.patch.object(guard, 'registry_bindings', return_value={'fake':'binding'}):
            with self.assertRaisesRegex(ValueError, 'NEW_HOLDOUT_SURFACE_DRIFT'):
                guard.finish(snapshot, [])

    def test_archived_collectors_retain_exact_source_and_row_parity(self):
        directory=Path(__file__).resolve().parent;archive=directory/'frozen_sources'
        sources=json.loads((archive/'manifest.json').read_text())['sources']
        names=['prepare_external_spelling_holdout.py','fresh_spelling_holdout.py','prepare_external_spelling_holdout_v7.py',
               'prepare_external_spelling_holdout_v8.py']
        digests=['956436a1fbd708706bddb3bad44c1fdf7bff838ef95a8c06911008148590fe01',
                 'a5fe5e58e2801996d62c293b89dec1aae64ac0356e070260cbacf5357feaf25f',
                 'fbc88fc175dd0407df287faa7cb3c6257fa181a271ffb03cbf6221a812b68a9b',
                 '4b5710d76e16faf1a06c316af1b7f45045d8a7d3187ad7da456572e380564fe6']
        pool=[dict(word=f'слово{i}',family=f'слово{i}',prefix='Контекст',selectionHash=f'{i:064x}') for i in range(6)]
        for name,digest in zip(names,digests,strict=True):
            source=archive/sources[digest]['file']
            self.assertEqual(digest,hashlib.sha256(source.read_bytes()).hexdigest())
            spec=importlib.util.spec_from_file_location('archived_collector',source)
            original=importlib.util.module_from_spec(spec)
            old_path=sys.path[:]
            sys.modules[spec.name]=original
            try:
                spec.loader.exec_module(original)
                current=importlib.import_module(Path(name).stem)
                args=([HoldoutSpec(9,'0014','a'*64,123,456)] if name=='fresh_spelling_holdout.py' else [])
                self.assertEqual(original.build_rows(*args,pool,set(),FakeGenerator,typo_count=2,correct_count=2),
                    current.build_rows(*args,pool,set(),FakeGenerator,typo_count=2,correct_count=2))
            finally:
                sys.modules.pop(spec.name,None)
                sys.path[:]=old_path

    def test_joint_row_generation_matches_the_original_archived_builder(self):
        directory=Path(__file__).resolve().parent
        source=directory/'frozen_sources/prepare_joint_correction_cfa5777d2a2ac53f.py'
        self.assertEqual('cfa5777d2a2ac53ffb339aa56b34d57c4a4a6a0ec1a712b1867b857d85043728',
                         hashlib.sha256(source.read_bytes()).hexdigest())
        original={'__file__':str(source),'__name__':'archived_joint'}
        exec(compile(source.read_bytes(),str(source),'exec'),original)
        import prepare_joint_correction as current
        pool={str(i):[dict(word=word,family=str(i),prefix='Контекст проверки',article=str(i),
                          selectionHash=f'{i:064x}')] for i,word in enumerate(('мир','пробный'))}
        expected=original['rows_from_pool'](pool,'holdout',{'мир','пробный'})
        self.assertTrue(expected)
        self.assertEqual(expected,current.rows_from_pool(pool,'holdout',{'мир','пробный'}))

    def test_v7_v8_shared_builder_matches_all_1700_original_rows(self):
        directory = Path(__file__).resolve().parent
        archive = directory / 'frozen_sources'
        sources = json.loads((archive / 'manifest.json').read_text())['sources']
        cases = ((7, 'fbc88fc175dd0407df287faa7cb3c6257fa181a271ffb03cbf6221a812b68a9b'),
                 (8, '4b5710d76e16faf1a06c316af1b7f45045d8a7d3187ad7da456572e380564fe6'))
        pool = [dict(word=f'слово{i:04d}', family=f'слово{i:04d}', prefix='Контекст',
                     selectionHash=f'{i:064x}') for i in range(1700)]
        for version, digest in cases:
            with self.subTest(version=version):
                path = archive / sources[digest]['file']
                self.assertEqual(digest, hashlib.sha256(path.read_bytes()).hexdigest())
                spec = importlib.util.spec_from_file_location(f'archived_v{version}', path)
                original = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(original)
                current = importlib.import_module(f'prepare_external_spelling_holdout_v{version}')
                expected = original.build_rows(pool, set(), FakeGenerator)
                actual = current.build_rows(pool, set(), FakeGenerator)
                self.assertEqual(1700, len(expected))
                self.assertEqual(expected, actual)

    def test_spec_and_rows_are_version_and_shard_bound(self):
        spec = HoldoutSpec(9, "0014", "a" * 64, 123, 456)
        pool = [{"word": f"слово{i}", "family": f"слово{i}", "prefix": "Контекст",
                 "selectionHash": f"{i:064x}"} for i in range(6)]
        rows = build_rows(spec, pool, set(), FakeGenerator, typo_count=2, correct_count=2)
        self.assertTrue(all(row["corpusVersion"] == 9 and "-v9-" in row["id"] for row in rows))
        self.assertTrue(all("ru-0014" in row["source"] for row in rows))
        self.assertEqual(len(rows), len({row["family"] for row in rows}))

    def test_invalid_spec_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "HOLDOUT_SPEC"):
            HoldoutSpec(6, "0012", "a" * 64, 123, 456)
        with self.assertRaisesRegex(ValueError, "HOLDOUT_SPEC"):
            HoldoutSpec(7, "14", "a" * 64, 123, 456)
        with self.assertRaisesRegex(ValueError, "SOURCE_SHA256"):
            HoldoutSpec(9, "0014", "z" * 64, 123, 456)


if __name__ == "__main__":
    unittest.main()
