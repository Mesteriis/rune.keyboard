import unittest
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from holdout_ledger import keys_for, KEY_SCHEMA
from import_early_ru_history import corpus_entries, read_corpus, CORPORA
import check_historical_qualification_archives as archived_corpora
import import_early_ru_history as subject


class Dictionary:
    def analyses(self,word):return [SimpleNamespace(lemma='слово')] if word=='слова' else []


class EarlyRuHistoryTest(unittest.TestCase):
    def rows(self):
        return [dict(id='a',language='ru',task='spelling',cohort='correct',typed='слова',prefix='Перед'),
                dict(id='b',language='ru',task='spelling',cohort='typo',typed='слвва',expectedSpelling='слова',prefix='Перед')]

    def test_correct_controls_and_typos_share_the_original_target_context_identity(self):
        entries,counts=corpus_entries('fixture',self.rows(),{'rows':'a'*64},Dictionary())
        self.assertEqual(1,len(entries[0]['keys']['context']));self.assertEqual(2,counts['resolvedRows'])
        self.assertEqual(keys_for([dict(prefix='Перед',expectedSpelling='слова',typed='иная')],'context'),set(entries[0]['keys']['context']))
        self.assertEqual(['article','family','sentence'],entries[0]['missingAxes'])

    def test_other_languages_and_nonspelling_tasks_fail_before_hashing(self):
        for changes in (dict(language='en'),dict(language='es'),dict(task='punctuation')):
            rows=self.rows();rows[0].update(changes)
            with self.assertRaisesRegex(ValueError,'SCOPE'):corpus_entries('fixture',rows,{'rows':'a'*64},Dictionary())

    def test_duplicate_rows_missing_targets_and_empty_corpora_fail(self):
        for rows in ([],self.rows()*2,[self.rows()[1]|dict(expectedSpelling=None)]):
            with self.assertRaises(ValueError):corpus_entries('fixture',rows,{'rows':'a'*64},Dictionary())

    def test_legacy_surface_family_is_not_trusted_as_a_lemma(self):
        rows=[self.rows()[1]|dict(expectedSpelling='дарси',family='вымышленная-лемма')]
        entries,counts=corpus_entries('fixture',rows,{'rows':'a'*64},Dictionary())
        self.assertEqual(1,len(entries));self.assertEqual(['b'],counts['unresolvedRows'])

    def test_verified_archive_fallback_and_partial_original_fail_closed(self):
        source = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            dest = root / 'tools/typing_experiments'
            dest.mkdir(parents=True)
            shutil.copytree(source / 'historical-qualification-v3-v4', dest / 'historical-qualification-v3-v4')
            shutil.copy2(source / 'check_historical_qualification_archives.py', dest)
            for name in ('compact-v3', 'compact-v4'):
                directory, expected, _ = CORPORA[name]
                manifest, rows, bindings, storage = read_corpus(root, name, directory, expected)
                self.assertEqual('verified-archive', storage)
                self.assertEqual(3400, len(rows.splitlines()))
                self.assertEqual(manifest['files']['spelling-ru.jsonl'], hashlib.sha256(rows).hexdigest())
                self.assertEqual(3, len(bindings))
                self.assertTrue(any(key.endswith('catalog.json') for key in bindings))
            directory, expected, _ = CORPORA['compact-v3']
            partial = root / directory / 'manifest.json'; partial.parent.mkdir(parents=True)
            partial.write_bytes(b'incomplete')
            with self.assertRaisesRegex(ValueError, 'EARLY_RU_PARTIAL_CORPUS'):
                read_corpus(root, 'compact-v3', directory, expected)
            partial.unlink()
            data = archived_corpora.load(dest / 'historical-qualification-v3-v4')['v3']
            partial.write_bytes(data['manifest.json'])
            rows_path = partial.parent / 'spelling-ru.jsonl'; rows_path.write_bytes(data['spelling-ru.jsonl'])
            _, _, bindings, storage = read_corpus(root, 'compact-v3', directory, expected)
            self.assertEqual('historical-files', storage)
            self.assertEqual({directory + '/manifest.json', directory + '/spelling-ru.jsonl'}, set(bindings))
            partial.write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError, 'EARLY_RU_MANIFEST_IDENTITY'):
                read_corpus(root, 'compact-v3', directory, expected)
            partial.unlink(); rows_path.unlink()
            archive = dest / 'historical-qualification-v3-v4/qualification-v3.tar.bz2'
            archive.write_bytes(archive.read_bytes() + b'bad')
            with self.assertRaisesRegex(ValueError, 'HISTORICAL_ARCHIVE_IDENTITY'):
                read_corpus(root, 'compact-v3', directory, expected)

    def test_import_build_accepts_archives_with_mocked_public_source_identity(self):
        source = Path(__file__).resolve().parent
        project = source.parents[1]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / 'tools/typing_experiments'; target.mkdir(parents=True)
            shutil.copytree(source / 'historical-qualification-v3-v4', target / 'historical-qualification-v3-v4')
            for name in ('check_historical_qualification_archives.py', 'import_early_ru_history.py', 'recover_legacy_families.py'):
                shutil.copy2(source / name, target / name)
            (root / 'tools/morphology').mkdir(parents=True)
            shutil.copy2(project / 'tools/morphology/ranker.py', root / 'tools/morphology/ranker.py')
            frozen = target / 'frozen_sources'; frozen.mkdir()
            frozen_manifest = json.loads((source / 'frozen_sources/manifest.json').read_bytes())
            (frozen / 'manifest.json').write_bytes((source / 'frozen_sources/manifest.json').read_bytes())
            for digest in ('60cb1cdf671dcc0781d47225d225eebc178392f7b616a7ae77d084e4906126a7',
                           '9615bc8033760257bc384ece09d67f6b92e0b7541e144ea6ec746a2f4cc06de4'):
                name = frozen_manifest['sources'][digest]['file']
                shutil.copy2(source / 'frozen_sources' / name, frozen / name)
            corpora = {k: CORPORA[k] for k in ('compact-v3', 'compact-v4')}
            archives = archived_corpora.load(target / 'historical-qualification-v3-v4')
            mocked_sources = {}
            for name, (_, _, source_path) in corpora.items():
                label = 'v3' if name == 'compact-v3' else 'v4'
                manifest = json.loads(archives[label]['manifest.json'])
                mocked_sources[root / source_path] = manifest['source']['files'][Path(source_path).name]
            real_sha = subject.sha
            def guarded_sha(path):
                path = Path(path)
                return mocked_sources[path] if path in mocked_sources else real_sha(path)
            class EmptyDictionary:
                def analyses(self, word): return []
                def receipt(self): return {'testOnly': True}
            base = dict(schema=1, keySchema=KEY_SCHEMA, publicDataOnly=True,
                coverage={'complete': False, 'pending': ['fixture']}, entries=[
                    {'id': 'fixture', 'usage': 'historical-context-exclusion',
                     'keys': {'context': ['0' * 64]}, 'missingAxes': [], 'bindings': {'fixture': '0' * 64}}])
            with patch.object(subject, 'CORPORA', corpora):
                with self.assertRaises(FileNotFoundError):
                    subject.build(root, base, EmptyDictionary())
            with patch.object(subject, 'CORPORA', corpora), patch.object(subject, 'sha', side_effect=guarded_sha):
                ledger, receipt = subject.build(root, base, EmptyDictionary())
            self.assertEqual({'compact-v3': 'verified-archive', 'compact-v4': 'verified-archive'}, receipt['corpusStorage'])
            self.assertEqual([3400, 3400], [receipt['counts'][k]['rows'] for k in corpora])
            self.assertEqual(3, len(ledger['entries']))
            self.assertTrue(all(any(k.endswith('.tar.bz2') for k in e['bindings']) for e in ledger['entries'][1:]))

    def test_all_original_qualification_generator_bytes_are_preserved(self):
        directory=Path(__file__).with_name('frozen_sources');sources=json.loads((directory/'manifest.json').read_text())['sources']
        for version,digest in ((2,'2cbcb2508ef66b32a60b5c7665ad96c66dc1c6477c9da4ad6dde0ea969806e65'),
            (3,'60cb1cdf671dcc0781d47225d225eebc178392f7b616a7ae77d084e4906126a7'),
            (4,'9615bc8033760257bc384ece09d67f6b92e0b7541e144ea6ec746a2f4cc06de4')):
            entry=sources[digest]
            self.assertEqual(f'tools/eval/smart-typing-0.3/qualification-v{version}/generate_corpus.py',entry['originalPath'])
            blob=(directory/entry['file']).read_bytes();self.assertEqual(digest,hashlib.sha256(blob).hexdigest())
            compile(blob,'archived-qualification','exec')


if __name__=='__main__':unittest.main()
