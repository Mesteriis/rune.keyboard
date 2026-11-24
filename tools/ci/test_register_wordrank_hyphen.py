from pathlib import Path
import tempfile
import unittest
from unittest import mock
import register_wordrank_hyphen as subject


class HyphenDisclosureTest(unittest.TestCase):
    def test_source_bound_rows_and_component_protection(self):
        rows,_=subject.inputs();a,b=subject.entries()
        self.assertEqual(5,len(rows));self.assertEqual(3,len(a['surfaceKeys']))
        self.assertEqual(5,len(a['articleKeys']));self.assertEqual(5,len(b['keys']['context']))

    def test_mutated_source_capture_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'contexts.jsonl';path.write_bytes(subject.FIXTURE.read_bytes()+b' ')
            with mock.patch.object(subject,'FIXTURE',path),self.assertRaises(ValueError):subject.inputs()


if __name__=='__main__':unittest.main()
