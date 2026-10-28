import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("pack_rare_word_lexicon.py")
SPEC = importlib.util.spec_from_file_location("pack_rare_word_lexicon", SCRIPT)
packer = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(packer)


class PackRareWordsTest(unittest.TestCase):
    def test_packs_identity_bound_front_coded_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            words = source / "words.txt"
            counts = source / "counts.tsv"
            words.write_text("абава\nабаза\nабака\n", encoding="utf-8")
            counts.write_text("абака\t5\t3\nабава\t4\t3\nабаза\t3\t2\n", encoding="utf-8")
            (source / "manifest.json").write_text(json.dumps({"schemaVersion": 1,
                "containsPrivateText": False, "files": {"words.txt": packer.sha256(words),
                "counts.tsv": packer.sha256(counts)}}))
            output, receipt = root / "words.bin", root / "receipt.json"
            result = packer.pack(source, output, receipt)
            self.assertEqual(b"RUNERAR1", output.read_bytes()[:8])
            self.assertEqual(3, result["words"])
            self.assertEqual(result, json.loads(receipt.read_text()))


if __name__ == "__main__":
    unittest.main()
