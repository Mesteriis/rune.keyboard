import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import import_unimorph_early_exclusions as subject
from public_corpus_preparation_v1 import preflight
from source_identities import unsupported_surface_key
from test_public_corpus_preparation_v1 import candidate, controls


class UniMorphEarlyExclusionTest(unittest.TestCase):
    def test_prefix_fragments_and_compounds_are_not_treated_as_whole_words(self):
        prefix = 'край целое северо-запад д’артаньян abcимя имя123 конец'
        self.assertEqual({unsupported_surface_key('целое')}, subject.interior_prefix_keys(prefix))
        with self.assertRaisesRegex(ValueError, 'UNIMORPH_NEIGHBOR_PREFIX'):
            subject.interior_prefix_keys(None)

    def test_capture_collects_all_forms_only_for_matched_lemmas(self):
        source = 'кот\tкота\tN;SG\nкот\tкоту\tN;SG\nпёс\tпса\tN;SG\n'.encode()
        parents = {'historic': {unsupported_surface_key('кота')}}
        with mock.patch.object(subject, 'SOURCE_SHA', subject.sha(source)):
            value = subject.capture(source, parents)
            self.assertEqual([['кот', 'кота'], ['кот', 'коту']], value['pairs'])
            self.assertEqual({'historic': [unsupported_surface_key('кота')]}, value['matchesByParent'])
            with self.assertRaisesRegex(ValueError, 'UNIMORPH_SOURCE_IDENTITY'):
                subject.capture(source + b'x', parents)

    def test_real_entry_blocks_new_surface_and_preserves_prior_entries(self):
        current = json.loads(subject.LEDGER.read_bytes())
        subject.ledger.validate_ledger(copy.deepcopy(current))
        registered = next(item for item in current['entries'] if item['id'] == subject.ENTRY)
        self.assertEqual(registered, subject.entry(current, json.loads(subject.FIXTURE.read_bytes())))
        previous = copy.deepcopy(current)
        previous['entries'] = [item for item in previous['entries'] if item['id'] != subject.ENTRY]
        old = {key for item in previous['entries'] for key in item.get('unsupportedSurfaceKeys', [])}
        fixture = json.loads(subject.FIXTURE.read_bytes())
        form = next(form for _, form in fixture['pairs'] if unsupported_surface_key(form) not in old)
        row = candidate(typed=form, expectedSpelling=form)
        self.assertEqual(0, preflight([row], 'spelling', previous, controls(), 'new-families')['unsupportedTargetOverlaps'])
        self.assertEqual(1, preflight([row], 'spelling', current, controls(), 'new-families')['unsupportedTargetOverlaps'])
        self.assertFalse(current['coverage']['complete'])

    def test_fixture_and_parent_drift_are_refused(self):
        base = json.loads(subject.LEDGER.read_bytes())
        fixture = json.loads(subject.FIXTURE.read_bytes())
        broken_fixture = copy.deepcopy(fixture)
        broken_fixture['pairs'].pop()
        with self.assertRaisesRegex(ValueError, 'UNIMORPH_FIXTURE'):
            subject.entry(base, broken_fixture)
        with self.assertRaisesRegex(ValueError, 'UNIMORPH_PARENT_IDENTITY'):
            subject.targets(base, subject.ROWS.read_bytes() + b' ')
        broken_parent = copy.deepcopy(base)
        parent = next(item for item in broken_parent['entries'] if item['id'] == subject.PARENT)
        parent['unsupportedSurfaceKeys'].remove(fixture['matchesByParent'][subject.PARENT][0])
        with self.assertRaisesRegex(ValueError, 'UNIMORPH_TARGET_SCOPE'):
            subject.entry(broken_parent, fixture)
        with mock.patch.object(subject, 'sha', return_value='0' * 64):
            with self.assertRaisesRegex(ValueError, 'UNIMORPH_NEIGHBOR_IDENTITY'):
                subject.parent_keys(base)
        with tempfile.TemporaryDirectory() as folder:
            changed = Path(folder) / 'projection.json'
            changed.write_bytes(subject.TEXT_FIXTURE.read_bytes() + b' ')
            with mock.patch.object(subject, 'TEXT_FIXTURE', changed):
                with self.assertRaisesRegex(ValueError, 'UNIMORPH_TEXT_FIXTURE'):
                    subject.parent_keys(base)

    def test_check_runs_from_temporary_source_tree_without_build(self):
        names = ('tools/typing_experiments/import_unimorph_early_exclusions.py',
                 'tools/typing_experiments/unimorph-early-exclusions-v1.json',
                 'tools/typing_experiments/holdout-ledger.json',
                 'tools/typing_experiments/holdout_ledger.py',
                 'tools/typing_experiments/source_identities.py',
                 'tools/typing_experiments/conversation_split_checks.py',
                 'tools/typing_experiments/neighbor-history-v1/train.jsonl',
                 'tools/typing_experiments/neighbor-history-v1/calibration.jsonl',
                 'tools/typing_experiments/neighbor-history-v1/holdout.jsonl',
                 'tools/typing_experiments/unimorph-historical-text-boundaries-v1.json',
                 'tools/typing_experiments/audit_unimorph_text_boundaries.py',
                 'tools/typing_experiments/selector_text_preflight_v1.py',
                 'tools/ci/historical-data-v1/files.tar.gz',
                 'tools/ci/historical-model-fixtures-v1/files.tar.gz',
                 'tools/eval/smart-typing-0.3/qualification-v2/corpus/spelling-ru.jsonl')
        with tempfile.TemporaryDirectory(prefix='rune-unimorph-portable-') as folder:
            root = Path(folder)
            for name in names:
                dest = root / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(subject.ROOT / name, dest)
            result = subprocess.run([sys.executable, '-B', str(root / names[0]), '--check'],
                                    cwd=root, capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertFalse((root / 'build').exists())
            self.assertEqual(644, json.loads(result.stdout)['surfaces'])


if __name__ == '__main__':
    unittest.main()
