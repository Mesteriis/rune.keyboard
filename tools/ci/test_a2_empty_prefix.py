import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import a2_empty_prefix_screen as screen
import register_a2_empty_prefix as subject


class EmptyPrefixTest(unittest.TestCase):
    def test_registered_in_both_applicable_ledgers(self):
        rows,_=subject.inputs();self.assertEqual(10,subject.check())
        for row in rows:
            with self.assertRaisesRegex(ValueError,'CONTROL_OVERLAP:regression'):
                subject.control.assert_disjoint([row],subject.control.load(subject.CONTROL),'regression')
        russian=next(row for row in rows if row['language']=='ru')
        with self.assertRaisesRegex(ValueError,'LEDGER_OVERLAP:context'):
            subject.lexical.assert_disjoint([russian],subject.lexical.load_ledger(subject.LEXICAL),
                                            kinds=('context',),require_complete=False)

    def test_scorer_response_identity_and_numeric_validation(self):
        cases=[dict(id='one',candidates=['a','b'])]
        valid={'id':'one','scores':[{'id':0,'sumLogProbability':-1.0,'scoredTokenCount':1},
                                   {'id':1,'sumLogProbability':-2.0,'scoredTokenCount':1}],'durationMillis':1}
        self.assertEqual([{'id':'one','scores':valid['scores']}],screen.normalize(cases,[json.dumps(valid)]))
        wrong=copy.deepcopy(valid);wrong['scores'][0]['id']=2
        with self.assertRaises(ValueError):screen.normalize(cases,[json.dumps(wrong)])
        with self.assertRaises(ValueError):screen.normalize(cases,[])

    def test_registry_check_without_build(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            names=('tools/ci/register_a2_empty_prefix.py','tools/typing_experiments/control_ledger.py',
                   'tools/typing_experiments/holdout_ledger.py','tools/typing_experiments/conversation_split_checks.py',
                   'tools/typing_experiments/source_identities.py','tools/typing_experiments/control-ledger.json',
                   'tools/typing_experiments/holdout-ledger.json')
            for name in names:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(subject.ROOT/name,path)
            shutil.copytree(subject.DATA,root/'tools/typing_experiments/a2-empty-prefix-controls-v1')
            result=subprocess.run([sys.executable,'-I',str(root/'tools/ci/register_a2_empty_prefix.py'),'--check'],
                                  cwd=root,text=True,capture_output=True,timeout=120)
            self.assertEqual(0,result.returncode,result.stderr)
            self.assertEqual({'contexts':10,'independentQualification':False},json.loads(result.stdout))
            self.assertFalse((root/'build').exists())


if __name__=='__main__':unittest.main()
