import unittest
from types import SimpleNamespace

from audit_truncated_text_sources import derive


class Lexicon:
    def analyses(self, word):
        return [SimpleNamespace(lemma='семья')] if word == 'альфа' else []


class TruncatedSourceTest(unittest.TestCase):
    def corpora(self, records):
        return {'word': {'train': records, 'dev': [], 'test': []},
                'refinement': {'train': [], 'dev': [], 'test': []},
                'epoch': {'train': [], 'dev': [], 'test': []}}

    def test_recovers_original_compound_and_dictionary_family(self):
        rows = derive(self.corpora([{'articleId':'1', 'text':'мы аль'}]),
                      {'1':'Мы альфа-код дальше.'}, Lexicon())
        self.assertEqual(1, len(rows))
        self.assertEqual('альфа-код', rows[0]['typed'])
        self.assertEqual('альфа', rows[0]['head'])
        self.assertEqual('аль', rows[0]['partial'])
        self.assertEqual(['семья'], rows[0]['families'])
        self.assertEqual(1, rows[0]['wordOrdinal'])

    def test_complete_word_and_space_boundary_do_not_count_as_truncation(self):
        rows = derive(self.corpora([{'articleId':'1', 'text':'мы альфа'}]),
                      {'1':'Мы альфа код дальше.'}, Lexicon())
        self.assertEqual([], rows)

    def test_missing_or_changed_source_and_duplicate_article_fail_closed(self):
        records = [{'articleId':'1', 'text':'мы аль'}]
        with self.assertRaisesRegex(ValueError, 'TRUNCATED_RECORD'):
            derive(self.corpora(records), {}, Lexicon())
        with self.assertRaisesRegex(ValueError, 'TRUNCATED_SOURCE_MISMATCH'):
            derive(self.corpora(records), {'1':'Другой источник'}, Lexicon())
        with self.assertRaisesRegex(ValueError, 'TRUNCATED_RECORD'):
            derive(self.corpora(records * 2), {'1':'Мы альфа'}, Lexicon())


if __name__ == '__main__':
    unittest.main()
