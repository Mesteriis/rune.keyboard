import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).with_name("prepare_external_spelling_holdout_v12.py")
SPEC = importlib.util.spec_from_file_location("prepare_external_spelling_holdout_v12", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


class ExternalHoldoutV12Test(unittest.TestCase):
    def test_source_identity_and_partition_are_frozen(self):
        self.assertEqual(12, module.SPEC.version)
        self.assertEqual("0017", module.SPEC.shard)
        self.assertEqual(210_166_516, module.SPEC.source_bytes)
        self.assertEqual("1a5c96dfda452e7725229760347e781b46f88ccd5df4196a5c1a9d46b51b1a65",
                         module.SPEC.source_sha256)


if __name__ == "__main__":
    unittest.main()
