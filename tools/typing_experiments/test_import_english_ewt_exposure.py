import hashlib
import unittest
from copy import deepcopy

import import_english_ewt_exposure as importer
import control_ledger
from holdout_ledger import assert_disjoint, keys_for
from test_holdout_ledger import ledger


class EwtExposureTest(unittest.TestCase):
    def sources(self):
        data = {}
        for name, index in [('dev', 1), ('test', 2), ('train', 3)]:
            data[name] = (f'# newdoc id = doc{index}\n# sent_id = id{index}\n'
                          f'# text = Example {index}.\n1\tExample\t_\tNOUN\t_\t_\t0\troot\t_\t_\n\n').encode()
        return data, {name: hashlib.sha256(value).hexdigest() for name, value in data.items()}

    def test_all_partitions_and_cross_source_sentence_overlap_are_excluded(self):
        data, hashes = self.sources(); rows = importer.rows_from_sources(data, hashes)
        d, overlap = importer.build(ledger(False), rows, {'fixture': 'a' * 64})
        self.assertEqual(0, overlap)
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:article'):
            assert_disjoint([rows[0]], d, kinds=('article',), require_complete=False)
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:sentence'):
            assert_disjoint([rows[0]], d, kinds=('sentence',), require_complete=False)
        tatoeba = {'sourceRepository': 'tatoeba', 'language': 'en', 'article': 'tatoeba:9',
                   'sentenceHash': rows[0]['sentenceHash']}
        self.assertEqual(keys_for([rows[0]], 'sentence'), keys_for([tatoeba], 'sentence'))
        # The source-only control entry uses the identical document namespace.
        self.assertEqual(keys_for([rows[0]], 'article'), {control_ledger.article_key(rows[0])})
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:sentence'):
            assert_disjoint([tatoeba], d, kinds=('sentence',), require_complete=False)
        with self.assertRaisesRegex(ValueError, 'EWT_ALREADY_IMPORTED'): importer.build(d, rows, {'fixture': 'a' * 64})

    def test_bad_identity_changed_source_and_missing_partition_fail(self):
        data, hashes = self.sources()
        altered = deepcopy(data); altered['dev'] += b'x'
        with self.assertRaisesRegex(ValueError, 'EWT_SOURCE_HASH'): importer.rows_from_sources(altered, hashes)
        with self.assertRaisesRegex(ValueError, 'EWT_SOURCE_SET'): importer.rows_from_sources({'dev': data['dev']}, hashes)
        rows = importer.rows_from_sources(data, hashes)
        for change in ({'article': 'ewt:'}, {'language': 'ru'}, {'article': 'ewt:  invalid'}):
            with self.assertRaises(ValueError): keys_for([rows[0] | change], 'article')


if __name__ == '__main__': unittest.main()
