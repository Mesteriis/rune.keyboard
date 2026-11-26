import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from collections import Counter

import check_available_v6_articles as subject
from import_recovered_v6_history import PARENT_ENTRY


class RetainedV6ArticleMappingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / 'mapping'
        shutil.copytree(subject.DIRECTORY, self.directory)

    def test_retained_mapping_covers_both_registered_partitions(self):
        result = subject.check(self.directory)
        self.assertEqual({'calibration': 1651, 'holdout': 1614}, result['partitions'])
        self.assertEqual(3265, result['articles'])
        self.assertFalse(result['independentQualification'])

    def test_rehashed_mutation_does_not_replace_frozen_mapping(self):
        path = self.directory / 'articles.jsonl'
        rows = [json.loads(line) for line in path.read_bytes().splitlines()]
        rows[0]['shard'], rows[-1]['shard'] = rows[-1]['shard'], rows[0]['shard']
        raw = ''.join(json.dumps(row, sort_keys=True) + '\n' for row in rows).encode()
        path.write_bytes(raw)
        receipt_path = self.directory / 'receipt.json'
        receipt = json.loads(receipt_path.read_bytes())
        receipt['articlesSha256'] = hashlib.sha256(raw).hexdigest()
        receipt_path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, 'V6_ARTICLE_RECEIPT'):
            subject.check(self.directory)

    def test_claim_of_corpus_or_qualification_is_rejected(self):
        path = self.directory / 'receipt.json'
        receipt = json.loads(path.read_bytes())
        receipt['corpusRowsRecovered'] = True
        path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, 'V6_ARTICLE_RECEIPT'):
            subject.check(self.directory)

    def test_known_historical_article_overlaps_have_bound_source_shards(self):
        subject.check(self.directory)
        ledger = subject.recovery.holdout_ledger.load_ledger(subject.recovery.LEDGER)
        historical = set().union(*(set(e.get('keys', {}).get('article', []))
            for e in ledger['entries'] if e['id'] != PARENT_ENTRY
            and not e['id'].startswith('public-right-context-available-v6-')))
        rows = [json.loads(line) for line in (self.directory / 'articles.jsonl').read_bytes().splitlines()]
        parent_keys = next(set(e['keys']['article']) for e in ledger['entries'] if e['id'] == PARENT_ENTRY)
        self.assertTrue({row['articleKey'] for row in rows} <= parent_keys)
        counts = Counter((row['partition'], row['shard']) for row in rows if row['articleKey'] in historical)
        self.assertEqual([193, 25, 18, 16, 19, 12, 21, 0, 0, 0],
            [counts['calibration', f'{n:04d}.parquet'] for n in range(11, 21)])
        self.assertEqual([162, 20, 18, 23, 26, 19, 21, 0, 0, 0],
            [counts['holdout', f'{n:04d}.parquet'] for n in range(11, 21)])


if __name__ == '__main__':
    unittest.main()
