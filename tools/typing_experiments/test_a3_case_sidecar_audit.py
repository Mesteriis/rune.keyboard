import unittest

from a3_case_sidecar_audit import summarize


class CaseSidecarAuditTest(unittest.TestCase):
    def test_counts_short_keys_and_three_way_intersection(self):
        result = summarize({'ива', 'ира', 'ми', 'москва'}, {'ива', 'ира'}, {'ира'})
        self.assertEqual({'shortCaseKeys': 2, 'inRare': 2, 'inLowerEvidence': 1,
                          'inRareWithoutLowerEvidence': 1}, result)
