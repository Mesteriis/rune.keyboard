import bz2
import hashlib
import unittest
from unittest.mock import patch

import import_english_tatoeba_screen as importer
from holdout_ledger import assert_disjoint
from test_holdout_ledger import ledger


class EnglishTatoebaScreenTest(unittest.TestCase):
    def test_disclosed_id_and_normalized_text_are_both_excluded(self):
        data = bz2.compress('1\teng\tHello there.\towner\n2\teng\tOther text.\towner\n'.encode())
        with patch.object(importer, 'DIGEST', hashlib.sha256(data).hexdigest()):
            result = importer.build(ledger(False), data, {'source': hashlib.sha256(data).hexdigest()})
        first = importer.rows_from_bytes(data)[0]
        for kind in ('article', 'sentence'):
            with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:' + kind):
                assert_disjoint([first], result, kinds=(kind,), require_complete=False)
        self.assertFalse(result['coverage']['complete'])

    def test_rejects_invalid_and_duplicate_rows_and_changed_source(self):
        for raw in ('1\trus\ttext\ta\n', '1\teng\ttext\ta\n01\teng\tother\ta\n', '1\teng\t \ta\n'):
            with self.assertRaises(ValueError):
                importer.rows_from_bytes(bz2.compress(raw.encode()))
        with self.assertRaisesRegex(ValueError, 'EN_TATOEBA_SOURCE_DIGEST'):
            importer.build(ledger(False), b'incorrect', {'source': 'a' * 64})


if __name__ == '__main__':
    unittest.main()
