import json
import unittest
from unittest import mock

import selector_text_preflight_files_v2 as old
import selector_text_preflight_files_v3 as subject
from test_selector_text_preflight_files_v1 import Dictionary
import test_selector_text_preflight_files_v2 as fixture


class BoundFormatPreflightTest(unittest.TestCase):
    setUp = fixture.BoundParquetPreflightTest.setUp
    write_source = fixture.BoundParquetPreflightTest.write_source

    def assess(self):
        return subject.assess_files(self.data, self.source, self.lock,
                                    self.lexical, self.controls, Dictionary())

    def test_bound_parquet_blocks_combining_and_mixed_token_fragments(self):
        for source, text in (('сло\u0301во', 'сло во'), ('северо-запад', 'северо запад'),
                             ('слово123', 'слово'), ('словоLatin', 'слово')):
            with self.subTest(source=source):
                self.texts[0] = source
                path = self.data / 'train-text.jsonl'
                payload = (json.dumps({'articleId': self.articles[0], 'text': text},
                                      ensure_ascii=False) + '\n').encode()
                path.write_bytes(payload)
                self.files[path.name] = fixture.sha(payload)
                self.write_source()
                result = self.assess()
                self.assertGreater(result['textIdentityBlockers']['sourceTokenFragments'], 0)
                self.assertFalse(result['publicationPermitted'])

    def test_format_fragment_is_found_in_actual_bound_parquet(self):
        self.texts[0] = 'слово\u200dчасть'
        path = self.data / 'train-text.jsonl'
        payload = (json.dumps({'articleId': self.articles[0], 'text': 'слово часть'},
                              ensure_ascii=False) + '\n').encode()
        path.write_bytes(payload)
        self.files[path.name] = fixture.sha(payload)
        self.write_source()
        old_report = old.assess_files(self.data, self.source, self.lock,
                                      self.lexical, self.controls, Dictionary())
        report = self.assess()
        self.assertEqual(0, old_report['textIdentityBlockers']['sourceTokenFragments'])
        self.assertGreater(report['textIdentityBlockers']['sourceFormatFragments'], 0)
        self.assertEqual('BLOCKED_TEXT_IDENTITIES', report['status'])
        self.assertFalse(report['publicationPermitted'])
        self.assertFalse(report['sourceDecoderAttested'])
        self.assertEqual(fixture.sha(self.source.read_bytes()), report['bindings']['sourceSha256'])
        self.assertEqual({'formatDiagnostic', 'formatBoundary', 'fileDiagnostic'}, set(report['bindings']['formatHelpers']))

    def test_input_drift_during_second_assessment_is_rejected(self):
        original = subject.text.assess
        def drift(*args):
            result = original(*args)
            path = self.data / 'train-text.jsonl'
            path.write_bytes(path.read_bytes() + b' ')
            return result
        with mock.patch.object(subject.text, 'assess', side_effect=drift):
            with self.assertRaisesRegex(ValueError, 'TEXT_PREFLIGHT_INPUT_DRIFT'):
                self.assess()

    def test_duplicate_and_changed_source_are_rejected(self):
        self.articles.append(self.articles[0]); self.texts.append(self.texts[0])
        self.write_source()
        with self.assertRaisesRegex(ValueError, 'TEXT_PREFLIGHT_DUPLICATE_SOURCE'):
            self.assess()
        self.articles.pop(); self.texts.pop(); self.write_source()
        self.source.write_bytes(self.source.read_bytes() + b'x')
        with self.assertRaisesRegex(ValueError, 'TEXT_PREFLIGHT_SOURCE_IDENTITY'):
            self.assess()

    def test_decoder_drift_is_rejected(self):
        with mock.patch.object(subject.parquet, 'decoder_identity',
                               side_effect=[{'version': 'before'}, {'version': 'after'}]):
            with self.assertRaisesRegex(ValueError, 'TEXT_PREFLIGHT_INPUT_DRIFT'):
                self.assess()

    def test_format_helper_drift_is_rejected(self):
        original = subject.files.file_sha
        calls = 0
        def changed(path):
            nonlocal calls
            if str(path) == str(subject.text.__file__):
                calls += 1
                if calls > 1:
                    return '0' * 64
            return original(path)
        with mock.patch.object(subject.files, 'file_sha', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'TEXT_PREFLIGHT_INPUT_DRIFT'):
                self.assess()

    def test_historical_helper_drift_after_first_assessment_is_rejected(self):
        original = subject.files.file_sha
        calls = 0
        def changed(path):
            nonlocal calls
            if path.name == 'selector_text_preflight_v1.py':
                calls += 1
                if calls > 2:
                    return '0' * 64
            return original(path)
        with mock.patch.object(subject.files, 'file_sha', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'TEXT_PREFLIGHT_INPUT_DRIFT'):
                self.assess()


if __name__ == '__main__':
    unittest.main()
