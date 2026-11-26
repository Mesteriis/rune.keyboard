import unittest
from audit_candidate_modes import compare
from test_audit_candidate_strip_utility import fixture


class CandidateModesTest(unittest.TestCase):
    def test_gain_view_boundary_and_undo_are_separate(self):
        row,on,identity=fixture();on|=dict(afterBoundary={'text':'one'},afterBackspace={'text':'restored'},restoredBeforeBoundaryExactly=True)
        off=on|dict(candidateView={'candidates':[{'role':'CORRECTION','text':'готовы'}]},afterBoundary={'text':'two'})
        result=compare([row],[on],[off],[identity])['languages']['ru']
        self.assertEqual(1,result['targetLostOn']);self.assertEqual(1,result['visibleViewChanges']);self.assertEqual(1,result['boundaryChanges'])
        self.assertEqual(1,result['visibleTextChanges'])
        self.assertNotIn('undoChanges',result)

    def test_identity_failure_is_not_skipped(self):
        row,on,identity=fixture();on|=dict(afterBoundary={},afterBackspace={},restoredBeforeBoundaryExactly=True)
        with self.assertRaises(ValueError):compare([row],[on],[on],[identity|{'sourceId':'wrong'}])
        with self.assertRaises(ValueError):compare([row],[on],[],[identity])


if __name__=='__main__':unittest.main()
