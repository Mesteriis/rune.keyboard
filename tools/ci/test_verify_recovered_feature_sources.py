import shutil
import tempfile
import unittest
from pathlib import Path

import verify_recovered_feature_sources as recovered


class RecoveredFeatureSourcesTest(unittest.TestCase):
    def test_source_and_receipt_must_remain_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for archived, _, _, receipt in recovered.SPECS:
                for relative in (Path('tools/typing_experiments/frozen_sources') / archived,
                                 Path('docs/acceptance') / receipt):
                    destination = root / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(recovered.ROOT / relative, destination)
            self.assertEqual(2, recovered.verify(root))
            archived = root / 'tools/typing_experiments/frozen_sources' / recovered.SPECS[0][0]
            archived.write_bytes(archived.read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'RECOVERED_FEATURE_SOURCE_IDENTITY'):
                recovered.verify(root)
            shutil.copyfile(recovered.ROOT / 'tools/typing_experiments/frozen_sources' / recovered.SPECS[0][0], archived)
            receipt = root / 'docs/acceptance' / recovered.SPECS[0][3]
            data = receipt.read_text().replace(recovered.SPECS[0][2], '0' * 64)
            receipt.write_text(data)
            with self.assertRaisesRegex(ValueError, 'RECOVERED_FEATURE_RECEIPT_IDENTITY'):
                recovered.verify(root)


if __name__ == '__main__':
    unittest.main()
