"""Verify original v6 text artifacts against the frozen recovery receipts."""

import bz2
import hashlib
import json
import unittest
import unicodedata

import check_available_v6_calibration_index
import holdout_ledger
import check_available_v6_contexts as anchors_check
from test_available_v6_recovery import FIXTURE, MANIFEST, MANIFEST_SHA256, ROOT

LOGGED_ROW = FIXTURE.with_name('available_clean_v6_logged_calibration_row.json')


class AvailableV6HistoricalArtifactsTest(unittest.TestCase):
    def test_calibration_tsv_index_covers_registered_articles_contexts_and_families(self):
        self.assertEqual(
            dict(rows=7905, contexts=1661, articles=1651, families=588),
            check_available_v6_calibration_index.check(),
        )

    def test_calibration_attribution_binds_the_original_archive_bytes(self):
        archive = check_available_v6_calibration_index.DIRECTORY / 'calibration.tsv.bz2'
        receipt = archive.parent.parent / 'calibration-attribution/receipt.json'
        bindings = json.loads(receipt.read_bytes())['bindings']
        self.assertEqual(bindings[archive.relative_to(ROOT).as_posix()],
                         hashlib.sha256(archive.read_bytes()).hexdigest())

    def test_recovered_calibration_archive_reopens_to_exact_historical_bytes(self):
        root = check_available_v6_calibration_index.DIRECTORY.parent
        manifest_bytes = MANIFEST.read_bytes()
        self.assertEqual(MANIFEST_SHA256, hashlib.sha256(manifest_bytes).hexdigest())
        manifest = json.loads(manifest_bytes)
        with bz2.open(root / "calibration-recovery/calibration.tsv.bz2", "rb") as stream:
            raw = stream.read(3_266_374)
        self.assertEqual(3_266_373, len(raw))
        self.assertEqual(manifest["files"]["calibration.tsv"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(manifest["counts"]["calibration"]["rows"], raw.count(b"\n"))
        self.assertFalse(manifest["holdoutScoringAllowed"])

    def test_logged_row_is_an_already_disclosed_historical_calibration_example(self):
        raw = LOGGED_ROW.read_bytes()
        self.assertEqual('5061b2449adfe6b306b354432de6a3d2dbfe1823e86a489d64e914ea659d9490',
                         hashlib.sha256(raw).hexdigest())
        row = json.loads(raw)
        self.assertEqual(('calibration', 'calibration', 'typo', False, False),
            (row['part'], row['split'], row['group'], row['noAuto'], row['retainBaseline']))
        self.assertEqual('0018.parquet', row['source'])
        self.assertEqual(row['word'], row['expectedSpelling'])
        context = ' '.join(unicodedata.normalize('NFC',
            row['prefix'] + ' ' + row['word'] + row['rightContext']).casefold().split())
        self.assertEqual(row['contextHash'], hashlib.sha256(context.encode()).hexdigest())
        ledger = holdout_ledger.load_ledger(ROOT / 'tools/typing_experiments/holdout-ledger.json')
        entry = next(e for e in ledger['entries'] if e['id'] == 'public-right-context-available-v6-calibration')
        for axis in ('article', 'family', 'sentence', 'context'):
            with self.subTest(axis=axis):
                self.assertTrue(holdout_ledger.keys_for([row], axis) <= set(entry['keys'][axis]))

    def test_logged_observation_has_one_matching_same_partition_anchor(self):
        anchors_check.check(anchors_check.DIRECTORY)
        row = json.loads(LOGGED_ROW.read_bytes())
        anchors = [json.loads(line) for line in (anchors_check.DIRECTORY / 'anchors.jsonl').read_bytes().splitlines()]
        matches = [a for a in anchors if a['article'] == row['article'] and a['contextHash'] == row['contextHash']]
        self.assertEqual(1, len(matches))
        self.assertEqual((row['split'], row['split'], row['source']),
            (matches[0]['articlePartition'], matches[0]['sentencePartition'], matches[0]['source']))



if __name__ == "__main__":
    unittest.main()
