from pathlib import Path
import tempfile
import unittest
from unittest import mock
import register_wordrank_boundaries as subject


class SourceBoundaryDisclosureTest(unittest.TestCase):
    def test_source_bound_rows_and_keys(self):
        rows,_=subject.inputs();a,b=subject.entries()
        self.assertEqual(52,len(rows));self.assertEqual(51,sum(r['boundaryKind']=='hyphen' for r in rows))
        self.assertEqual(1,sum(r['boundaryKind']=='alphanumeric' for r in rows))
        self.assertTrue(a['surfaceKeys']);self.assertTrue(a['articleKeys']);self.assertTrue(b['keys']['context'])

    def test_changed_fixture_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'contexts.jsonl';path.write_bytes(subject.FIXTURE.read_bytes()+b' ')
            with mock.patch.object(subject,'FIXTURE',path),self.assertRaises(ValueError):subject.inputs()


if __name__=='__main__':unittest.main()
