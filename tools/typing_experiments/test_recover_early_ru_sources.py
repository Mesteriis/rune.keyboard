import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from recover_early_ru_sources import article_selected,archived_source,prepare_selection


class EarlySourceRecoveryTest(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        shutil.copytree(Path(__file__).with_name('frozen_sources'),self.root/'tools/typing_experiments/frozen_sources',
                        ignore=shutil.ignore_patterns('__pycache__'))

    def test_calibration_and_holdout_templates_recover_without_mutating_originals(self):
        import importlib.util
        original='tools/eval/smart-typing-0.3/qualification-v3/generate_corpus.py'
        digest='60cb1cdf671dcc0781d47225d225eebc178392f7b616a7ae77d084e4906126a7'
        spec=importlib.util.spec_from_file_location('frozen_test',archived_source(self.root,original,digest))
        generator=importlib.util.module_from_spec(spec);spec.loader.exec_module(generator)
        text='Один два три четыре целевое слово.'
        selected=generator.spelling_candidates(text,'ru',{'целевое'},set(),3052026)[0]
        for split in ('calibration','holdout'):
            row=dict(id='a',language='ru',task='spelling',split=split,cohort='correct',typed='целевое',
                     prefix=selected['prefix'],family=selected['family'],template=split+'-wikipedia-'+selected['selectionHash'])
            before=dict(row)
            recovery=prepare_selection([row],generator,3052026,digest)
            self.assertEqual(1,len(recovery.recover_article('123',text)))
            self.assertEqual(before,row)
            with self.assertRaises(ValueError):prepare_selection([row|dict(template='wrong')],generator,3052026,digest)
            with self.assertRaises(ValueError):prepare_selection([row|dict(language='en')],generator,3052026,digest)

    def test_original_article_hash_partition_is_respected(self):
        selection=dict(seed=3042026,modulus=4,residue=0)
        for article in ('1','123','8825104'):
            rank=int.from_bytes(hashlib.sha256(f'3042026:ru:{article}'.encode()).digest()[:8],'big')
            self.assertEqual(rank%4==0,article_selected(article,selection))
            self.assertEqual(1,sum(article_selected(article,selection|dict(residue=r)) for r in range(4)))
        for change in (dict(modulus=0),dict(modulus=True),dict(residue=4),dict(seed='3042026')):
            with self.assertRaises(ValueError):article_selected('123',selection|change)

    def test_source_lock_archives_match_original_hashes_and_ru_source_metadata(self):
        directory=Path(__file__).with_name('frozen_sources')
        entries=json.loads((directory/'manifest.json').read_text())['sources']
        for version in (2,3,4):
            original=f'tools/eval/smart-typing-0.3/qualification-v{version}/source-lock.json'
            digest=next(h for h,e in entries.items() if e['originalPath']==original)
            path=archived_source(self.root,original,digest);lock=json.loads(path.read_text())
            self.assertEqual(digest,hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertTrue(lock['files'][lock['languageFiles']['ru']]['repositoryPath'].startswith('20231101.ru/'))
            self.assertEqual(4,lock['articleSelection']['modulus'])

    def test_changed_archive_bytes_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);target=root/'tools/typing_experiments/frozen_sources'
            shutil.copytree(Path(__file__).with_name('frozen_sources'),target,ignore=shutil.ignore_patterns('__pycache__'))
            entries=json.loads((target/'manifest.json').read_text())['sources']
            digest,entry=next((h,e) for h,e in entries.items() if e['originalPath'].endswith('qualification-v2/source-lock.json'))
            (target/entry['file']).write_text('{}')
            with self.assertRaisesRegex(ValueError,'ARCHIVE_IDENTITY'):archived_source(root,entry['originalPath'],digest)


if __name__=='__main__':unittest.main()
