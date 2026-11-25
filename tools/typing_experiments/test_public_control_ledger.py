import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from control_ledger import load,key_for,article_key,assert_disjoint,surface_key
from import_control_components import load_original


class PublicControlSnapshotTest(unittest.TestCase):
    HISTORICAL_PUNCTUATION_IDS = {f'{corpus}-punctuation-{language}'
                                 for corpus in ('qualification-v2', 'compact-v3', 'compact-v4')
                                 for language in ('en', 'ru', 'es')}

    def setUp(self):self.ledger=load(Path(__file__).with_name('control-ledger.json'))

    def test_all_punctuation_components_and_languages_are_persisted(self):
        entries=[e for e in self.ledger['entries']
                 if e['kind']=='punctuation' and e['id'] in self.HISTORICAL_PUNCTUATION_IDS]
        self.assertEqual(self.HISTORICAL_PUNCTUATION_IDS,{e['id'] for e in entries})
        self.assertEqual(3600,sum(e['rowCount'] for e in entries))
        self.assertEqual({'en','ru','es'},{e['language'] for e in entries})

    def test_known_ru_punctuation_identity_survives_without_original_corpora(self):
        keys={k for e in self.ledger['entries'] if e['kind']=='punctuation' for k in e['keys']}
        self.assertIn('42a780b228b43e70eb7ce7449434f545fbdc4fc7af1cb2b214e84b230401a618',keys)
        self.assertFalse(self.ledger['coverageComplete'])

    def test_all_protected_language_components_are_persisted(self):
        prefixes=('qualification-v2-protected-', 'compact-v3-protected-', 'compact-v4-protected-')
        entries=[e for e in self.ledger['entries'] if e['kind']=='protected' and e['id'].startswith(prefixes)]
        self.assertEqual({prefix + lang for prefix in prefixes for lang in ('en','ru','es')},
                         {e['id'] for e in entries})
        self.assertEqual(9,len(entries));self.assertEqual(5400,sum(e['rowCount'] for e in entries))
        self.assertEqual(1800,len({k for e in entries for k in e['keys']}))

    def test_all_punctuation_articles_are_persisted_with_language_namespace(self):
        entries=[e for e in self.ledger['entries'] if e['id'] in self.HISTORICAL_PUNCTUATION_IDS]
        self.assertEqual(3476,sum(len(e['articleKeys']) for e in entries))
        self.assertIn(article_key(dict(language='ru',article='4476020')),{k for e in entries for k in e['articleKeys']})
        self.assertTrue(all('articleKeys' not in e for e in self.ledger['entries'] if e['kind']=='protected'))

    def test_protected_ru_token_is_blocked_without_original_corpora(self):
        with self.assertRaisesRegex(ValueError,'CONTROL_OVERLAP:protected'):
            assert_disjoint([dict(language='ru',prefix='Сохраните точный токен в примере 0',typed='Amelia')],self.ledger,'protected')

    def test_disclosed_wiktionary_abbreviations_block_new_contexts(self):
        entry, = [entry for entry in self.ledger['entries']
                  if entry['id'] == 'public-a4-wiktionary-graphic-abbreviations-v1']
        frozen = json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
        self.assertEqual(hashlib.sha256(frozen).hexdigest(),
                         '6c2b5f4452fa71c23713f26df62a30bddcd47d60cd40af2caff22f31bc6c2e38')
        source_rows = entry['sourceCapture']['rows']
        self.assertEqual(124, len({row['pageId'] for row in source_rows}))
        self.assertEqual(set(entry['surfaceKeys']), {row['surfaceSha256'] for row in source_rows})
        original = {'language': 'ru', 'prefix': '', 'typed': 'аббр'}
        self.assertIn(key_for(original, 'regression'), entry['keys'])
        self.assertIn(surface_key('ru', original['typed']), entry['surfaceKeys'])
        before = self.ledger | {'entries': [item for item in self.ledger['entries'] if item is not entry]}
        new_context = original | {'prefix': 'Новый контекст'}
        with self.assertRaisesRegex(ValueError, '^CONTROL_COVERAGE_INCOMPLETE$'):
            assert_disjoint([new_context], before, 'regression')
        with self.assertRaisesRegex(ValueError, '^CONTROL_OVERLAP:regression$'):
            assert_disjoint([original], self.ledger, 'regression')
        with self.assertRaisesRegex(ValueError, '^CONTROL_SURFACE_OVERLAP$'):
            assert_disjoint([new_context], self.ledger, 'regression')
        punctuation = {'language': 'ru', 'prefix': 'Новый контекст',
                       'currentWord': 'аббр', 'expectedBoundary': '. '}
        with self.assertRaisesRegex(ValueError, '^CONTROL_SURFACE_OVERLAP$'):
            assert_disjoint([punctuation], self.ledger, 'punctuation')

    def test_disclosed_domain_labels_block_new_punctuation_contexts(self):
        entry, = [entry for entry in self.ledger['entries']
                  if entry['id'] == 'public-a4-tranco-jzw4y-short-rf-labels-v1']
        frozen = json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
        self.assertEqual(hashlib.sha256(frozen).hexdigest(),
                         '35832890e53cad9283125f9f19272afb0f41e1e8d03051cb58d644600e5d4278')
        self.assertEqual(50, len(entry['keys']))
        self.assertEqual(50, len(entry['surfaceKeys']))
        punctuation = {'language': 'ru', 'prefix': 'Новый контекст',
                       'currentWord': 'яокб', 'expectedBoundary': '. '}
        before = self.ledger | {'entries': [item for item in self.ledger['entries'] if item is not entry]}
        with self.assertRaisesRegex(ValueError, '^CONTROL_COVERAGE_INCOMPLETE$'):
            assert_disjoint([punctuation], before, 'punctuation')
        with self.assertRaisesRegex(ValueError, '^CONTROL_SURFACE_OVERLAP$'):
            assert_disjoint([punctuation], self.ledger, 'punctuation')

    def test_disclosed_registry_domain_labels_bind_both_replay_inputs(self):
        entry, = [item for item in self.ledger['entries']
                  if item['id'] == 'public-a4-cctld-rf-deletion-lists-20261124-25-v1']
        frozen = json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
        self.assertEqual('2d6f7349ff94688f5d1077a95da65f3d09d51466603b31b3d75b776edc3d7015',
                         hashlib.sha256(frozen).hexdigest())
        self.assertEqual(506, entry['rowCount'])
        self.assertEqual(506, len(entry['keys']))
        self.assertEqual(506, len(entry['surfaceKeys']))
        self.assertEqual({'cctld/RFDelList20261124.zip', 'cctld/RFDelList20261125.zip',
                          'first-period.jsonl', 'full-domain-space.jsonl'}, set(entry['bindings']))

    def test_followup_registry_domain_replay_excludes_labels_and_complete_names(self):
        entry, = [item for item in self.ledger['entries']
                  if item['id'] == 'public-a4-cctld-rf-deletion-lists-20261118-20-v1']
        frozen = json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
        self.assertEqual('7eb983ab5e019e49ca04072f3cb39f8b31a3f6548f998af668b05d96ff16b128',
                         hashlib.sha256(frozen).hexdigest())
        self.assertEqual(113, entry['rowCount'])
        self.assertEqual(113, len(entry['keys']))
        self.assertEqual(226, len(entry['surfaceKeys']))

    def test_law_enumeration_colons_bind_exact_contexts_only(self):
        entry, = [item for item in self.ledger['entries']
                  if item['id'] == 'public-a4-law79-enumeration-colons-v1']
        frozen = json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
        self.assertEqual('d6ef33e48121e916d7b2a41335422c0303eea08141a929b5256a4b4fac253447',
                         hashlib.sha256(frozen).hexdigest())
        self.assertEqual(18, entry['rowCount'])
        self.assertEqual(18, len(entry['keys']))
        self.assertNotIn('surfaceKeys', entry)

    def test_direct_speech_colons_bind_exact_contexts_only(self):
        entry, = [item for item in self.ledger['entries']
                  if item['id'] == 'public-a4-wikisource-direct-speech-colons-v1']
        frozen = json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
        self.assertEqual('b7e51a8f0dd33d497a07e310bb6ba16eea870db9afb45c8c7a0fba046b2639ee',
                         hashlib.sha256(frozen).hexdigest())
        self.assertEqual(32, entry['rowCount'])
        self.assertEqual(32, len(entry['keys']))
        self.assertEqual({'inline': 30, 'nextParagraphDash': 2}, entry['sourceCapture'])
        self.assertNotIn('surfaceKeys', entry)

    def test_russian_forum_punctuation_binds_exact_contexts_only(self):
        entry, = [item for item in self.ledger['entries']
                  if item['id'] == 'public-a4-rus-stackexchange-comment-boundaries-v1']
        frozen = json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
        self.assertEqual('58cf284289e553813285f20b0ff12d147e4103efdb87f7fb2b600ff51829fde5',
                         hashlib.sha256(frozen).hexdigest())
        self.assertEqual({'period': 71, 'colon': 6}, entry['sourceCapture'])
        self.assertEqual(77, entry['rowCount'])
        self.assertEqual(77, len(entry['keys']))
        self.assertNotIn('surfaceKeys', entry)

    def test_archived_protected_matrices_match_every_persisted_key(self):
        directory=Path(__file__).with_name('frozen_sources')
        versions=[('qualification-v2',2,'2cbcb2508ef66b32a60b5c7665ad96c66dc1c6477c9da4ad6dde0ea969806e65'),
            ('compact-v3',3,'60cb1cdf671dcc0781d47225d225eebc178392f7b616a7ae77d084e4906126a7'),
            ('compact-v4',4,'9615bc8033760257bc384ece09d67f6b92e0b7541e144ea6ec746a2f4cc06de4')]
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);shutil.copytree(directory,root/'tools/typing_experiments/frozen_sources',ignore=shutil.ignore_patterns('__pycache__'))
            for name,version,digest in versions:
                manifest=dict(sources={f'tools/eval/smart-typing-0.3/qualification-v{version}/generate_corpus.py':digest})
                generator,_=load_original(root,manifest)
                for lang in ('en','ru','es'):
                    entry=next(e for e in self.ledger['entries'] if e['id']==name+'-protected-'+lang)
                    self.assertEqual(set(entry['keys']),{key_for(row,'protected') for row in generator.protected_rows(lang)})


if __name__=='__main__':unittest.main()
