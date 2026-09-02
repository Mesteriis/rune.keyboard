import hashlib
import struct
import unittest

from derive import HEADER, RECORD, derive, validate


def fixture(words):
    tree = {"children": {}, "terminal": 0}
    for ordinal, word in enumerate(sorted(words), 1):
        node = tree
        for char in word:
            node = node["children"].setdefault(char, {"children": {}, "terminal": 0})
        node["terminal"] = ordinal
    records, bounds = [], []

    def walk(node, char, depth):
        index = len(records)
        records.append([ord(char) if char else 0, 0, 0, node["terminal"]])
        bounds.append(None)
        children = []
        low = depth if node["terminal"] else 33
        high = depth if node["terminal"] else 0
        for label, child in sorted(node["children"].items()):
            child_id = walk(child, label, depth + 1)
            children.append(child_id)
            low, high = min(low, bounds[child_id][0]), max(high, bounds[child_id][1])
        if children:
            records[index][1] = children[0]
        for a, b in zip(children, children[1:]):
            records[a][2] = b
        bounds[index] = (low, high)
        return index

    walk(tree, "", 0)
    trie = struct.pack("<4sIII", b"RTR1", len(words), len(records), 16)
    trie += b"".join(struct.pack("<4I", *r) for r in records)
    lengths = struct.pack("<4sIII", b"LEN1", 1, len(records), 0) + b"".join(bytes(b) for b in bounds)
    digest = hashlib.sha256(("\n".join(sorted(words)) + "\n").encode()).hexdigest()
    return trie, lengths, digest


class RadixDerivation(unittest.TestCase):
    def test_prefix_terminals_branches_and_scalar_labels_preserve_word_stream(self):
        source = fixture(["a", "abc", "abd", "albatross", "é", "école", "ё", "ёлка", "😀abc", "😀abd"])
        result = derive(*source)
        report = validate(result, source[2])
        self.assertEqual(10, report["words"])
        self.assertLess(report["nodes"], (len(source[0]) - 16) // 16)
        self.assertEqual(result, derive(*source))

    def test_maximum_path_length_and_leaf_chain(self):
        source = fixture(["😀" * 32])
        result = derive(*source)
        self.assertEqual(2, validate(result, source[2])["nodes"])
        self.assertEqual((32, 128, 32, 32), RECORD.unpack_from(result, HEADER.size + RECORD.size)[4:])
        with self.assertRaises(ValueError):
            derive(*fixture(["a" * 33]))

    def test_bad_source_identity_topology_lengths_and_ordinals_are_rejected(self):
        trie, lengths, digest = fixture(["abc", "abd"])
        mutations = [(0, b"BAD1"), (16 + 16 + 4, struct.pack("<I", 1)),
                     (16 + 3 * 16 + 12, struct.pack("<I", 2))]
        for offset, replacement in mutations:
            changed = bytearray(trie)
            changed[offset:offset + len(replacement)] = replacement
            with self.assertRaises(ValueError):
                derive(changed, lengths, digest)
        changed = bytearray(lengths)
        changed[16] = 1
        with self.assertRaises(ValueError):
            derive(trie, changed, digest)
        with self.assertRaises(ValueError):
            derive(trie, lengths, "0" * 64)

    def test_compressed_decoder_rejects_changed_bounds_ids_offsets_utf8_and_trailing_bytes(self):
        source = fixture(["abc", "abd"])
        good = derive(*source)
        mutations = [(HEADER.size + 4, struct.pack("<I", 2)),
                     (HEADER.size + RECORD.size, struct.pack("<I", 1)),
                     (HEADER.size + RECORD.size + 18, bytes([1])),
                     (len(good) - 1, b"\xff")]
        for offset, replacement in mutations:
            changed = bytearray(good)
            changed[offset:offset + len(replacement)] = replacement
            with self.assertRaises(ValueError):
                validate(changed, source[2])
        with self.assertRaises(ValueError):
            validate(good + b"x", source[2])


if __name__ == "__main__":
    unittest.main()
