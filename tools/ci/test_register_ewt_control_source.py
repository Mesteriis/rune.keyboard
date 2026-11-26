import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

import register_ewt_control_source as subject


class EwtControlSourceTest(unittest.TestCase):
    def test_registered_keys_equal_disclosed_lexical_documents(self):
        ledger=subject.lexical.load_ledger(subject.LEXICAL)
        parent=next(e for e in ledger['entries'] if e['id']==subject.PARENT)
        entry=subject.entry(ledger)
        self.assertEqual(parent['keys']['article'],entry['articleKeys'])
        self.assertEqual(1174,len(entry['articleKeys']))
        self.assertEqual('source',entry['kind'])
        self.assertEqual([],entry['keys'])
        self.assertEqual(1174,subject.check())
        self.assertFalse(subject.control.load(subject.CONTROL)['coverageComplete'])

    def test_changed_parent_key_and_metadata_are_rejected(self):
        ledger=subject.lexical.load_ledger(subject.LEXICAL)
        for mutation in ('key','scope'):
            changed=copy.deepcopy(ledger);parent=next(e for e in changed['entries'] if e['id']==subject.PARENT)
            if mutation=='key':
                parent['keys']['article'][0]='0'*64
                parent['keys']['article']=sorted(set(parent['keys']['article']))
            else:parent['sourceRepository']='other'
            with self.assertRaises(ValueError):subject.entry(changed)

    def test_changed_registered_document_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'control-ledger.json'
            ledger=json.loads(subject.CONTROL.read_bytes())
            entry=next(e for e in ledger['entries'] if e['id']==subject.ENTRY)
            entry['articleKeys'][0]='0'*64
            entry['articleKeys']=sorted(set(entry['articleKeys']))
            path.write_text(json.dumps(ledger))
            with mock.patch.object(subject,'CONTROL',path):
                with self.assertRaisesRegex(ValueError,'EWT_CONTROL_DRIFT'):
                    subject.check()

    def test_corrupt_archived_helper_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture=Path(directory)/'fixture';shutil.copytree(subject.FIXTURE,fixture)
            (fixture/'sources'/(subject.CONTROL_SHA+'.txt')).write_bytes(b'changed')
            with mock.patch.object(subject,'FIXTURE',fixture):
                with self.assertRaisesRegex(ValueError,'EWT_CONTROL_HELPER_DRIFT'):
                    subject.entry(json.loads(subject.LEXICAL.read_bytes()))


if __name__=='__main__':unittest.main()
