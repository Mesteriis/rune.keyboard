import copy
import unittest
from pathlib import Path
import tempfile
import compare_neighbor_reproduction as subject


class NeighborReproductionComparisonTest(unittest.TestCase):
    def setUp(self):
        self.payloads = {name: name.encode() for name in subject.FILES}
        self.old = {'generator': 'old', 'counts': {'train': 5},
                    'files': {name: subject.sha(raw) for name, raw in self.payloads.items()}}
        self.new = copy.deepcopy(self.old)
        self.new['generator'] = 'new'

    def test_exact_rows_allow_different_generator_without_claiming_its_recovery(self):
        result = subject.compare(self.old, self.new, self.payloads, 'new')
        self.assertTrue(result['allFilesMatch'])
        self.assertTrue(result['metadataMatches'])
        self.assertFalse(result['historicalGeneratorRecovered'])
        self.assertFalse(result['qualified'])

    def test_edited_rows_and_metadata_do_not_pass(self):
        payloads = self.payloads | {'train.jsonl': b'altered'}
        with self.assertRaisesRegex(ValueError, 'NEIGHBOR_GENERATED_FILE_DRIFT'):
            subject.compare(self.old, self.new, payloads, 'new')
        updated = copy.deepcopy(self.new)
        updated['files']['train.jsonl'] = subject.sha(b'altered')
        updated['counts']['train'] = 6
        result = subject.compare(self.old, updated, payloads, 'new')
        self.assertFalse(result['allFilesMatch'])
        self.assertFalse(result['metadataMatches'])

    def test_historical_source_bytes_are_checked(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            sources = {}
            for number in range(11, 18):
                name = f'build/typing-ranker-v2/ru-{number:04d}.parquet'
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'public fixture')
                sources[name] = {'sha256': subject.sha(b'public fixture'), 'bytes': len(b'public fixture')}
            historical = {'sources': sources}
            for name, field in (
                ('app/src/main/assets/smarttyping/lexicon/ru.morph', 'morphology'),
                ('build/smart-typing-0.3/corpus-inputs/ru_50k.txt', 'frequency'),
                ('app/src/main/assets/smarttyping/experiments/ru-ranking-context.bin', 'context'),
            ):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'asset')
                historical[field] = subject.sha(b'asset')
            self.assertEqual(10, len(subject.verify_inputs(root, historical)))
            (root / next(iter(sources))).write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'NEIGHBOR_INPUT_IDENTITY'):
                subject.verify_inputs(root, historical)

    def test_wrong_source_or_missing_files_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'NEIGHBOR_GENERATOR_IDENTITY'):
            subject.compare(self.old, self.new, self.payloads, 'wrong')
        with self.assertRaisesRegex(ValueError, 'NEIGHBOR_FILE_SET'):
            subject.compare(self.old, self.new, {}, 'new')


if __name__ == '__main__':
    unittest.main()
