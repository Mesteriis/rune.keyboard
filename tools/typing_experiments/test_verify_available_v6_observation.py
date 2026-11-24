import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import pyarrow as pa
import pyarrow.parquet as pq
import verify_available_v6_observation as subject


class AvailableV6ObservationSourceTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.source = Path(self.directory.name) / 'source.parquet'
        self.row = json.loads(subject.OBSERVATION.read_bytes())

    def write_source(self, ids=None, text=None):
        ids = ids if ids is not None else [self.row['article']]
        text = text if text is not None else self.row['prefix'] + ' ' + self.row['word'] + self.row['rightContext']
        table = pa.table({'id': ids, 'url': [subject.ARTICLE_URL] * len(ids),
                          'title': [subject.ARTICLE_TITLE] * len(ids), 'text': [text] * len(ids)})
        pq.write_table(table, self.source)

    def assess(self):
        with mock.patch.object(subject, 'SOURCE_BYTES', self.source.stat().st_size), \
             mock.patch.object(subject, 'SOURCE_SHA256', subject.file_sha(self.source)):
            return subject.verify(self.source)

    def test_unique_source_context_passes_without_qualification(self):
        self.write_source()
        report = self.assess()
        self.assertEqual((1, 1), (report['matchingArticles'], report['matchingContexts']))
        self.assertFalse(report['independentQualification'])
        self.assertFalse(report['sourceDecoderAttested'])

    def test_wrong_context_missing_and_duplicate_article_are_refused(self):
        matched = self.row['prefix'] + ' ' + self.row['word'] + self.row['rightContext']
        for ids, text in (([self.row['article']], 'unrelated'), (['999999999'], None),
                          ([self.row['article'], self.row['article']], None),
                          ([self.row['article']], matched + ' ' + matched)):
            with self.subTest(ids=ids, text_is_missing=text is None):
                self.write_source(ids, text)
                with self.assertRaisesRegex(ValueError, 'V6_SOURCE_ARTICLE_OR_CONTEXT'):
                    self.assess()

    def test_source_and_observation_hash_mismatches_are_refused(self):
        self.write_source()
        with mock.patch.object(subject, 'SOURCE_BYTES', self.source.stat().st_size), \
             mock.patch.object(subject, 'SOURCE_SHA256', '0' * 64):
            with self.assertRaisesRegex(ValueError, 'V6_SOURCE_IDENTITY'):
                subject.verify(self.source)
        observation = Path(self.directory.name) / 'observation.json'
        observation.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'V6_OBSERVATION_IDENTITY'):
            subject.verify(self.source, observation)

    def test_source_drift_after_initial_hash_is_refused(self):
        self.write_source()
        real = subject.file_sha
        calls = 0
        def changed(path):
            nonlocal calls
            if Path(path) == self.source:
                calls += 1
                if calls > 1:
                    return '0' * 64
            return real(path)
        expected = real(self.source)
        with mock.patch.object(subject, 'SOURCE_BYTES', self.source.stat().st_size), \
             mock.patch.object(subject, 'SOURCE_SHA256', expected), \
             mock.patch.object(subject, 'file_sha', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'V6_SOURCE_DRIFT'):
                subject.verify(self.source)
