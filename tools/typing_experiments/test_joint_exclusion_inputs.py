import hashlib
import json
import re
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
import joint_exclusion_inputs as exclusion
import joint_source_attestation as attestation


class JointExclusionInputTest(unittest.TestCase):
    def test_source_attestation_checks_article_windows_labels_and_all_lemmas(self):
        class Generator:
            @staticmethod
            def bounded_prefix(text):return text
        class Lexicon:
            def analyses(self,word):
                return [SimpleNamespace(lemma=x) for x in {'стали':['стать','сталь']}.get(word,[])]
        text='Они давно стали обсуждать планы.';word='стали';article='123';source='0018.parquet'
        match=re.search(word,text);prefix=text[:match.start()].rstrip()
        row=dict(article=article,source=source,word=word,prefix=prefix,family='17',split='train',
                 typed='слали',expectedSpelling=word,noAuto=False,cohort='typo',families=['сталь','стать'],
                 selectionHash=hashlib.sha256((attestation.SEED+article+word+prefix).encode()).hexdigest(),
                 contextHash=exclusion.source_context_hash(text,match,Generator()),
                 sourceSegmentHash=exclusion.source_segment_hash_at(text,match,exclusion.segment_index(text)))
        def verify(item=row,article_text=text):
            return attestation.attest_article(article,source,article_text,[item],Generator(),Lexicon(),{'стали':'17'},lambda _: 'train')
        self.assertEqual({'checkedRows':1},verify())
        for changes,error in [({'article':'124'},'ROW_SCOPE'),({'split':'holdout'},'ROW_SCHEMA'),({'family':'18'},'ROW_SCHEMA'),
                              ({'expectedSpelling':'сталь'},'LABEL'),({'families':['сталь']},'LEMMAS'),
                              ({'selectionHash':'0'*64},'SELECTION'),({'contextHash':'0'*64},'SOURCE_MISMATCH'),
                              ({'sourceSegmentHash':'0'*64},'SOURCE_MISMATCH')]:
            with self.subTest(changes=changes),self.assertRaisesRegex(ValueError,'JOINT_ARTICLE_'+error):verify(row|changes)
        with self.assertRaisesRegex(ValueError,'JOINT_ARTICLE_SOURCE_MISMATCH'):
            verify(article_text=text.replace('планы','работу'))

    def test_segment_identity_matches_historical_delimiters_and_rejects_wrong_source(self):
        from holdout_ledger import source_segment_hash
        from recover_ranker_sources import BOUNDARY
        self.assertEqual(BOUNDARY.pattern, exclusion.SEGMENT_BOUNDARY.pattern)
        text='Первая фраза.  Вторая строка!\nТретий фрагмент'
        index=exclusion.segment_index(text)
        for token, expected in [('фраза','Первая фраза.'), ('строка','Вторая строка!'), ('фрагмент','Третий фрагмент')]:
            self.assertEqual(source_segment_hash(expected), exclusion.source_segment_hash_at(text,re.search(token,text),index))
        with self.assertRaisesRegex(ValueError,'JOINT_SEGMENT_SOURCE'):
            exclusion.source_segment_hash_at(text,re.search('слово','иное слово'),index)

    def test_source_window_hash_matches_established_recovery_and_uses_right_context(self):
        from right_context_sentence_audit import _source_hash
        class Generator:
            @staticmethod
            def bounded_prefix(text): return text
        text='Накануне  Стали продолжать разговор.'
        match=re.search('Стали',text)
        self.assertEqual(_source_hash('Накануне','стали',' продолжать разговор.'),
                         exclusion.source_context_hash(text,match,Generator()))
        changed=text.replace('разговор','работу')
        self.assertNotEqual(exclusion.source_context_hash(text,match,Generator()),
                            exclusion.source_context_hash(changed,re.search('Стали',changed),Generator()))

    def test_canonical_projection_covers_all_analyses_and_rejects_split_overlap(self):
        class Lexicon:
            def analyses(self, word):
                return tuple(SimpleNamespace(lemma=x) for x in {
                    'стали':['стать','сталь'], 'сталь':['сталь'], 'домой':['домой']
                }.get(word, []))
        def row(word,part,cohort='typo'):
            return dict(word=word,split=part,cohort=cohort,family='172788',
                        expectedSpelling='@'+word if cohort=='protected' else word)
        original=row('стали','train')
        projected=exclusion.canonical_registry_rows({'train':[original,row('стали','train','protected')],
            'holdout':[row('домой','holdout')]},Lexicon())
        self.assertEqual(['сталь','стать'],projected[0]['families'])
        self.assertNotIn('families',original)
        with self.assertRaisesRegex(ValueError,'JOINT_CANONICAL_SPLIT_OVERLAP'):
            exclusion.canonical_registry_rows({'train':[original],'holdout':[row('сталь','holdout')]},Lexicon())
        first=original|{'contextHash':'a'*64}
        second=row('домой','holdout')|{'contextHash':'a'*64}
        with self.assertRaisesRegex(ValueError,'JOINT_SOURCE_CONTEXT_SPLIT_OVERLAP'):
            exclusion.canonical_registry_rows({'train':[first],'holdout':[second]},Lexicon())
        first=original|{'sourceSegmentHash':'b'*64}
        second=row('домой','holdout')|{'sourceSegmentHash':'b'*64}
        self.assertEqual('b'*64, exclusion.canonical_registry_rows({'train':[first]},Lexicon())[0]['sourceSegmentHash'])
        with self.assertRaisesRegex(ValueError,'JOINT_SOURCE_SEGMENT_SPLIT_OVERLAP'):
            exclusion.canonical_registry_rows({'train':[first],'holdout':[second]},Lexicon())
        with self.assertRaisesRegex(ValueError,'JOINT_CANONICAL_UNRESOLVED'):
            exclusion.canonical_registry_rows({'train':[row('неизвестно','train')]},Lexicon())
        altered=row('стали','train');altered['expectedSpelling']='иное'
        with self.assertRaisesRegex(ValueError,'JOINT_CANONICAL_TARGET'):
            exclusion.canonical_registry_rows({'train':[altered]},Lexicon())

    def test_manifest_identity_scope_and_drift(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=root/'calibration.jsonl'
            path.write_text(json.dumps({'family':'lemma','article':'123','split':'calibration'})+'\n')
            digest=hashlib.sha256(path.read_bytes()).hexdigest()
            manifest=root/'manifest.json';manifest.write_text(json.dumps({'files':{path.name:digest},'counts':{'calibration':{'rows':1}}}))
            snapshot=exclusion.capture(root,('calibration.jsonl',))
            self.assertEqual({'lemma'},snapshot['families'])
            self.assertEqual({'123'},snapshot['articles'])
            path.write_text(path.read_text()+' ')
            with self.assertRaisesRegex(ValueError,'EXCLUSION_INPUT_DRIFT'):exclusion.verify(snapshot)
            with self.assertRaisesRegex(ValueError,'EXCLUSION_IDENTITY'):exclusion.capture(root,('calibration.jsonl',))
            path.write_text(json.dumps({'family':'lemma','article':'123','split':'calibration'})+'\n')
            wrong=json.loads(manifest.read_text());wrong['counts']['calibration']['rows']=0;manifest.write_text(json.dumps(wrong))
            with self.assertRaisesRegex(ValueError,'EXCLUSION_COUNTS'):exclusion.capture(root,('calibration.jsonl',))
            wrong['counts']['calibration']['rows']=1;manifest.write_text(json.dumps(wrong))
            path.write_text(json.dumps({'family':'lemma','article':'123','split':'holdout'})+'\n')
            wrong['files'][path.name]=hashlib.sha256(path.read_bytes()).hexdigest();manifest.write_text(json.dumps(wrong))
            with self.assertRaisesRegex(ValueError,'EXCLUSION_SPLIT'):exclusion.capture(root,('calibration.jsonl',))
            path.write_text(json.dumps({'family':'lemma','article':'123','split':'calibration'})+'\n')
            wrong['files'][path.name]=hashlib.sha256(path.read_bytes()).hexdigest();manifest.write_text(json.dumps(wrong))
            (root/'extra.jsonl').write_text('{}\n')
            with self.assertRaisesRegex(ValueError,'EXCLUSION_INPUT_DRIFT'):exclusion.verify(snapshot)
            with self.assertRaisesRegex(ValueError,'EXCLUSION_UNDECLARED_FILES'):exclusion.capture(root,('calibration.jsonl',))
            with self.assertRaisesRegex(ValueError,'EXCLUSION_MANIFEST_SCOPE'):exclusion.capture(root,('holdout.jsonl',))


    def test_unknown_manifest_is_not_recognized_as_public(self):
        with self.assertRaisesRegex(ValueError,'EXCLUSION_PUBLIC_ORIGIN_UNVERIFIED'):
            exclusion.verify_public_origin({'manifestSha256':'a'*64})

    def test_every_split_must_be_registered_with_its_own_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=root/'calibration.jsonl'
            path.write_text(json.dumps({'family':'lemma','article':'123','split':'calibration'})+'\n')
            digest=hashlib.sha256(path.read_bytes()).hexdigest()
            (root/'manifest.json').write_text(json.dumps({'files':{path.name:digest},'counts':{'calibration':{'rows':1}}}))
            captured=exclusion.capture(root,('calibration.jsonl',))
            entries=[{'id':'known','bindings':{'public/corpus/manifest.json':captured['manifestSha256'],
                                              'public/corpus/calibration.jsonl':digest}}]
            self.assertEqual({'calibration.jsonl':['known']},exclusion.verify_registered(captured,{'entries':entries}))
            entries[0]['bindings']['public/corpus/manifest.json']='a'*64
            with self.assertRaisesRegex(ValueError,'EXCLUSION_NOT_REGISTERED'):exclusion.verify_registered(captured,{'entries':entries})
            entries[0]['bindings']={'other/manifest.json':captured['manifestSha256'],'public/corpus/calibration.jsonl':digest}
            with self.assertRaisesRegex(ValueError,'EXCLUSION_NOT_REGISTERED'):exclusion.verify_registered(captured,{'entries':entries})


if __name__=='__main__':unittest.main()
