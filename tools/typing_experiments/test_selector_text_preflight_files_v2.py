import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import pyarrow as pa
import pyarrow.parquet as parquet

import selector_text_preflight_files_v2 as subject
from test_holdout_ledger import ledger
from test_public_corpus_preparation_v1 import controls
from test_selector_text_preflight_files_v1 import Dictionary
from test_selector_text_preflight_v1 import sample


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class BoundParquetPreflightTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.source = root / 'source.parquet'
        self.lock = root / 'lock.json'
        self.lexical = root / 'lexical.json'
        self.controls = root / 'controls.json'
        self.data = root / 'data'
        self.data.mkdir()
        self.lexical.write_text(json.dumps(ledger(False)))
        self.controls.write_text(json.dumps(controls()))
        texts, rows, sources = sample()
        self.articles = list(sources)
        self.texts = list(sources.values())
        self.files = {}
        for part in subject.previous.PARTS:
            for kind, values in (('text', texts[part]), ('rows', rows[part])):
                name = f'{part}-{kind}.jsonl'
                raw = ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in values).encode()
                (self.data / name).write_bytes(raw)
                self.files[name] = sha(raw)
        self.write_source()

    def write_source(self):
        parquet.write_table(pa.table({'id': self.articles, 'text': self.texts}), self.source)
        raw = self.source.read_bytes()
        self.lock.write_text(json.dumps({'wikipediaContext': {'files': {'ru-0007.parquet':
            {'bytes': len(raw), 'sha256': sha(raw)}}}}))
        (self.data / 'manifest.json').write_text(json.dumps(dict(containsPersonalMessages=False,
            sourceSha256=sha(raw), files=self.files)))

    def assess(self):
        return subject.assess_files(self.data, self.source, self.lock, self.lexical, self.controls, Dictionary())

    def test_actual_parquet_is_read_and_publication_stays_blocked(self):
        report = self.assess()
        self.assertEqual('BLOCKED_COVERAGE', report['status'])
        self.assertFalse(report['publicationPermitted'])
        self.assertFalse(report['sourceDecoderAttested'])
        self.assertEqual(subject.PYARROW_VERSION, report['bindings']['decoder']['version'])
        self.assertEqual(sha(self.source.read_bytes()), report['bindings']['sourceSha256'])
        self.assertEqual(set(subject.decoder_identity()['files']), set(report['bindings']['decoder']['files']))

    def test_decoded_source_cannot_be_replaced_with_a_forged_mapping(self):
        self.texts[0] = 'чужой исходный текст'
        self.write_source()
        with self.assertRaisesRegex(ValueError, 'TEXT_AUDIT_SOURCE_MISMATCH'):
            self.assess()

    def test_duplicate_referenced_article_is_rejected(self):
        self.articles.append(self.articles[0]); self.texts.append(self.texts[0])
        self.write_source()
        with self.assertRaisesRegex(ValueError, 'TEXT_PREFLIGHT_DUPLICATE_SOURCE'):
            self.assess()

    def test_bad_rows_are_not_coerced(self):
        self.articles[0] = None
        self.write_source()
        with self.assertRaisesRegex(ValueError, 'TEXT_PREFLIGHT_DECODER_ROW'):
            self.assess()

    def test_source_bytes_must_match_lock(self):
        self.source.write_bytes(self.source.read_bytes() + b'x')
        with self.assertRaisesRegex(ValueError, 'TEXT_PREFLIGHT_SOURCE_IDENTITY'):
            self.assess()

    def test_decoder_drift_is_rejected(self):
        original = subject.decoder_identity()
        with mock.patch.object(subject, 'decoder_identity', side_effect=[original, {'version': 'changed'}]):
            with self.assertRaisesRegex(ValueError, 'TEXT_PREFLIGHT_DECODER_DRIFT'):
                self.assess()

    def test_wrong_decoder_version_is_rejected(self):
        with mock.patch.object(subject.metadata, 'version', return_value='0'):
            with self.assertRaisesRegex(ValueError, 'TEXT_PREFLIGHT_DECODER_VERSION'):
                self.assess()

    def test_recorded_package_files_are_bound_and_missing_files_refused(self):
        root = Path(self.tmp.name) / 'package'
        root.mkdir()
        (root / 'first.so').write_bytes(b'native')
        (root / 'reader.py').write_bytes(b'python')
        distribution = mock.Mock(files=[Path('first.so'), Path('reader.py')])
        distribution.locate_file.side_effect = lambda entry: root / entry
        before = subject.package_identity(distribution)
        self.assertEqual(2, before['recordedFileCount'])
        (root / 'first.so').write_bytes(b'changed')
        self.assertNotEqual(before['recordedFilesSha256'],
                            subject.package_identity(distribution)['recordedFilesSha256'])
        (root / 'reader.py').unlink()
        with self.assertRaisesRegex(ValueError, 'TEXT_PREFLIGHT_DECODER_FILE_MISSING'):
            subject.package_identity(distribution)

    def test_untrusted_package_file_list_is_rejected(self):
        for files, error in (([], 'TEXT_PREFLIGHT_DECODER_FILES'),
                             ([Path('../outside')], 'TEXT_PREFLIGHT_DECODER_PATH'),
                             ([Path('/absolute')], 'TEXT_PREFLIGHT_DECODER_PATH'),
                             ([Path('file'), Path('file')], 'TEXT_PREFLIGHT_DECODER_FILES')):
            with self.subTest(files=files):
                distribution = mock.Mock(files=files)
                distribution.locate_file.return_value = self.source
                with self.assertRaisesRegex(ValueError, error):
                    subject.package_identity(distribution)

    def test_recorded_package_change_during_scan_is_rejected(self):
        installed = Path(self.tmp.name) / 'decoder.so'
        installed.write_bytes(b'first')
        distribution = mock.Mock(files=[Path('decoder.so')])
        distribution.locate_file.return_value = installed
        package_identity = subject.package_identity
        def run_preflight(*args):
            installed.write_bytes(b'second')
            return {'bindings': {}}
        with mock.patch.object(subject, 'package_identity', side_effect=lambda _: package_identity(distribution)):
            with mock.patch.object(subject.previous, 'assess_files', side_effect=run_preflight):
                with self.assertRaisesRegex(ValueError, 'TEXT_PREFLIGHT_DECODER_DRIFT'):
                    self.assess()
if __name__ == '__main__':
    unittest.main()
