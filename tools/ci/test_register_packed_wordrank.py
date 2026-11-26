from pathlib import Path
import tempfile
import unittest
from unittest import mock
import register_packed_wordrank as subject


class PackedDisclosureTest(unittest.TestCase):
    def test_captured_entries_bind_all_disclosed_contexts(self):
        rows,_=subject.inputs();control,lexical=subject.entries()
        self.assertEqual(3,len(rows));self.assertEqual(3,control['rowCount'])
        self.assertEqual(3,len(control['keys']));self.assertEqual(3,len(lexical['keys']['context']))
        self.assertTrue(control['surfaceKeys']);self.assertTrue(control['articleKeys'])

    def test_mutated_capture_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'contexts.jsonl';path.write_bytes(subject.FIXTURE.read_bytes()+b' ')
            with mock.patch.object(subject,'FIXTURE',path),self.assertRaises(ValueError):subject.inputs()


if __name__=='__main__':unittest.main()
