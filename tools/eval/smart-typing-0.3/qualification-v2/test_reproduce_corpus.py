import hashlib
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import reproduce_corpus as reproduction


class ReproductionTest(unittest.TestCase):
    def test_exact_historical_sources_and_all_reference_files_are_available(self):
        manifest = reproduction.reference()
        self.assertEqual(13200, manifest['validation']['samples'])
        self.assertEqual(reproduction.SOURCES, manifest['sources'])
        sources = reproduction.archived_sources()
        self.assertEqual(set(reproduction.SOURCES), set(sources))
        self.assertEqual(8, len(reproduction.verify_product(reproduction.HERE / 'corpus', manifest)))

    def test_modified_archived_evaluator_fails_before_import_or_execution(self):
        with TemporaryDirectory() as folder:
            directory = Path(folder) / 'archive'
            shutil.copytree(reproduction.ARCHIVE, directory, ignore=shutil.ignore_patterns('__pycache__'))
            path = directory / 'qualification_evaluator_ad76b78ba9f00f30.py'
            path.write_bytes(path.read_bytes() + b'\n')
            with patch.object(reproduction, 'ARCHIVE', directory):
                with self.assertRaisesRegex(ValueError, 'V2_REPRODUCTION_IDENTITY'):
                    reproduction.archived_sources()

    def test_changed_missing_and_additional_outputs_cannot_match_reference(self):
        manifest = reproduction.reference()
        with TemporaryDirectory() as folder:
            output = Path(folder) / 'output'
            shutil.copytree(reproduction.HERE / 'corpus', output)
            path = output / 'spelling-ru.jsonl'
            raw = path.read_bytes()
            path.write_bytes(raw + b'\n')
            with self.assertRaisesRegex(ValueError, 'V2_REPRODUCTION_IDENTITY'):
                reproduction.verify_product(output, manifest)
            path.unlink()
            with self.assertRaisesRegex(ValueError, 'V2_REPRODUCTION_OUTPUT_SET'):
                reproduction.verify_product(output, manifest)
            path.write_bytes(raw)
            extra = output / 'unexpected.json'
            extra.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'V2_REPRODUCTION_OUTPUT_SET'):
                reproduction.verify_product(output, manifest)
            extra.unlink()
            self.assertEqual(8, len(reproduction.verify_product(output, manifest)))

    def test_manifest_cannot_be_rehashed_to_accept_changed_reference(self):
        with TemporaryDirectory() as folder:
            directory = Path(folder)
            shutil.copytree(reproduction.HERE / 'corpus', directory / 'corpus')
            path = directory / 'corpus/manifest.json'
            path.write_bytes(path.read_bytes() + b'\n')
            with patch.object(reproduction, 'HERE', directory):
                with self.assertRaisesRegex(ValueError, 'V2_REPRODUCTION_IDENTITY'):
                    reproduction.reference()

    def test_catalog_cannot_redirect_an_exact_source_outside_archive(self):
        with TemporaryDirectory() as folder:
            directory = Path(folder) / 'archive'
            shutil.copytree(reproduction.ARCHIVE, directory, ignore=shutil.ignore_patterns('__pycache__'))
            path = directory / 'manifest.json'
            catalog = json.loads(path.read_text())
            digest = next(iter(reproduction.SOURCES.values()))
            source = directory / catalog['sources'][digest]['file']
            shutil.copyfile(source, directory.parent / 'outside.py')
            catalog['sources'][digest]['file'] = '../outside.py'
            path.write_text(json.dumps(catalog))
            with patch.object(reproduction, 'ARCHIVE', directory):
                with self.assertRaisesRegex(ValueError, 'V2_REPRODUCTION_SOURCE_PATH'):
                    reproduction.archived_sources()

    def test_wrong_parquet_fails_before_subprocess_and_output_creation(self):
        manifest = reproduction.reference()
        with TemporaryDirectory() as folder:
            directory = Path(folder)
            name = next(iter(manifest['source']['files']))
            (directory / name).write_bytes(b'not the frozen Wikipedia input')
            output = directory / 'output'
            args = SimpleNamespace(old_corpus=reproduction.HERE.parent, inputs=directory,
                                   frequency_inputs=directory, training_data=directory, output=output)
            with patch.object(reproduction.subprocess, 'run') as run:
                with self.assertRaisesRegex(ValueError, 'V2_REPRODUCTION_IDENTITY'):
                    reproduction.run(args)
                run.assert_not_called()
            self.assertFalse(output.exists())

    def test_symlink_is_not_an_exact_file_binding(self):
        with TemporaryDirectory() as folder:
            directory = Path(folder)
            original = directory / 'original'
            original.write_bytes(b'exact bytes')
            link = directory / 'link'
            link.symlink_to(original)
            with self.assertRaisesRegex(ValueError, 'V2_REPRODUCTION_IDENTITY'):
                reproduction.checked(link, hashlib.sha256(original.read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()
