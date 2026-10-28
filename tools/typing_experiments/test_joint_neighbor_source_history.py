"""Historical source/receipt integrity; no training scripts are executed."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'docs/acceptance/2026-10-28-q2-joint-neighbor-sources-evidence.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class JointNeighborSourceHistoryTest(unittest.TestCase):
    def setUp(self):
        self.evidence = json.loads(EVIDENCE.read_text())

    def test_original_receipt_bytes_are_retained(self):
        records = self.evidence['archivedReceipts']
        self.assertEqual(5, len(records))
        for name, record in records.items():
            with self.subTest(receipt=name):
                self.assertEqual(record['sha256'], sha(ROOT / name))

    def test_joint_sources_match_original_receipt_fields(self):
        records = self.evidence['historicalSourceMatches']
        self.assertEqual(2, len(records))
        for record in records:
            with self.subTest(source=record['source']):
                receipt = json.loads((ROOT / record['receipt']).read_text())
                self.assertEqual(record['sha256'], receipt[record['field']])
                self.assertEqual(record['sha256'], sha(ROOT / record['source']))

    def test_preparers_match_exact_frozen_sources(self):
        records = self.evidence['frozenBuilderMatches']
        self.assertEqual(3, len(records))
        for record in records:
            with self.subTest(source=record['source']):
                self.assertEqual(record['sha256'], sha(ROOT / record['source']))
                self.assertEqual(record['sha256'], sha(ROOT / record['archived']))

    def test_reconstructed_neighbor_tool_matches_original_complete_file_digest(self):
        records = self.evidence['recoveredHistoricalSources']
        self.assertEqual(1, len(records))
        for record in records:
            receipt = json.loads((ROOT / record['receipt']).read_text())
            self.assertEqual(record['expectedSha256'], receipt[record['field']])
            self.assertEqual(record['expectedSha256'], sha(ROOT / record['archived']))
            self.assertFalse(record['executed'])


if __name__ == '__main__':
    unittest.main()
