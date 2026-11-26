import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import register_authored_short_search as subject


class ShortSearchDisclosureTest(unittest.TestCase):
    def test_output_contexts_are_registered(self):
        rows, _ = subject.inputs()
        self.assertEqual(24, len(rows))
        self.assertEqual(24, subject.check())
        case = next(row for row in rows if row['typed'] == 'метро')
        with self.assertRaisesRegex(ValueError, 'CONTROL_OVERLAP:regression'):
            subject.control.assert_disjoint([case], subject.control.load(subject.CONTROL), 'regression')
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:context'):
            subject.lexical.assert_disjoint([case], subject.lexical.load_ledger(subject.LEXICAL),
                                            kinds=('context',), require_complete=False)

    def test_modified_projection_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder) / 'fixture'; shutil.copytree(subject.SEARCH, fixture)
            path = fixture / 'projection.jsonl'; path.write_bytes(path.read_bytes() + b' ')
            with mock.patch.object(subject, 'SEARCH', fixture):
                with self.assertRaisesRegex(ValueError, 'SHORT_SEARCH_BINDING'):
                    subject.inputs()

    def test_no_build_registry_check(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            names=('tools/ci/register_authored_dialogue.py','tools/ci/register_authored_phrase_inputs.py',
                   'tools/ci/register_authored_typo_inputs.py','tools/ci/register_authored_short_search.py',
                   'tools/typing_experiments/control_ledger.py','tools/typing_experiments/holdout_ledger.py',
                   'tools/typing_experiments/conversation_split_checks.py','tools/typing_experiments/source_identities.py',
                   'tools/typing_experiments/control-ledger.json','tools/typing_experiments/holdout-ledger.json')
            for name in names:
                dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(subject.ROOT/name,dest)
            for fixture in ('authored-dialogue-v1','authored-short-search-v1'):
                shutil.copytree(subject.ROOT/'tools/typing_experiments'/fixture,root/'tools/typing_experiments'/fixture)
            result=subprocess.run([sys.executable,'-I',str(root/'tools/ci/register_authored_short_search.py'),'--check'],
                                  cwd=root,text=True,capture_output=True,timeout=120)
            self.assertEqual(0,result.returncode,result.stderr)
            self.assertEqual({'tokens':24,'independentQualification':False},json.loads(result.stdout))
            self.assertFalse((root/'build').exists())


if __name__=='__main__':unittest.main()
