import unittest
from control_ledger import article_key
from holdout_ledger import KEY_SCHEMA,keys_for,validate_ledger


def tt(**changes):return dict(sourceRepository='tatoeba',language='ru',article='tatoeba:123',sentenceHash='a'*64)|changes


class SourceIdentityTest(unittest.TestCase):
    def test_tatoeba_and_wikipedia_numeric_ids_do_not_alias(self):
        self.assertNotEqual(keys_for([tt()],'article'),keys_for([dict(article='123')],'article'))
        self.assertEqual(keys_for([tt()],'article'),keys_for([tt(article='tatoeba:00123')],'article'))
        with self.assertRaises(ValueError):keys_for([dict(article='tatoeba:123')],'article')

    def test_full_sentence_hashes_do_not_alias_source_windows_or_depend_on_id(self):
        self.assertNotEqual(keys_for([tt()],'sentence'),keys_for([dict(contextHash='a'*64)],'sentence'))
        self.assertEqual(keys_for([tt()],'sentence'),keys_for([tt(article='tatoeba:124')],'sentence'))

    def test_invalid_language_unknown_source_zero_and_mismatched_id_are_rejected(self):
        for change in (dict(language='en'),dict(sourceRepository='unknown'),dict(article='tatoeba:0'),dict(article='123'),dict(sentenceHash='bad')):
            with self.assertRaises(ValueError):keys_for([tt(**change)],'sentence')

    def test_control_source_articles_use_the_same_explicit_source_scope(self):
        self.assertNotEqual(article_key(tt()),article_key(dict(language='ru',article='123')))
        self.assertEqual(article_key(tt()),article_key(tt(article='tatoeba:00123')))
        with self.assertRaises(ValueError):article_key(dict(language='ru',article='tatoeba:123'))

    def test_source_only_entries_cannot_smuggle_target_axes_or_fake_missing_coverage(self):
        entry=dict(id='source',usage='historical-source-exclusion',keys={k:sorted(keys_for([tt()],k)) for k in ('article','sentence')},bindings={'source':'b'*64},missingAxes=[])
        ledger=dict(schema=1,keySchema=KEY_SCHEMA,publicDataOnly=True,coverage=dict(complete=False,pending=['pending']),entries=[entry])
        validate_ledger(ledger);entry['keys']['context']=['c'*64]
        with self.assertRaisesRegex(ValueError,'SOURCE_SCOPE'):validate_ledger(ledger)


if __name__=='__main__':unittest.main()
