import unittest
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
from holdout_ledger import keys_for
import import_joint_history as importer
from import_joint_history import partition_entries
from recover_legacy_families import sha


class Dictionary:
    def analyses(self,word):
        return [SimpleNamespace(lemma='стать'),SimpleNamespace(lemma='сталь')] if word=='стали' else []


class JointHistoryTest(unittest.TestCase):
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
