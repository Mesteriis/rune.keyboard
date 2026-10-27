from pathlib import Path
import shutil
import tempfile
import unittest
from control_ledger import load,key_for,article_key,assert_disjoint
from import_control_components import load_original


class PublicControlSnapshotTest(unittest.TestCase):
    def setUp(self):self.ledger=load(Path(__file__).with_name('control-ledger.json'))

    def test_all_punctuation_components_and_languages_are_persisted(self):
        entries=[e for e in self.ledger['entries'] if e['kind']=='punctuation']
        self.assertEqual(9,len(entries));self.assertEqual(3600,sum(e['rowCount'] for e in entries))
        self.assertEqual({'en','ru','es'},{e['language'] for e in entries})

    def test_known_ru_punctuation_identity_survives_without_original_corpora(self):
        keys={k for e in self.ledger['entries'] if e['kind']=='punctuation' for k in e['keys']}
        self.assertIn('42a780b228b43e70eb7ce7449434f545fbdc4fc7af1cb2b214e84b230401a618',keys)
        self.assertFalse(self.ledger['coverageComplete'])

    def test_all_protected_language_components_are_persisted(self):
        entries=[e for e in self.ledger['entries'] if e['kind']=='protected']
        self.assertEqual(9,len(entries));self.assertEqual(5400,sum(e['rowCount'] for e in entries))
        self.assertEqual(1800,len({k for e in entries for k in e['keys']}))

    def test_all_punctuation_articles_are_persisted_with_language_namespace(self):
        entries=[e for e in self.ledger['entries'] if e['kind']=='punctuation']
        self.assertEqual(3476,sum(len(e['articleKeys']) for e in entries))
        self.assertIn(article_key(dict(language='ru',article='4476020')),{k for e in entries for k in e['articleKeys']})
        self.assertTrue(all('articleKeys' not in e for e in self.ledger['entries'] if e['kind']=='protected'))

    def test_protected_ru_token_is_blocked_without_original_corpora(self):
        with self.assertRaisesRegex(ValueError,'CONTROL_OVERLAP:protected'):
            assert_disjoint([dict(language='ru',prefix='Сохраните точный токен в примере 0',typed='Amelia')],self.ledger,'protected')

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
