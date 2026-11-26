import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import register_ewt_product_contexts as subject


class EwtProductContextsTest(unittest.TestCase):
    def test_source_bound_contexts_are_in_real_registry(self):
        expected=subject.entry();ledger=subject.control.load(subject.LEDGER)
        self.assertEqual([expected],[e for e in ledger['entries'] if e['id']==subject.ENTRY])
        self.assertEqual(533,len(expected['keys']))
        self.assertFalse(json.loads(subject.FIXTURE.read_bytes())['independentQualification'])

    def test_modified_fixture_refuses_registration(self):
        value=json.loads(subject.FIXTURE.read_bytes());value['sourceLockSha256']='0'*64
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'fixture.json';path.write_text(json.dumps(value))
            with mock.patch.object(subject,'FIXTURE',path):
                with self.assertRaisesRegex(ValueError,'EWT_CONTEXT_FIXTURE'):
                    subject.entry()


if __name__=='__main__':unittest.main()
