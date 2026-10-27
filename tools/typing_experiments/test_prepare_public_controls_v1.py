import json
from pathlib import Path
import tempfile
import unittest
from test_prepare_public_spelling_v1 import run_builder


def protected(**changes):
    return dict(id='new-control',language='ru',prefix='Сохраните точный токен в примере 0',typed='Amelia',
                cohort='protected',noAuto=True,expectedCandidate=0,candidates=[' Amelia',' Ameli'])|changes


class ControlsBuilderTest(unittest.TestCase):
    def test_real_protected_matrix_blocks_reuse_without_creating_output(self):
        with tempfile.TemporaryDirectory() as folder:
            result=run_builder(folder,'prepare_public_controls_v1.py',[protected()],['--kind','protected'])
            self.assertEqual(2,result.returncode,result.stderr);report=json.loads(result.stdout)
            self.assertEqual('BLOCKED_OVERLAP',report['status']);self.assertEqual(1,report['controlOverlaps']['protected'])
            self.assertFalse((Path(folder)/'output').exists())

    def test_unseen_authored_control_still_fails_incomplete_coverage(self):
        with tempfile.TemporaryDirectory() as folder:
            result=run_builder(folder,'prepare_public_controls_v1.py',[protected(prefix='Новый контекст проверки')],['--kind','protected'])
            self.assertEqual(2,result.returncode,result.stderr);report=json.loads(result.stdout)
            self.assertEqual('BLOCKED_COVERAGE',report['status']);self.assertFalse(report['sourceLabelsQualified'])
            self.assertFalse((Path(folder)/'output').exists())


if __name__=='__main__':unittest.main()
