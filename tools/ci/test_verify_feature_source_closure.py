import json
from pathlib import Path
import shutil
import tempfile
import unittest

import verify_feature_source_closure as closure


class FeatureSourceClosureTest(unittest.TestCase):
    def test_source_and_receipt_mutations_are_rejected(self):
        snapshot = json.loads((closure.ROOT / closure.SNAPSHOT).read_bytes())
        paths = {closure.SNAPSHOT}
        for corpus in snapshot['corpora']:
            paths.add('docs/acceptance/' + corpus['receipt'])
            paths.update(item['trackedPath'] for item in corpus['sources'])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for relative in paths:
                dest = root / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(closure.ROOT / relative, dest)
            self.assertEqual(11, closure.verify(root))
            relative = snapshot['corpora'][0]['sources'][0]['trackedPath']
            target = root / relative
            target.write_bytes(target.read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'FEATURE_CLOSURE_SOURCE'):
                closure.verify(root)
            shutil.copyfile(closure.ROOT / relative, target)
            corpus = snapshot['corpora'][0]
            receipt = root / 'docs/acceptance' / corpus['receipt']
            receipt.write_text(receipt.read_text().replace(corpus['manifestSha256'], '0' * 64))
            with self.assertRaisesRegex(ValueError, 'FEATURE_CLOSURE_PARENT'):
                closure.verify(root)


if __name__ == '__main__':
    unittest.main()
