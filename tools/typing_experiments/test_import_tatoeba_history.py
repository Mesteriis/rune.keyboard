import bz2
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from import_tatoeba_history import partition_entries,sentence_hash,verify_sources


class Dictionary:
    def analyses(self,word):return [SimpleNamespace(lemma='слово')] if word=='слова' else []


def row(**changes):
    return dict(id='a',article='tatoeba:123',sentenceHash='a'*64,language='ru',split='train',word='слова',family='999',
                prefix='Это',typed='слвоа',expectedSpelling='слова',cohort='typo',group='typo')|changes


class TatoebaHistoryTest(unittest.TestCase):
    def entries(self,rows=None,trained=True):return partition_entries('fixture','train',rows or [row()],trained,Dictionary(),{'file':'b'*64})

    def test_native_family_ids_are_not_lemmas_and_supervised_promotion_is_explicit(self):
        entries,counts=self.entries();self.assertEqual('supervised',entries[1]['usage'])
        self.assertEqual(1,counts['dictionaryFamilies']);self.assertEqual([],entries[0]['missingAxes'])
        self.assertEqual(1,len(self.entries(trained=False)[0]))

    def test_protected_source_words_are_analyzed_without_guessing_mentions_as_lemmas(self):
        entries,counts=self.entries([row(typed='@слова',expectedSpelling='@слова',cohort='protected',group='protected',noAuto=True)])
        self.assertEqual([],counts['unresolvedRows']);self.assertEqual(1,counts['dictionaryFamilies'])
        _,counts=self.entries([row(typed='@слова',expectedSpelling='@слова',cohort='correct',group='protected',noAuto=True)])
        self.assertEqual([],counts['unresolvedRows'])
        with self.assertRaises(ValueError):self.entries([row(typed='@слова',expectedSpelling='@слова',cohort='protected',group='protected',noAuto=False)])

    def test_unknown_targets_and_bad_scope_remain_blocked(self):
        entries,counts=self.entries([row(word='дарси',expectedSpelling='слова')])
        self.assertEqual(['a'],counts['unresolvedRows']);self.assertEqual(['family'],entries[0]['missingAxes'])
        for change in (dict(language='en'),dict(split='holdout'),dict(article='123')):
            with self.assertRaises(ValueError):self.entries([row(**change)])

    def test_compressed_public_source_ids_and_normalized_sentence_hashes_are_verified(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.bz2';path.write_bytes(bz2.compress('123\trus\tЕ\u0308лка слова.\tdate\n'.encode()))
            verify_sources(path,{'123':sentence_hash('Ёлка слова.')},4)
            with self.assertRaisesRegex(ValueError,'PREFIX_CAPTURE'):
                verify_sources(path,{'123':sentence_hash('Ёлка слова.')},4,{'123':{'Чужой префикс'}})
            for wanted in ({'123':'0'*64},{'124':sentence_hash('Ёлка слова.')}):
                with self.assertRaises(ValueError):verify_sources(path,wanted,4)


if __name__=='__main__':unittest.main()
