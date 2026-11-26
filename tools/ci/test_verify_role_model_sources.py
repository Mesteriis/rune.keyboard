import json
from pathlib import Path
import shutil
import tempfile
import unittest

import verify_role_model_sources as inventory


class RoleModelSourcesTest(unittest.TestCase):
    def test_source_and_inventory_mutations_are_rejected(self):
        data = json.loads((inventory.ROOT / inventory.INVENTORY).read_bytes())
        paths = {inventory.INVENTORY}
        paths.update(source['trackedPath'] for record in data['records'] for source in record['sourceBindings'])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for relative in paths:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(inventory.ROOT / relative, target)
            self.assertEqual((14, 322, 53), inventory.verify(root))
            relative = data['records'][0]['sourceBindings'][0]['trackedPath']
            target = root / relative
            target.write_bytes(target.read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'ROLE_MODEL_SOURCE_DRIFT'):
                inventory.verify(root)
            shutil.copyfile(inventory.ROOT / relative, target)
            snapshot = root / inventory.INVENTORY
            snapshot.write_bytes(snapshot.read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'ROLE_MODEL_INVENTORY_DRIFT'):
                inventory.verify(root)


if __name__ == '__main__':
    unittest.main()
