import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest import mock

import independent_corpus_guard as guard
import prepare_epoch_test as epoch
import prepare_refinement as refinement
import prepare_word_ranking as ranking


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class SelectorCollectorFormatTest(unittest.TestCase):
    def test_all_three_collectors_refuse_joined_text_before_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            source = root / 'source.parquet'; source.write_bytes(b'fixture')
            frequency = root / 'frequency.txt'; frequency.write_text('слово 1\n')
            lock = root / 'tools/model/rune-text-0.2/source-lock.json'
            lock.parent.mkdir(parents=True)
            lock.write_text(json.dumps({'wikipediaContext': {'files': {'ru-0007.parquet':
                {'bytes': source.stat().st_size, 'sha256': sha(source.read_bytes())}}},
                'frequencyWords': {'files': {'ru_50k.txt': sha(frequency.read_bytes())}}}))
            prior = root / 'build/typing-refinement/data'; prior.mkdir(parents=True)
            prior_files = {}
            for part in ('train', 'dev', 'test'):
                for kind in ('rows', 'text'):
                    name = f'{part}-{kind}.jsonl'; (prior / name).write_bytes(b''); prior_files[name] = sha(b'')
            manifest = prior / 'manifest.json'
            manifest.write_text(json.dumps({'containsPersonalMessages': False, 'scannedArticles': 1920,
                'partitions': {p: {'articles': []} for p in ('train', 'dev', 'test')}, 'files': prior_files}))
            observation = root / 'build/typing-refinement/verified-observations/manifest.json'
            observation.parent.mkdir(parents=True)
            observation.write_text(json.dumps({'dataManifestSha256': sha(manifest.read_bytes())}))
            bad_text = ''

            class Batch:
                def column(self, index):
                    return SimpleNamespace(to_pylist=lambda: ['123'] * 1921 if index == 0 else [bad_text] * 1921)
            parquet = ModuleType('pyarrow.parquet')
            parquet.ParquetFile = lambda path: SimpleNamespace(iter_batches=lambda **kwargs: [Batch()])
            arrow = ModuleType('pyarrow'); arrow.parquet = parquet
            with mock.patch.dict(sys.modules, {'pyarrow': arrow, 'pyarrow.parquet': parquet}), \
                 mock.patch.object(refinement, 'ROOT', root), mock.patch.object(ranking, 'ROOT', root), \
                 mock.patch.object(epoch, 'ROOT', root), mock.patch.object(ranking, 'SKIP', 0), \
                 mock.patch.object(guard, 'begin', return_value={}), \
                 mock.patch.object(guard, 'selector_inputs', return_value=None), \
                 mock.patch.object(guard, 'selector_admission', return_value=None), \
                 mock.patch.object(guard, 'prior_input_snapshot', return_value={}), \
                 mock.patch.object(ranking, 'prior_evidence', return_value=(set(), set(), set(), {})):
                for fragment, error in (('слово\u200dчасть', 'SELECTOR_TEXT_FORMAT_FRAGMENT'),
                                        ('сло\u0301во', 'SELECTOR_TEXT_PARTIAL_SOURCE_TOKEN'),
                                        ('северо-запад', 'SELECTOR_TEXT_PARTIAL_SOURCE_TOKEN'),
                                        ('северо‒запад', 'SELECTOR_TEXT_PARTIAL_SOURCE_TOKEN'),
                                        ('северо—запад', 'SELECTOR_TEXT_PARTIAL_SOURCE_TOKEN'),
                                        ('слово123', 'SELECTOR_TEXT_PARTIAL_SOURCE_TOKEN')):
                    bad_text = fragment + ' текст' * 20
                    for name, func in (('refinement', refinement.run), ('ranking', ranking.run),
                                       ('epoch', epoch.prepare)):
                        output = root / 'build' / ('out-' + name)
                        with self.subTest(collector=name, fragment=fragment), self.assertRaisesRegex(ValueError, error):
                            func(source, frequency, output)
                        self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
