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
    import refinement_evaluation_smoke as smoke
finally:
    sys.path[:]=old_path


class RefinementEvaluationDriverTest(unittest.TestCase):
    def test_real_bounded_evaluation_receipt_and_review_export_roundtrip(self):
        with temporary_build_directory(ROOT) as directory,contextlib.redirect_stdout(io.StringIO()):
            result=smoke.run(Path(directory)/'output')
        self.assertEqual(4,result['mainRows'])
        self.assertEqual(4,result['legacyRows'])
        self.assertFalse(result['independentDataEvaluation'])
        self.assertTrue(result['metricMutationRejected'])
        self.assertTrue(result['legacyRegressionBound'])
        self.assertTrue(result['legacyInputMutationRejected'])
        self.assertTrue(result['packagedFilesUnchanged'])
        self.assertEqual(6,len(result['exportFiles']))


if __name__=='__main__':unittest.main()
