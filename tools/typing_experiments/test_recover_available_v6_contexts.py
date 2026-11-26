import json
import ast
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import pyarrow as pa
import pyarrow.parquet as pq
import recover_available_v6_contexts as subject


class RecoverAvailableV6ContextsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.row = json.loads((subject.ROOT / 'tools/typing_experiments/historical_provenance_sources/available_clean_v6_logged_calibration_row.json').read_bytes())
        cls.generator = subject.prepare_external_spelling_holdout.load_generator()
        cls.key = next(iter(subject.holdout_ledger.keys_for([{'contextHash': cls.row['contextHash']}], 'sentence')))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'source.parquet'
        self.text = self.row['prefix'] + ' ' + self.row['word'] + self.row['rightContext']
        self.article = self.row['article']
        self.write_source([self.article], [self.text])

    def write_source(self, ids, texts):
        pq.write_table(pa.table({'id': ids, 'text': texts}), self.source)

    def shard(self):
        return {'name': '0018.parquet', 'bytes': self.source.stat().st_size,
                'sha256': subject.articles.sha_file(self.source)}

    def scan(self):
        return subject.scan_shard(self.source, self.shard(),
            [{'article': self.article, 'partition': 'calibration'}],
            {self.key: 'calibration'}, self.generator)

    def test_logged_context_is_reconstructed_without_emitting_text(self):
        anchors, counts = self.scan()
        self.assertEqual(1, len(anchors))
        self.assertEqual(1, counts['articles'])
        self.assertEqual(self.row['contextHash'], anchors[0]['contextHash'])
        self.assertEqual(self.key, anchors[0]['sentenceKey'])
        self.assertNotIn('prefix', anchors[0])
        self.assertNotIn('text', anchors[0])
        self.assertLess(anchors[0]['wordStart'], anchors[0]['wordEnd'])

    def test_lowercase_length_change_is_reported_not_guessed(self):
        self.assertIsNone(subject.context_candidates('İ слово потом', self.generator))
        self.write_source([self.article], ['İ слово потом'])
        anchors, counts = self.scan()
        self.assertEqual([], anchors)
        self.assertEqual(1, counts['foldingRefusals'])

    def test_missing_duplicate_and_changed_source_are_refused(self):
        self.write_source(['999999999'], ['ordinary'])
        with self.assertRaisesRegex(ValueError, 'V6_CONTEXT_SOURCE_ARTICLES_MISSING'):
            self.scan()
        self.write_source([self.article, self.article], [self.text, self.text])
        with self.assertRaisesRegex(ValueError, 'V6_CONTEXT_DUPLICATE_SOURCE_ARTICLE'):
            self.scan()
        self.write_source([self.article], [self.text])
        shard = self.shard() | {'sha256': '0' * 64}
        with self.assertRaisesRegex(ValueError, 'V6_CONTEXT_SOURCE_IDENTITY'):
            subject.scan_shard(self.source, shard, [], {}, self.generator)

    def test_source_drift_after_decode_is_refused(self):
        shard = self.shard()
        real = subject.articles.sha_file
        calls = 0
        def changed(path):
            nonlocal calls
            calls += 1
            return real(path) if calls == 1 else '0' * 64
        with mock.patch.object(subject.articles, 'sha_file', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'V6_CONTEXT_SOURCE_DRIFT'):
                subject.scan_shard(self.source, shard,
                    [{'article': self.article, 'partition': 'calibration'}],
                    {self.key: 'calibration'}, self.generator)

    def test_sentence_keys_cannot_overlap_between_partitions(self):
        def entry(part):
            return {'id': subject.articles.ENTRY + part, 'keys': {'sentence': [self.key]}}
        with self.assertRaisesRegex(ValueError, 'V6_CONTEXT_PARTITION_OVERLAP'):
            subject.sentence_targets({'entries': [entry('calibration'), entry('holdout')]})

    def test_bounded_prefix_matches_both_retained_historical_sources(self):
        paths = [subject.prepare_external_spelling_holdout.GENERATOR,
            subject.ROOT / 'tools/typing_experiments/frozen_sources/qualification_v2_2cbcb2508ef66b32.py',
            subject.ROOT / 'tools/typing_experiments/frozen_sources/qualification_v2_ed9928d64d80911c.py']
        bodies = []
        for path in paths:
            tree = ast.parse(path.read_text())
            node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'bounded_prefix')
            bodies.append(ast.dump(node, include_attributes=False))
        self.assertEqual(bodies[0], bodies[1])
        self.assertEqual(bodies[0], bodies[2])

    def test_cross_partition_and_ambiguous_candidates_do_not_become_unique(self):
        targets = {'a': 'calibration', 'b': 'holdout', 'c': 'holdout'}
        anchors = [dict(sentenceKey='a', sentencePartition='calibration', articlePartition='holdout'),
                   dict(sentenceKey='b', sentencePartition='holdout', articlePartition='holdout'),
                   dict(sentenceKey='b', sentencePartition='holdout', articlePartition='holdout'),
                   dict(sentenceKey='c', sentencePartition='holdout', articlePartition='holdout')]
        self.assertEqual({'uniqueTargets': 1, 'ambiguousTargets': 1, 'missingTargets': 1,
                          'crossPartitionAnchors': 1}, subject.summarize(targets, anchors))


if __name__ == '__main__':
    unittest.main()
