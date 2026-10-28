import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).with_name("prepare_external_spelling_holdout_v11.py")
SPEC = importlib.util.spec_from_file_location("prepare_external_spelling_holdout_v11", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


class ExternalHoldoutV11Test(unittest.TestCase):
    def test_source_identity_and_partition_are_frozen(self):
        self.assertEqual(11, module.SPEC.version)
        self.assertEqual("0016", module.SPEC.shard)
        self.assertEqual(229_151_965, module.SPEC.source_bytes)
        self.assertEqual("0e2d2100e924ebedb057a37e789fec861fe2b78787c912c266e36eadd8d2e0a7",
                         module.SPEC.source_sha256)
        self.assertEqual("20231101.ru/train/0016.parquet", module.SPEC.source_path)


if __name__ == "__main__":
    unittest.main()
