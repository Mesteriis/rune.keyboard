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
    import extra_epoch_evaluation_smoke as smoke
finally:sys.path[:]=old_path


class ExtraEpochEvaluationDriverTest(unittest.TestCase):
    def test_disclosed_bound_comparison_cannot_qualify_and_keeps_packaged_files(self):
        with temporary_build_directory(ROOT) as folder,contextlib.redirect_stdout(io.StringIO()):
            result=smoke.run(Path(folder)/'output')
        self.assertTrue(result['packagedFilesUnchanged'])
        extra=result['extraComparison']
        self.assertEqual((4,4,4),(extra['mainRows'],extra['previousRows'],extra['legacyRows']))
        self.assertFalse(extra['accepted']);self.assertTrue(extra['devInputMutationRejected'])


if __name__=='__main__':unittest.main()
