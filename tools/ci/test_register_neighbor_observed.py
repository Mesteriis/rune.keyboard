from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

import register_neighbor_observed as subject


class NeighborObservedTest(unittest.TestCase):
    def test_entries_cover_every_observed_output(self):
        rows, _ = subject.inputs()
        control, lexical = subject.entries()
        self.assertEqual(3472, len(rows))
        self.assertEqual(3472, control['rowCount'])
        self.assertEqual(3472, lexical['rowCount'])
        self.assertTrue(control['keys'])
        self.assertTrue(control['surfaceKeys'])
        self.assertTrue(control['articleKeys'])
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
                with self.assertRaisesRegex(ValueError, 'NEIGHBOR_OBSERVED_IDENTITY'):
                    subject.inputs()

    def test_disclosed_output_is_rejected_by_both_registries(self):
        rows, _ = subject.inputs()
        row = next(row for row in rows if row['typed'] == 'дневной' and row['prefix'].endswith('для пользы'))
        controls = subject.control.load(subject.CONTROL)
        lexical = subject.lexical.load_ledger(subject.LEXICAL)
        with self.assertRaisesRegex(ValueError, 'CONTROL_OVERLAP'):
            subject.control.assert_disjoint([row], controls, 'regression')
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:context'):
            subject.lexical.assert_disjoint([row], lexical, kinds=('context',), require_complete=False)


if __name__ == '__main__':
    unittest.main()
