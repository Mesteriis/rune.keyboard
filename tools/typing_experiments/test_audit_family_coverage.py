from types import SimpleNamespace
import unittest
from audit_family_coverage import classify_rows,source_path


class Dictionary:
    def analyses(self,word):return [SimpleNamespace(lemma='слово')] if word=='слова' else []


class FamilyCoverageTest(unittest.TestCase):
    def protected(self,**changes):
        return dict(id='p',cohort='protected',group='protected',word='слова',typed='@слова',expectedSpelling='@слова',noAuto=True)|changes

    def test_protected_mentions_are_nonlexical_and_not_unknown_lemmas(self):
        result=classify_rows([self.protected()],Dictionary())
        self.assertEqual({'protected-nonlexical-control':1},result['counts'])
        self.assertEqual([],result['unresolved']);self.assertEqual(['p'],result['protectedControlIds'])

    def test_ordinary_unknown_words_remain_unresolved_without_stripping_tokens(self):
        rows=[dict(id='a',expectedSpelling='слова'),dict(id='b',expectedSpelling='дарси'),dict(id='c',expectedSpelling='@дарси')]
        result=classify_rows(rows,Dictionary())
        self.assertEqual({'dictionary-supported-lexical':1,'unresolved-lexical':1,'unresolved-nonlexical':1},result['counts'])

    def test_incorrect_protected_metadata_duplicate_ids_and_missing_targets_fail(self):
        for changes in (dict(noAuto=False),dict(group='typo'),dict(word='иной'),dict(typed='слова'),dict(expectedSpelling='@иной')):
            with self.assertRaisesRegex(ValueError,'PROTECTED_CONSTRUCTION'):classify_rows([self.protected(**changes)],Dictionary())
        for rows in ([self.protected()]*2,[dict(id='x')]):
            with self.assertRaises(ValueError):classify_rows(rows,Dictionary())

    def test_only_explicit_public_parents_are_selected(self):
        self.assertIsNone(source_path(dict(id='private-conversation',bindings={})))
        self.assertIsNone(source_path(dict(id='public-joint-history-corpus-train-families',bindings={})))
        self.assertEqual('a/train-rows.jsonl',source_path(dict(id='public-ranker-history-train',bindings={'a/train-rows.jsonl':'a'*64,'a/test-rows.jsonl':'b'*64})))
        with self.assertRaisesRegex(ValueError,'SOURCE_BINDING'):source_path(dict(id='public-spelling-v7',bindings={}))


if __name__=='__main__':unittest.main()
