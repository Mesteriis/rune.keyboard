import unittest

import a3_case_control_inputs as probe
import control_ledger as controls
from test_control_ledger import registry


class CaseControlInputsTest(unittest.TestCase):
    def test_probe_is_sorted_unlabelled_and_excludes_surfaces(self):
        rows = probe.make_rows({'ира', 'ива', 'москва'}, {'ира', 'ива'}, {'ива'})
        self.assertEqual(2, len(rows))
        self.assertTrue(all(row['typed'] == 'ира' and row['split'] == 'calibration' for row in rows))
        self.assertTrue(all('expectedSpelling' not in row and 'noAuto' not in row for row in rows))
        result = probe.register(registry(), rows, {'fixture': 'a' * 64}, 'b' * 64)
        with self.assertRaisesRegex(ValueError, 'CONTROL_SURFACE_OVERLAP'):
            controls.assert_disjoint([rows[0] | {'prefix': 'другой контекст'}], result, 'regression')
        with self.assertRaisesRegex(ValueError, 'A3_ALREADY_REGISTERED'):
            probe.register(result, rows, {'fixture': 'a' * 64}, 'b' * 64)
