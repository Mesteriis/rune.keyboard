import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import register_a2_empty_candidates as subject


class EmptyControllerDisclosureTest(unittest.TestCase):
    def test_registered_candidate_context_is_blocked(self):
        rows,_=subject.inputs();self.assertEqual(42,subject.check())
        row=next(r for r in rows if r['typed']=='молот')
        with self.assertRaisesRegex(ValueError,'CONTROL_OVERLAP:regression'):
            subject.control.assert_disjoint([row],subject.control.load(subject.CONTROL),'regression')
        with self.assertRaisesRegex(ValueError,'LEDGER_OVERLAP:context'):
            subject.lexical.assert_disjoint([row],subject.lexical.load_ledger(subject.LEXICAL),
                                            kinds=('context',),require_complete=False)

    def test_changed_projection_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'fixture';shutil.copytree(subject.SEARCH,target)
            p=target/'projection.jsonl';p.write_bytes(p.read_bytes()+b' ')
            with mock.patch.object(subject,'SEARCH',target),self.assertRaisesRegex(ValueError,'EMPTY_CONTROLLER_BINDING'):
                subject.inputs()

    def test_without_build(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            files=('tools/ci/register_a2_empty_prefix.py','tools/ci/register_a2_empty_candidates.py',
                   'tools/typing_experiments/control_ledger.py','tools/typing_experiments/holdout_ledger.py',
                   'tools/typing_experiments/conversation_split_checks.py','tools/typing_experiments/source_identities.py',
                   'tools/typing_experiments/control-ledger.json','tools/typing_experiments/holdout-ledger.json')
            for name in files:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(subject.ROOT/name,p)
            for name in ('a2-empty-prefix-controls-v1','a2-empty-controller-v1'):
                shutil.copytree(subject.ROOT/'tools/typing_experiments'/name,root/'tools/typing_experiments'/name)
            result=subprocess.run([sys.executable,'-I',str(root/'tools/ci/register_a2_empty_candidates.py'),'--check'],
                                  cwd=root,text=True,capture_output=True,timeout=120)
            self.assertEqual(0,result.returncode,result.stderr)
            self.assertEqual({'tokens':42,'independentQualification':False},json.loads(result.stdout))
            self.assertFalse((root/'build').exists())


if __name__=='__main__':unittest.main()
