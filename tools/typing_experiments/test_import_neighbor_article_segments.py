import unittest
import import_neighbor_article_segments as subject


class NeighborSegmentsTest(unittest.TestCase):
    def test_collects_segments_from_exact_requested_articles(self):
        found = subject.collect_source({'7'}, [(['7', '8'], ['Первое. Второе!', 'ignored'])])
        self.assertEqual(2, len(found))
        self.assertNotIn('Первое', str(found))

    def test_cross_shard_article_identity_is_rejected(self):
        rows = [{'article': '7', 'shard': 11}, {'article': '7', 'shard': 12}]
        with self.assertRaisesRegex(ValueError, 'NEIGHBOR_SEGMENT_CROSS_SHARD_ARTICLE'):
            subject.partition_articles(rows)
        self.assertEqual({'7'}, subject.partition_articles(rows[:1])[0])

    def test_missing_duplicate_and_empty_sources_fail(self):
        for ids, batches in [({'7'}, [(['8'], ['other'])]),
                             ({'7'}, [(['7', '7'], ['first', 'second'])]),
                             (set(), []), ({'7'}, [(['7'], [''])])]:
            with self.subTest(ids=ids, batches=batches), self.assertRaises(ValueError):
                subject.collect_source(ids, batches)


if __name__ == '__main__':
    unittest.main()
