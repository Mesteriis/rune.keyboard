import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import pyarrow as pa
import pyarrow.parquet as pq
import recover_available_v6_targets as subject


class RecoverV6TargetsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = subject.ROOT / 'tools/typing_experiments/historical_provenance_sources/available_clean_v6_logged_calibration_row.json'
        cls.row = json.loads(path.read_bytes())
        cls.generator = subject.prepare_external_spelling_holdout.load_generator()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'source.parquet'
        self.text = self.row['prefix'] + ' ' + self.row['word'] + self.row['rightContext']
        start = len(self.row['prefix']) + 1
        self.anchor = dict(article=self.row['article'], source='0018.parquet', wordStart=start,
            wordEnd=start + len(self.row['word']), contextHash=self.row['contextHash'],
            sentenceKey='a' * 64, articlePartition='calibration', sentencePartition='calibration')
        self.keys = subject.candidate_targets(self.text, self.anchor, self.generator)
        self.write_source([self.row['article']], [self.text])

    def write_source(self, ids, texts):
        pq.write_table(pa.table({'id': ids, 'text': texts}), self.source)

    def shard(self):
        return {'name': '0018.parquet', 'bytes': self.source.stat().st_size,
                'sha256': subject.articles.sha_file(self.source)}

    def scan(self, targets):
        return subject.scan_shard(self.source, self.shard(),
            [{'article': self.row['article'], 'partition': 'calibration'}], [self.anchor], targets, self.generator)

    def test_source_and_protected_keys_match_direct_ledger_calculation(self):
        for variant, target in (('source-word', self.row['word']), ('protected-source-word', '@' + self.row['word'])):
            expected = subject.holdout_ledger.keys_for([dict(prefix=self.row['prefix'], typed=target,
                expectedSpelling=target)], 'context')
            self.assertEqual(expected, {self.keys[variant]})
        matches, counts = self.scan({key: 'calibration' for key in self.keys.values()})
        self.assertEqual(2, len(matches))
        self.assertEqual(1, counts['checkedAnchors'])
        self.assertTrue(all('word' not in item and 'prefix' not in item and 'text' not in item for item in matches))

    def test_wrong_context_and_invalid_offset_are_refused(self):
        with self.assertRaisesRegex(ValueError, 'V6_TARGET_SOURCE_CONTEXT'):
            subject.candidate_targets(self.text + 'changed', self.anchor | {'contextHash': '0' * 64}, self.generator)
        with self.assertRaisesRegex(ValueError, 'V6_TARGET_SOURCE_OFFSET'):
            subject.candidate_targets(self.text, self.anchor | {'wordEnd': len(self.text) + 1}, self.generator)

    def test_missing_duplicate_and_source_drift_are_refused(self):
        self.write_source(['999999999'], ['other'])
        with self.assertRaisesRegex(ValueError, 'V6_TARGET_SOURCE_ARTICLES_MISSING'):
            self.scan({})
        self.write_source([self.row['article'], self.row['article']], [self.text, self.text])
        with self.assertRaisesRegex(ValueError, 'V6_TARGET_DUPLICATE_SOURCE_ARTICLE'):
            self.scan({})
        self.write_source([self.row['article']], [self.text])
        shard = self.shard()
        real = subject.articles.sha_file
        calls = 0
        def changed(path):
            nonlocal calls
            calls += 1
            return real(path) if calls == 1 else '0' * 64
        with mock.patch.object(subject.articles, 'sha_file', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'V6_TARGET_SOURCE_DRIFT'):
                subject.scan_shard(self.source, shard, [{'article': self.row['article']}],
                                   [self.anchor], {}, self.generator)

    def test_cross_partition_matches_do_not_count_as_unique(self):
        targets = {'a': 'calibration', 'b': 'holdout', 'c': 'holdout'}
        matches = [dict(targetKey='a', targetPartition='calibration', sourcePartition='holdout'),
                   dict(targetKey='b', targetPartition='holdout', sourcePartition='holdout'),
                   dict(targetKey='b', targetPartition='holdout', sourcePartition='holdout'),
                   dict(targetKey='c', targetPartition='holdout', sourcePartition='holdout')]
        self.assertEqual({'uniqueTargets': 1, 'ambiguousTargets': 1, 'unmatchedTargets': 1,
                          'crossPartitionMatches': 1}, subject.summarize(targets, matches))

    def test_context_key_partition_overlap_is_refused(self):
        def entry(part): return {'id': subject.articles.ENTRY + part, 'keys': {'context': ['a' * 64]}}
        with self.assertRaisesRegex(ValueError, 'V6_TARGET_PARTITION_OVERLAP'):
            subject.target_index({'entries': [entry('calibration'), entry('holdout')]})


if __name__ == '__main__':
    unittest.main()
