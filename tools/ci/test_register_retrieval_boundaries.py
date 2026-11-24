from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock
import register_retrieval_boundaries as subject


class HistoricalBoundaryTest(unittest.TestCase):
    def test_rows_and_registry_overlap(self):
        rows, _ = subject.inputs()
        self.assertEqual(9, len(rows))
        self.assertEqual(9, subject.check())
        with self.assertRaisesRegex(ValueError, 'CONTROL_OVERLAP:regression'):
            subject.control.assert_disjoint([rows[0]], subject.control.load(subject.CONTROL), 'regression')
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:context'):
            subject.lexical.assert_disjoint([rows[0]], subject.lexical.load_ledger(subject.LEXICAL),
                                            kinds=('context',), require_complete=False)

    def test_modified_fixture_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / 'fixture'
            shutil.copytree(subject.FIXTURE, fixture)
            row = fixture / 'contexts.jsonl'
            row.write_bytes(row.read_bytes().replace(b'\n', b' \n', 1))
            with mock.patch.object(subject, 'FIXTURE', fixture):
                with self.assertRaisesRegex(ValueError, 'SOURCE_BOUNDARY_DISCLOSURE_BINDING'):
                    subject.inputs()


if __name__ == '__main__':
    unittest.main()
