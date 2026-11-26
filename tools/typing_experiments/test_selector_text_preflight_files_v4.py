import json
import unittest
from unittest import mock

import selector_text_preflight_files_v4 as subject
from test_selector_text_preflight_files_v1 import Dictionary
import test_selector_text_preflight_files_v2 as fixture


class BoundDashPreflightTest(unittest.TestCase):
    setUp = fixture.BoundParquetPreflightTest.setUp
    write_source = fixture.BoundParquetPreflightTest.write_source

    def assess(self):
        return subject.assess_files(self.data, self.source, self.lock,
                                    self.lexical, self.controls, Dictionary())

    def test_dash_is_detected_in_bound_source(self):
        self.texts[0] = 'слово—часть'
        path = self.data / 'train-text.jsonl'
        payload = (json.dumps({'articleId': self.articles[0], 'text': 'слово часть'},
                              ensure_ascii=False) + '\n').encode()
        path.write_bytes(payload)
        self.files[path.name] = fixture.sha(payload)
        self.write_source()
        result = self.assess()
        self.assertEqual(2, result['textIdentityBlockers']['sourceDashFragments'])
        self.assertEqual('BLOCKED_TEXT_IDENTITIES', result['status'])
        self.assertFalse(result['publicationPermitted'])
        self.assertFalse(result['sourceDecoderAttested'])
        self.assertIn('previousFormatDiagnostic', result['bindings']['formatHelpers'])

    def test_new_helper_drift_is_rejected(self):
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

    def test_prior_format_helper_drift_is_rejected(self):
        original = subject.files.file_sha
        calls = 0
        def changed(path):
            nonlocal calls
            if str(path) == str(subject.text.previous.__file__):
                calls += 1
                if calls > 1:
                    return '0' * 64
            return original(path)
        with mock.patch.object(subject.files, 'file_sha', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'TEXT_PREFLIGHT_INPUT_DRIFT'):
                self.assess()

    def test_data_drift_after_first_assessment_is_rejected(self):
        original = subject.text.assess
        def changed(*args):
            result = original(*args)
            path = self.data / 'train-text.jsonl'
            path.write_bytes(path.read_bytes() + b' ')
            return result
        with mock.patch.object(subject.text, 'assess', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'TEXT_PREFLIGHT_INPUT_DRIFT'):
                self.assess()

    def test_decoder_drift_is_rejected(self):
        with mock.patch.object(subject.parquet, 'decoder_identity',
                               side_effect=[{'version': 'before'}, {'version': 'after'}]):
            with self.assertRaisesRegex(ValueError, 'TEXT_PREFLIGHT_INPUT_DRIFT'):
                self.assess()

    def test_duplicate_source_is_rejected(self):
        self.articles.append(self.articles[0])
        self.texts.append(self.texts[0])
        self.write_source()
        with self.assertRaisesRegex(ValueError, 'TEXT_PREFLIGHT_DUPLICATE_SOURCE'):
            self.assess()
