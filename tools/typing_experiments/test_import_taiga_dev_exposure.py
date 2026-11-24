import hashlib
import unittest

import import_taiga_dev_exposure as importer
from holdout_ledger import assert_disjoint, keys_for
from test_holdout_ledger import ledger


class TaigaExposureTest(unittest.TestCase):
    def test_sentence_exclusion_and_cross_source_normalization(self):
        data = '# newdoc\n# sent_id = a\n# text = Привет мир!\n1\tПривет\n\n'.encode()
        keys, count = importer.sentence_keys(data, hashlib.sha256(data).hexdigest())
        result, overlap = importer.build(ledger(False), keys, count, {'fixture': 'a' * 64})
        self.assertEqual((1, 0), (count, overlap))
        sentence = hashlib.sha256('привет мир!'.encode()).hexdigest()
        row = {'sourceRepository': 'tatoeba', 'language': 'ru', 'article': 'tatoeba:1', 'sentenceHash': sentence}
        self.assertEqual(set(keys), keys_for([row], 'sentence'))
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:sentence'):
            assert_disjoint([row], result, kinds=('sentence',), require_complete=False)
        with self.assertRaisesRegex(ValueError, 'TAIGA_ALREADY_IMPORTED'):
            importer.build(result, keys, count, {'fixture': 'a' * 64})

    def test_rejects_bad_hash_duplicate_and_missing_text(self):
        def parse(text):
            data = text.encode()
            return importer.sentence_keys(data, hashlib.sha256(data).hexdigest())
        with self.assertRaisesRegex(ValueError, 'TAIGA_SOURCE_HASH'):
            importer.sentence_keys(b'changed', '0' * 64)
        with self.assertRaisesRegex(ValueError, 'TAIGA_SENTENCE_ID'):
            parse('# sent_id = a\n# text = x\n\n# sent_id = a\n# text = y\n')
        with self.assertRaisesRegex(ValueError, 'TAIGA_SENTENCE_INCOMPLETE'):
            parse('# sent_id = a\n\n')
