import unittest
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from holdout_ledger import keys_for
from import_early_ru_history import corpus_entries


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
