import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import register_tatoeba_undo_continuation as subject


class RegistrationTest(unittest.TestCase):
    def test_registered_identity_and_actual_guard(self):
        ledger=subject.control.load(subject.source.CONTROL);entry=subject.entry()
        self.assertEqual([entry],[x for x in ledger['entries'] if x['id']==subject.ENTRY])
        self.assertEqual(10,len(entry['keys']))
        row={'language':'ru','prefix':'галина поехала в командировку в','typed':'Австрию'}
        self.assertIn(subject.control.key_for(row,'regression'),entry['keys'])
        with self.assertRaisesRegex(ValueError,'CONTROL_OVERLAP'):
            subject.control.assert_disjoint([row],ledger,'regression')

    def test_altered_receipt_is_refused(self):
        data=json.loads(subject.RECEIPT.read_bytes());data['laterPrefixChanges']=1
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'receipt.json';path.write_text(json.dumps(data))
            with mock.patch.object(subject,'RECEIPT',path),self.assertRaisesRegex(ValueError,'UNDO_CONTINUATION_RECEIPT'):
                subject.entry()


if __name__=='__main__':unittest.main()
