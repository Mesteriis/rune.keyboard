#!/usr/bin/env python3
"""Pack the frozen public rare-word supplement for bounded Android lookup."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct


MAGIC = b"RUNERAR1"
BLOCK_SIZE = 32
HEADER_BYTES = 24


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def common_prefix(left: bytes, right: bytes) -> int:
    count = 0
    for a, b in zip(left, right):
        if a != b or count == 255:
            break
        count += 1
    return count


def pack(source: Path, output: Path, receipt: Path) -> dict:
    source = source.resolve(strict=True)
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    words_path, counts_path = source / "words.txt", source / "counts.tsv"
    if (manifest.get("schemaVersion") != 1 or manifest.get("containsPrivateText") is not False or
            sha256(words_path) != manifest.get("files", {}).get("words.txt") or
            sha256(counts_path) != manifest.get("files", {}).get("counts.tsv")):
        raise ValueError("SUPPLEMENT_IDENTITY")
    words = words_path.read_text(encoding="utf-8").splitlines()
    if words != sorted(set(words)) or not words:
        raise ValueError("SUPPLEMENT_WORDS")
    ranks = {}
    for rank, line in enumerate(counts_path.read_text(encoding="utf-8").splitlines(), 1):
        fields = line.split("\t")
        if len(fields) != 3 or fields[0] in ranks:
            raise ValueError("SUPPLEMENT_COUNTS")
        ranks[fields[0]] = rank
    if set(ranks) != set(words):
        raise ValueError("SUPPLEMENT_COUNTS")

    data = bytearray()
    offsets = []
    previous = b""
    for index, word in enumerate(words):
        encoded = word.encode("utf-8")
        if len(encoded) > 255:
            raise ValueError("WORD_TOO_LONG")
        if index % BLOCK_SIZE == 0:
            offsets.append(len(data))
            prefix = 0
        else:
            prefix = common_prefix(previous, encoded)
        suffix = encoded[prefix:]
        if not suffix or len(suffix) > 255:
            raise ValueError("INVALID_SUFFIX")
        data.extend(struct.pack("<BBI", prefix, len(suffix), ranks[word]))
        data.extend(suffix)
        previous = encoded
    offsets.append(len(data))
    blocks = (len(words) + BLOCK_SIZE - 1) // BLOCK_SIZE
    if len(offsets) != blocks + 1:
        raise ValueError("BLOCK_OFFSETS")
    data_offset = HEADER_BYTES + 4 * len(offsets)
    blob = bytearray(MAGIC)
    blob.extend(struct.pack("<IIII", BLOCK_SIZE, len(words), blocks, data_offset))
    blob.extend(struct.pack("<" + "I" * len(offsets), *offsets))
    blob.extend(data)
    blob.extend(hashlib.sha256(blob).digest())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(blob)
    result = {
        "schemaVersion": 1, "format": "RUNERAR1", "blockSize": BLOCK_SIZE,
        "words": len(words), "bytes": len(blob), "sha256": sha256(output),
        "sourceManifestSha256": sha256(source / "manifest.json"),
        "sourceWordsSha256": sha256(words_path), "sourceCountsSha256": sha256(counts_path),
        "scriptSha256": sha256(Path(__file__)),
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(pack(args.source, args.output, args.receipt), sort_keys=True))


if __name__ == "__main__":
    main()
