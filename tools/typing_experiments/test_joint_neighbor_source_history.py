"""Historical source/receipt integrity; no training scripts are executed."""
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import types
from temporary_test_build import temporary_build_directory
import unittest
from unittest import mock

from frozen_source_identity import read_frozen_source

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'docs/acceptance/2026-10-28-q2-joint-neighbor-sources-evidence.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class JointNeighborSourceHistoryTest(unittest.TestCase):
    def setUp(self):
        self.evidence = json.loads(EVIDENCE.read_text())

    def test_original_receipt_bytes_are_retained(self):
        records = self.evidence['archivedReceipts']
        self.assertEqual(5, len(records))
        for name, record in records.items():
            with self.subTest(receipt=name):
                self.assertEqual(record['sha256'], sha(ROOT / name))

    def test_joint_sources_match_original_receipt_fields(self):
        records = self.evidence['historicalSourceMatches']
        self.assertEqual(2, len(records))
        for record in records:
            with self.subTest(source=record['source']):
                receipt = json.loads((ROOT / record['receipt']).read_text())
                self.assertEqual(record['sha256'], receipt[record['field']])
                original=read_frozen_source(ROOT,record['source'],record['sha256'])
                self.assertEqual(record['sha256'],hashlib.sha256(original).hexdigest())

    def test_original_joint_trainer_survives_changed_current_source(self):
        original='tools/typing_experiments/train_joint_correction.py'
        receipt=json.loads((ROOT/'tools/typing_experiments/historical_provenance_sources/joint-neighbor-receipts/joint-original-policy.json').read_text())
        digest=receipt['trainerSha256']
        archive=ROOT/'tools/typing_experiments/frozen_sources'
        manifest=json.loads((archive/'manifest.json').read_text())
        entry=manifest['sources'][digest]
        self.assertEqual(original,entry['originalPath'])
        self.assertEqual(digest,sha(archive/entry['file']))
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            current=root/original;current.parent.mkdir(parents=True)
            current.write_text('# changed trainer\n')
            target=root/'tools/typing_experiments/frozen_sources';target.mkdir()
            (target/'manifest.json').write_text(json.dumps(manifest))
            (target/entry['file']).write_bytes((archive/entry['file']).read_bytes())
            self.assertEqual(digest,hashlib.sha256(read_frozen_source(root,original,digest)).hexdigest())
            (target/entry['file']).write_bytes(b'corrupted')
            with self.assertRaisesRegex(ValueError,'FROZEN_SOURCE_IDENTITY'):
                read_frozen_source(root,original,digest)

    def test_joint_trainer_refuses_unbound_inputs_before_creating_output(self):
        script=ROOT/'tools/typing_experiments/train_joint_correction.py'
        with temporary_build_directory(ROOT) as folder:
            out=Path(folder)/'result'
            args=[str(script),str(out/'missing'),str(out/'train'),str(out/'calibration'),str(out)]
            for optimized in (False,True):
                cmd=[sys.executable]+(['-O'] if optimized else [])+args
                run=subprocess.run(cmd,text=True,capture_output=True)
                self.assertNotEqual(0,run.returncode)
                self.assertIn('NEW_HOLDOUT_REGISTRY_COVERAGE_INCOMPLETE',run.stderr)
                self.assertFalse(out.exists())
            run=subprocess.run([sys.executable]+args+['--historical-reproduction'],text=True,capture_output=True)
            self.assertNotEqual(0,run.returncode)
            self.assertIn('FileNotFoundError',run.stderr)
            self.assertFalse(out.exists())
            corpus=Path(folder)/'corpus';corpus.mkdir();(corpus/'manifest.json').write_text('{}')
            args=[str(script),str(corpus),str(out/'train'),str(out/'calibration'),str(out),'--historical-reproduction']
            for optimized in (False,True):
                run=subprocess.run([sys.executable]+(['-O'] if optimized else [])+args,text=True,capture_output=True)
                self.assertNotEqual(0,run.returncode)
                self.assertIn('HISTORICAL_CORPUS_IDENTITY',run.stderr)
                self.assertFalse(out.exists())

    def test_historical_preparers_have_exact_frozen_sources_and_original_paths(self):
        records = self.evidence['frozenBuilderMatches']
        archive = ROOT / 'tools/typing_experiments/frozen_sources'
        manifest = json.loads((archive/'manifest.json').read_text())['sources']
        self.assertEqual(3, len(records))
        for record in records:
            with self.subTest(source=record['source']):
                self.assertEqual(record['sha256'], sha(ROOT / record['archived']))
                entry = manifest[record['sha256']]
                self.assertEqual(record['source'], entry['originalPath'])
                self.assertEqual(ROOT / record['archived'], archive / entry['file'])

    def test_reconstructed_neighbor_tool_matches_original_complete_file_digest(self):
        records = self.evidence['recoveredHistoricalSources']
        self.assertEqual(1, len(records))
        for record in records:
            receipt = json.loads((ROOT / record['receipt']).read_text())
            self.assertEqual(record['expectedSha256'], receipt[record['field']])
            self.assertEqual(record['expectedSha256'], sha(ROOT / record['archived']))
            self.assertFalse(record['executed'])

    def test_neighbor_corpus_generator_is_recovered_from_its_original_receipt(self):
        receipt = ROOT / 'tools/typing_experiments/historical_provenance_sources/joint-neighbor-receipts/neighbor-corpus-manifest.json'
        digest = json.loads(receipt.read_text())['generator']
        self.assertEqual('bf2118a0b7d54f10a56d59c73ae77900fbd957c997f8307452b33549769b0323', digest)
        original = read_frozen_source(ROOT, 'tools/typing_experiments/neighbor_recovery.py', digest)
        self.assertEqual(digest, hashlib.sha256(original).hexdigest())
        with self.assertRaisesRegex(ValueError, 'FROZEN_SOURCE_ORIGIN'):
            read_frozen_source(ROOT, 'tools/typing_experiments/other.py', digest)

    def test_original_neighbor_generator_reproduces_archived_typo_and_control_labels(self):
        data = ROOT / 'tools/typing_experiments/neighbor-history-v1'
        self.assertEqual('2aeaf745c132c869d2560c89f3831f9710d82d34f559083a352eeb99b604060e', sha(data / 'manifest.json'))
        manifest = json.loads((data / 'manifest.json').read_text())
        source = ROOT / 'tools/typing_experiments/frozen_sources/neighbor_recovery_bf2118a0b7d54f10.py'
        self.assertEqual(manifest['generator'], sha(source))
        common = types.ModuleType('prepare_external_spelling_holdout')
        common.sha256 = sha
        with mock.patch.dict(sys.modules, {'prepare_external_spelling_holdout': common}), mock.patch.object(sys, 'path', sys.path.copy()):
            original = runpy.run_path(str(source), run_name='historical_neighbor_label_probe')
        original['morphology'].__globals__['MORPH'] = ROOT / 'app/src/main/assets/smarttyping/lexicon/ru.morph'
        dictionary = original['morphology']()
        for part in ('train', 'calibration', 'holdout'):
            counts = {}
            path = data / f'{part}.jsonl'
            self.assertEqual(manifest['files'][path.name], sha(path))
            for line in path.read_text(encoding='utf-8').splitlines():
                row = json.loads(line)
                group = row['group']
                counts[group] = counts.get(group, 0) + 1
                self.assertEqual(part, row['split'])
                if group in original['GROUPS']:
                    self.assertEqual(row['typed'], original['typo'](row['word'], group, part, dictionary))
                    self.assertEqual(row['word'], row['expected'])
                    self.assertIs(row['noAuto'], False)
                else:
                    self.assertIn(group, ('correct', 'protected'))
                    expected = row['word'] + ('42' if group == 'protected' else '')
                    self.assertEqual((expected, expected), (row['typed'], row['expected']))
                    self.assertIs(row['noAuto'], True)
            self.assertEqual(manifest['files'][path.name], sha(path))
            self.assertEqual(manifest['counts'][part], counts)

    def test_neighbor_source_selector_observed_excerpt_and_selection_hashes(self):
        archive = ROOT / 'tools/typing_experiments/frozen_sources'
        selector = archive / 'qualification_v2_ed9928d64d80911c.py'
        helper = archive / 'prepare_external_spelling_holdout_956436a1fbd70870.py'
        self.assertEqual('ed9928d64d80911c0182e03446d710a60abb990cb5fb1cff30730443db773225', sha(selector))
        self.assertEqual('956436a1fbd708706bddb3bad44c1fdf7bff838ef95a8c06911008148590fe01', sha(helper))
        for path, start, end, expected in (
            (selector, 110, 153, 'c8ae12dd57284c9b459ec4568c48684fbb7be04331e873d0bec555d4f77d2885'),
            (helper, 1, 50, '5ba81233630296ab08f359c1e467abdd06d91b5d65b25abe8699add2aa4e6885'),
        ):
            excerpt = b''.join(path.read_bytes().splitlines(keepends=True)[start - 1:end])
            self.assertEqual(expected, hashlib.sha256(excerpt).hexdigest())
        selector_module = runpy.run_path(str(selector), run_name='historical_selector_probe')
        data = ROOT / 'tools/typing_experiments/neighbor-history-v1'
        self.assertEqual('2aeaf745c132c869d2560c89f3831f9710d82d34f559083a352eeb99b604060e', sha(data / 'manifest.json'))
        manifest = json.loads((data / 'manifest.json').read_text())
        for part in ('train', 'calibration', 'holdout'):
            path = data / f'{part}.jsonl'
            self.assertEqual(manifest['files'][path.name], sha(path))
            for line in path.read_text(encoding='utf-8').splitlines():
                row = json.loads(line)
                family = selector_module['family'](row['word'])
                identity = f"26092026:qualification:ru:{family}:{row['prefix']}"
                self.assertEqual(row['selectionHash'], hashlib.sha256(identity.encode()).hexdigest())
            self.assertEqual(manifest['files'][path.name], sha(path))


if __name__ == '__main__':
    unittest.main()
