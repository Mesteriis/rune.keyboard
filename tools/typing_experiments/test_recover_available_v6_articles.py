import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import pyarrow as pa
import pyarrow.parquet as pq
import holdout_ledger
import recover_available_v6_articles as subject
import recover_available_v6_calibration_attribution as attribution


class RecoverAvailableV6ArticlesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'sample.parquet'
        self.write_source(['100', '101', '102'])

    def write_source(self, ids):
        pq.write_table(pa.table({'id': ids, 'text': ['ignored'] * len(ids)}), self.source)

    def shard(self):
        return dict(name='0011.parquet', bytes=self.source.stat().st_size,
                    sha256=subject.sha_file(self.source))

    def key(self, article):
        return next(iter(holdout_ledger.keys_for([{'article': article}], 'article')))

    def test_recovers_only_registered_articles_with_partition(self):
        targets = {self.key('100'): 'calibration', self.key('102'): 'holdout'}
        rows, count = subject.scan_shard(self.source, self.shard(), targets, set())
        self.assertEqual(3, count)
        self.assertEqual([('100', 'calibration'), ('102', 'holdout')],
                         [(r['article'], r['partition']) for r in rows])
        self.assertTrue(all(r['shard'] == '0011.parquet' for r in rows))

    def test_refuses_wrong_source_or_duplicate_article(self):
        shard = self.shard() | {'sha256': '0' * 64}
        with self.assertRaisesRegex(ValueError, 'V6_ARTICLE_SOURCE_IDENTITY'):
            subject.scan_shard(self.source, shard, {}, set())
        self.write_source(['100', '100'])
        with self.assertRaisesRegex(ValueError, 'V6_ARTICLE_DUPLICATE_SOURCE'):
            subject.scan_shard(self.source, self.shard(), {self.key('100'): 'calibration'}, set())

    def test_refuses_source_drift(self):
        shard = self.shard()
        real = subject.sha_file
        calls = 0
        def changed(path):
            nonlocal calls
            calls += 1
            return real(path) if calls == 1 else '0' * 64
        with mock.patch.object(subject, 'sha_file', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'V6_ARTICLE_SOURCE_DRIFT'):
                subject.scan_shard(self.source, shard, {}, set())

    def test_calibration_attribution_reads_the_bound_page_metadata(self):
        pq.write_table(pa.table({
            "id": ["100", "101"], "title": ["Пример", "Вторая статья"],
            "url": ["https://ru.wikipedia.org/wiki/Пример", "https://ru.wikipedia.org/wiki/Вторая_статья"],
        }), self.source)
        rows, source_rows = attribution.scan_shard(self.source, self.shard(), {"100"})
        self.assertEqual(2, source_rows)
        self.assertEqual([{
            "article": "100", "title": "Пример", "url": "https://ru.wikipedia.org/wiki/Пример",
            "shard": "0011.parquet",
        }], rows)
        with self.assertRaisesRegex(ValueError, "V6_CALIBRATION_ATTRIBUTION_SHARD"):
            attribution.scan_shard(self.source, self.shard() | {"sha256": "0" * 64}, {"100"})
        with self.assertRaisesRegex(ValueError, "HISTORICAL_ATTRIBUTION_COVERAGE"):
            attribution.scan_shard(self.source, self.shard(), {"102"})

    def test_target_overlap_and_missing_source_binding_are_rejected(self):
        key = self.key('100')
        def entry(part, keys):
            return dict(id=subject.ENTRY + part, keys={'article': keys})
        ledger = {'entries': [entry('calibration', [key]), entry('holdout', [key])]}
        with self.assertRaisesRegex(ValueError, 'V6_ARTICLE_PARTITION_OVERLAP'):
            subject.target_index(ledger)
        lock = {'shards': [{'name': '0011.parquet', 'sha256': 'a' * 64}]}
        with self.assertRaisesRegex(ValueError, 'V6_ARTICLE_HISTORICAL_SOURCE_BINDING'):
            subject.verify_historical_source_bindings(lock, {'entries': []})
        with self.assertRaisesRegex(ValueError, 'V6_ARTICLE_HISTORICAL_SOURCE_BINDING'):
            subject.verify_historical_source_bindings(lock, {'entries': [
                {'bindings': {'build/ru-0011.parquet': 'b' * 64}}]})
        subject.verify_historical_source_bindings(lock, {'entries': [
            {'bindings': {'build/ru-0011.parquet': 'a' * 64}}]})


if __name__ == '__main__':
    unittest.main()
