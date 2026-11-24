import contextlib
import io
from pathlib import Path
import sys
from temporary_test_build import temporary_build_directory
import unittest

ROOT=Path(__file__).resolve().parents[2]
old_path=sys.path[:]
try:
    sys.path.insert(0,str(ROOT/'tools/ci'))
    import retrieval_evaluation_smoke as smoke
finally:sys.path[:]=old_path


class RetrievalDriverTest(unittest.TestCase):
    def test_real_bound_manual_pool_comparison_cannot_qualify_and_refuses_mid_run_drift(self):
        with temporary_build_directory(ROOT) as folder,contextlib.redirect_stdout(io.StringIO()):
            result=smoke.run(Path(folder)/'output')
        self.assertEqual((3,1),(result['typoRows'],result['controls']))
        self.assertFalse(result['independentQualification']);self.assertFalse(result['productionQualified'])
        self.assertTrue(result['packagedFilesUnchanged']);self.assertTrue(result['midEvaluationDriftRejected'])
        self.assertTrue(result['secondWriteRejected'])
        self.assertEqual(result['capturedFiles']-2,result['isolatedInputMutationRejections'])


if __name__=='__main__':unittest.main()
