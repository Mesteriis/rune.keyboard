from pathlib import Path
import json
import shutil
import tempfile
import unittest
from unittest import mock

import register_retrieval_suspended_source as subject
from public_corpus_preparation_v1 import preflight


class SuspendedSourceTest(unittest.TestCase):
    def test_exact_source_and_registry_exclude_both_observed_forms(self):
        rows, _ = subject.inputs()
        self.assertEqual(['аудио-', 'видеофайлов'], [r['typed'] for r in rows])
        self.assertEqual(2, subject.check())
        controls = subject.control.load(subject.CONTROL)
        for row in rows:
            with self.subTest(word=row['typed']):
                with self.assertRaisesRegex(ValueError, 'CONTROL_OVERLAP:regression'):
                    subject.control.assert_disjoint([row], controls, 'regression')
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:context'):
            subject.lexical.assert_disjoint([rows[1]], subject.lexical.load_ledger(subject.LEXICAL),
                                            kinds=('context',), require_complete=False)
        self.assertIn(subject.unsupported_surface_key('видеофайлов'),
                      subject.entries()[1]['unsupportedSurfaceKeys'])

    def test_modified_article_fails_source_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / 'fixture'
            shutil.copytree(subject.FIXTURE, fixture)
            article = fixture / 'article.json'
            value = json.loads(article.read_text()).replace('аудио- и видеофайлов', 'аудио и видеофайлов')
            article.write_text(json.dumps(value, ensure_ascii=False) + '\n')
            with mock.patch.object(subject, 'FIXTURE', fixture):
                with self.assertRaisesRegex(ValueError, 'SUSPENDED_SOURCE_ARTICLE_IDENTITY'):
                    subject.inputs()

    def test_new_surface_is_blocked_even_with_new_article_and_context(self):
        lexical = subject.lexical.load_ledger(subject.LEXICAL)
        controls = subject.control.load(subject.CONTROL)
        row = dict(id='fresh', language='ru', article='999999999', families=['редчайший'],
                   contextHash='0'*64, sourceSegmentHash='f'*64, prefix='другой контекст',
                   typed='видеофайлов', expectedSpelling='видеофайлов')
        result = preflight([row], 'spelling', lexical, controls, 'new-families')
        self.assertEqual('BLOCKED_OVERLAP', result['status'])
        self.assertEqual(1, result['unsupportedTargetOverlaps'])
        self.assertEqual(1, result['controlOverlaps']['surface'])
        lexical['entries'] = [e for e in lexical['entries'] if e['id'] != subject.ENTRY+'-contexts']
        controls['entries'] = [e for e in controls['entries'] if e['id'] != subject.ENTRY]
        previous = preflight([row], 'spelling', lexical, controls, 'new-families')
        self.assertEqual(0, previous['unsupportedTargetOverlaps'])
        self.assertEqual(0, previous['controlOverlaps']['surface'])

    def test_unexpected_or_ambiguous_source_boundary_is_refused(self):
        rows, _ = subject.inputs()
        parent = subject.parent_row()
        article = subject.article_snapshot()
        needle = parent['prefix'] + 'аудио- и видеофайлов'
        for altered in (article.replace(needle, needle.replace('аудио- и', 'аудио-видео и')),
                        article + '\n' + needle):
            with self.subTest(altered=altered[-20:]):
                with self.assertRaisesRegex(ValueError, 'SUSPENDED_SOURCE_BOUNDARY'):
                    subject.project(parent, altered)
        self.assertEqual(2, len(rows))

    def test_source_article_stream_requires_exact_single_match(self):
        article = subject.article_snapshot()
        self.assertEqual(article, subject.article_from_batches([(['1', '3089989'], ['other', article])]))
        for batches in ([], [(['3089989', '3089989'], [article, article])], [(['3089989'], ['changed'])]):
            with self.subTest(batches=len(batches)):
                with self.assertRaisesRegex(ValueError, 'SUSPENDED_SOURCE_ARTICLE'):
                    subject.article_from_batches(batches)

    def test_changed_segment_helper_invalidates_registry_binding(self):
        target = subject.ROOT / 'tools/typing_experiments/independent_corpus_guard.py'
        original = Path.read_bytes
        def changed(path):
            raw = original(path)
            return raw + b'\n' if path == target else raw
        with mock.patch.object(Path, 'read_bytes', changed):
            with self.assertRaisesRegex(ValueError, 'SUSPENDED_SOURCE_REGISTRY_DRIFT'):
                subject.check()


if __name__ == '__main__':
    unittest.main()
