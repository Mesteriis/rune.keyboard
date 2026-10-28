"""Cross-version source and replay routing checks; no source corpus is scored."""
import importlib
import io
import json
from pathlib import Path
from unittest.mock import patch
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE_RECEIPT = ROOT / ('tools/typing_experiments/historical_provenance_sources/'
                        'joint-neighbor-receipts/neighbor-corpus-manifest.json')


def rows(version):
    return [dict(id=f'{cohort}-{i}', family=f'{cohort}-{i}', cohort=cohort,
                 language='ru', split='holdout', task='spelling',
                 corpusVersion=version,
                 **({'expectedSpelling': 'слово'} if cohort == 'typo' else {}))
            for cohort, count in [('typo', 1000), ('correct', 700)]
            for i in range(count)]


class HistoricalHoldoutVariantsTest(unittest.TestCase):
    def test_all_six_preparers_match_original_pinned_shards(self):
        sources = json.loads(SOURCE_RECEIPT.read_text())['sources']
        for version in range(7, 13):
            with self.subTest(version=version):
                module = importlib.import_module(f'prepare_external_spelling_holdout_v{version}')
                if version < 9:
                    path, digest, size = module.SOURCE_PATH, module.SOURCE_SHA256, module.SOURCE_BYTES
                else:
                    path, digest, size = module.SPEC.source_path, module.SPEC.source_sha256, module.SPEC.source_bytes
                    self.assertEqual(version, module.SPEC.version)
                self.assertEqual(f'20231101.ru/train/{version + 5:04d}.parquet', path)
                source = sources[f'build/typing-ranker-v2/ru-{version + 5:04d}.parquet']
                self.assertEqual(source['path'], path)
                self.assertEqual(source['sha256'], digest)
                self.assertEqual(source['bytes'], size)

    def test_each_replay_rejects_a_different_corpus_version(self):
        from fresh_spelling_replay import validate_rows
        for version in range(7, 13):
            with self.subTest(version=version):
                module = importlib.import_module(f'export_external_spelling_replay_v{version}')
                check = module.validate_rows if version < 9 else lambda values: validate_rows(values, module.VERSION)
                check(rows(version))
                with self.assertRaisesRegex(ValueError, 'HOLDOUT_SCOPE'):
                    check(rows(version - 1))

    def test_shared_export_wrappers_forward_exact_version_and_explicit_java(self):
        for version in range(9, 13):
            with self.subTest(version=version):
                module = importlib.import_module(f'export_external_spelling_replay_v{version}')
                args = ['export', '--rows', 'rows', '--manifest', 'manifest', '--parquet', 'parquet',
                        '--policy', 'policy', '--output', 'output', '--java', 'explicit-java']
                response = dict(rows=0, observations=0, modelCalls=0, policySha256='fixture')
                with patch.object(module, 'export', return_value=response) as export, \
                        patch('sys.argv', args), patch('sys.stdout', new_callable=io.StringIO):
                    module.main()
                self.assertEqual(version, export.call_args.args[0])
                self.assertEqual(Path(module.__file__), export.call_args.args[1])
                self.assertEqual(Path('explicit-java'), export.call_args.args[-1])


if __name__ == '__main__':
    unittest.main()
