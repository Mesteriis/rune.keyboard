import json
from pathlib import Path
import unittest
import a4_abbreviation_frequency as subject


class AbbreviationFrequencyTest(unittest.TestCase):
    def test_distinct_article_and_occurrence_counts(self):
        result = subject.scan([('1', 'СПБ. спб. и инн.'), ('2', '(спб.)')], ['спб', 'инн'])
        self.assertEqual(2, result['sourceRows'])
        self.assertEqual({'occurrences': 3, 'articles': 2}, result['forms']['спб'])
        self.assertEqual({'occurrences': 1, 'articles': 1}, result['forms']['инн'])

    def test_domain_hyphen_and_contained_words_do_not_count(self):
        result = subject.scan([('1', 'спб.рф x-спб. суперспб. спб.ру')], ['спб'])
        self.assertEqual({'occurrences': 0, 'articles': 0}, result['forms']['спб'])

    def test_bad_rows_and_duplicate_article_rejected(self):
        for rows in ([], [('1', 'спб.'), ('01', 'спб.')], [('0', 'спб.')], [('x', 'спб.')], [('1', None)]):
            with self.assertRaises(ValueError): subject.scan(rows, ['спб'])

    def test_tracked_controls_are_unique_and_bound(self):
        self.assertEqual(54, len(subject.targets()))
        with self.assertRaises(ValueError): subject.scan([('1', '')], ['спб', 'спб'])

    def test_retained_aggregate_is_source_bound_and_does_not_claim_qualification(self):
        path = subject.ROOT / 'tools/typing_experiments/a4_controls/wikipedia-0011-frequency.json'
        receipt = json.loads(path.read_text())
        lock = json.loads(subject.LOCK.read_text())
        shard = next(item for item in lock['shards'] if item['name'] == subject.SHARD)
        self.assertEqual(subject.sha(subject.CONTROLS), receipt['controlsSha256'])
        self.assertEqual(subject.sha(subject.LOCK), receipt['sourceLockSha256'])
        self.assertEqual(subject.sha(Path(subject.__file__)), receipt['helperSha256'])
        self.assertEqual(shard['sha256'], receipt['sourceSha256'])
        self.assertEqual(lock['repository'], receipt['sourceRepository'])
        self.assertEqual(lock['revision'], receipt['sourceRevision'])
        self.assertEqual(subject.SHARD, receipt['sourceShard'])
        self.assertEqual(92622, receipt['sourceRows'])
        self.assertEqual(set(subject.targets()), set(receipt['forms']))
        self.assertFalse(receipt['independentlyQualified'])
        self.assertFalse(receipt['sourceDecoderAttested'])
        for value in receipt['forms'].values():
            self.assertEqual({'articles', 'occurrences'}, set(value))
            self.assertTrue(0 <= value['articles'] <= value['occurrences'])


if __name__ == '__main__': unittest.main()
