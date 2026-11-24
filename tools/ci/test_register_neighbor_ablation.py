from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

import register_neighbor_ablation as subject


class NeighborAblationTest(unittest.TestCase):
    def test_entries_cover_every_observed_output(self):
        rows, _ = subject.inputs()
        control, lexical = subject.entries()
        self.assertEqual(6000, len(rows))
        self.assertEqual(6000, control['rowCount'])
        self.assertEqual(6000, lexical['rowCount'])
        self.assertTrue(control['keys'])
        self.assertTrue(control['surfaceKeys'])
        self.assertTrue(lexical['keys']['context'])

    def test_mutated_fixture_is_refused(self):
        build = subject.ROOT / 'build'
        build.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=build) as folder:
            data = Path(folder)
            for name in subject.PINS:
                shutil.copyfile(subject.DATA / name, data / name)
            fixture = data / subject.FIXTURE.name
            with fixture.open('ab') as stream:
                stream.write(b' ')
            with mock.patch.object(subject, 'DATA', data), mock.patch.object(subject, 'FIXTURE', fixture):
                with self.assertRaisesRegex(ValueError, 'NEIGHBOR_ABLATION_IDENTITY'):
                    subject.inputs()

    def test_new_contexts_are_blocked_in_both_registries(self):
        rows, _ = subject.inputs()
        controls = subject.control.load(subject.CONTROL)
        ledger = subject.lexical.load_ledger(subject.LEXICAL)
        old_controls = {key for entry in controls['entries'] if entry['id'] != subject.ENTRY and entry['kind'] == 'regression' for key in entry['keys']}
        old_contexts = {key for entry in ledger['entries'] if entry['id'] != subject.ENTRY + '-contexts' for key in entry['keys'].get('context', [])}
        candidates = [row for row in rows if subject.control.key_for(row, 'regression') not in old_controls
                      and not subject.lexical.keys_for([row], 'context') <= old_contexts]
        self.assertTrue(candidates)
        with self.assertRaisesRegex(ValueError, 'CONTROL_OVERLAP'):
            subject.control.assert_disjoint([candidates[0]], controls, 'regression')
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:context'):
            subject.lexical.assert_disjoint([candidates[0]], ledger, kinds=('context',), require_complete=False)


if __name__ == '__main__':
    unittest.main()
