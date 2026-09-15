import hashlib
from pathlib import Path
import struct
import tempfile
import unittest

from export_dictionary import accepted, dictionary_records, write_index
from dictionary_index import DictionaryIndex


class DictionaryExportTest(unittest.TestCase):
    def test_exact_front_coding_and_reproducibility_across_blocks(self):
        records = sorted([(f"слово{'а' * i}", i + 1) for i in range(1, 28)] +
                         [(f"тест{'а' * i}", i + 50) for i in range(1, 20)] + [("почтений", 0)])
        with tempfile.TemporaryDirectory() as root:
            first, second = Path(root) / "first", Path(root) / "second"
            a, b = write_index(records, first), write_index(records, second)
            self.assertEqual(a, b)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            data = first.read_bytes()
            self.assertEqual(data[-32:], hashlib.sha256(data[:-32]).digest())
            width, count, blocks, start = struct.unpack_from("<IIII", data, 8)
            decoded = []
            for block in range(blocks):
                offset = start + struct.unpack_from("<I", data, 24 + block * 4)[0]
                previous = b""
                for _ in range(min(width, count - block * width)):
                    prefix, suffix, lemma = struct.unpack_from("<BBI", data, offset)
                    word = previous[:prefix] + data[offset + 6:offset + 6 + suffix]
                    decoded.append((word.decode("utf-8"), lemma))
                    previous = word
                    offset += 6 + suffix
            self.assertEqual(records, decoded)
            with DictionaryIndex(first) as index:
                for word, _ in records:
                    self.assertTrue(index.contains(word))
                self.assertTrue(index.contains("Почтений"))
                self.assertFalse(index.contains("почтения"))
                self.assertFalse(index.contains("ыыыы"))
                self.assertFalse(index.contains("а"))
            with self.assertRaises(ValueError):
                index.contains("почтений")
            corrupt = bytearray(data)
            corrupt[40] ^= 1
            second.write_bytes(corrupt)
            with self.assertRaises(ValueError):
                with DictionaryIndex(second):
                    pass

    def test_dictionary_filters_and_invalid_order(self):
        self.assertTrue(accepted("почтений"))
        self.assertTrue(accepted("кто-то"))
        for word in ("Почтений", "x", "", "1-ая", "а" * 33, "а--б"):
            self.assertFalse(accepted(word))
        with tempfile.TemporaryDirectory() as root:
            for records in ([], [("б", 1), ("а", 2)], [("а", 1), ("а", 2)]):
                with self.assertRaises(ValueError):
                    write_index(records, Path(root) / "invalid")

    def test_analysis_ambiguity_is_not_discarded(self):
        class Words:
            def iteritems(self):
                return iter([("а", (1, 0)), ("а", (2, 0)), ("б", (1, 0)), ("в", (1, 1))])
        class Dictionary:
            words = Words()
            def build_normal_form(self, para, idx, word):
                return "б" if word in ("б", "в") else "а"
        stats = {"ambiguousWords": 0}
        self.assertEqual([("а", 0), ("б", 1), ("в", 1)], list(dictionary_records(Dictionary(), stats)))
        self.assertEqual({"ambiguousWords": 1, "lemmaFamilies": 1}, stats)


if __name__ == "__main__":
    unittest.main()
