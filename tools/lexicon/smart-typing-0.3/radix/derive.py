"""Offline radix-trie experiment. Preserve every terminal ordinal; never read frequency data."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import struct

HEADER = struct.Struct("<4sIIIII")
RECORD = struct.Struct("<IIIIBBBB")
MANIFEST_SHA = "7ce207ab7d05b8800a1d8921f6e55fe81f429f8158bf8ebcebf581cbee7255f0"


def require(condition, code):
    if not condition:
        raise ValueError(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def derive(trie, lengths, word_sha):
    require(len(trie) >= 16 and len(lengths) >= 16, "HEADER")
    magic, words, nodes, stride = struct.unpack_from("<4sIII", trie)
    require(magic == b"RTR1" and words > 0 and nodes > 1 and stride == 16 and
            len(trie) == 16 + 16 * nodes, "TRIE_HEADER")
    require(struct.unpack_from("<4sIII", lengths) == (b"LEN1", 1, nodes, 0) and
            len(lengths) == 16 + 2 * nodes, "LENGTH_HEADER")

    def source(node):
        require(0 <= node < nodes, "NODE_RANGE")
        cp, child, sibling, terminal = struct.unpack_from("<IIII", trie, 16 + 16 * node)
        require(cp <= 0x10ffff and not 0xd800 <= cp <= 0xdfff and
                child < nodes and sibling < nodes and terminal <= words, "NODE_FIELDS")
        return cp, child, sibling, terminal

    root = source(0)
    require(root[0] == root[2] == root[3] == 0, "ROOT")
    visited = bytearray(nodes)
    visited[0] = 1
    records = bytearray(RECORD.size)
    labels = bytearray()
    path = []
    ordinal = 0
    digest = hashlib.sha256()

    def sibling_list(first):
        first_id = previous_id = 0
        previous_label = -1
        low, high = 33, 0
        while first:
            cp, _, sibling, _ = source(first)
            require(cp > previous_label, "SIBLING_ORDER")
            previous_label = cp
            edge_id, edge_low, edge_high = edge(first)
            if previous_id:
                struct.pack_into("<I", records, previous_id * RECORD.size + 8, edge_id)
            else:
                first_id = edge_id
            previous_id = edge_id
            low, high = min(low, edge_low), max(high, edge_high)
            first = sibling
        return first_id, low, high

    def edge(node):
        nonlocal ordinal
        start_depth = len(path)
        chain = []
        while True:
            require(not visited[node] and len(path) < 32, "CYCLE_OR_DEPTH")
            visited[node] = 1
            cp, child, _, terminal = source(node)
            path.append(cp)
            chain.append(node)
            if terminal or not child or source(child)[2]:
                break
            node = child
        edge_id = len(records) // RECORD.size
        records.extend(bytes(RECORD.size))
        offset = len(labels)
        encoded = "".join(map(chr, path[start_depth:])).encode("utf-8")
        labels.extend(encoded)
        if terminal:
            ordinal += 1
            require(terminal == ordinal, "TERMINAL_ORDER")
            digest.update("".join(map(chr, path)).encode("utf-8") + b"\n")
        low = len(path) if terminal else 33
        high = len(path) if terminal else 0
        child_id, child_low, child_high = sibling_list(child)
        low, high = min(low, child_low), max(high, child_high)
        require(1 <= low <= high <= 32, "EMPTY_BRANCH")
        for original in chain:
            require(tuple(lengths[16 + 2 * original:18 + 2 * original]) == (low, high), "LENGTHS")
        RECORD.pack_into(records, edge_id * RECORD.size, offset, child_id, 0, terminal,
                         len(chain), len(encoded), low, high)
        del path[start_depth:]
        return edge_id, low, high

    first, low, high = sibling_list(root[1])
    require(ordinal == words and all(visited) and digest.hexdigest() == word_sha, "SOURCE_IDENTITY")
    require(tuple(lengths[16:18]) == (low, high), "ROOT_LENGTHS")
    RECORD.pack_into(records, 0, 0, first, 0, 0, 0, 0, low, high)
    output = HEADER.pack(b"RDX1", 1, len(records) // RECORD.size, words, RECORD.size, len(labels)) + records + labels
    validate(output, word_sha)
    return output


def validate(data, word_sha):
    """Independent decode of compressed edges, child topology, word stream and exact length bounds."""
    require(len(data) >= HEADER.size, "RADIX_HEADER")
    magic, version, nodes, words, stride, blob_size = HEADER.unpack_from(data)
    require(magic == b"RDX1" and version == 1 and nodes > 1 and words > 0 and stride == RECORD.size
            and len(data) == HEADER.size + stride * nodes + blob_size, "RADIX_SIZE")
    blob = HEADER.size + stride * nodes
    next_id, next_byte, ordinal = 0, 0, 0
    digest = hashlib.sha256()

    def visit(node, prefix):
        nonlocal next_id, next_byte, ordinal
        require(node == next_id and node < nodes, "RADIX_PREORDER")
        next_id += 1
        offset, child, sibling, terminal, count, size, low, high = RECORD.unpack_from(data, HEADER.size + node * stride)
        require(offset == next_byte and offset + size <= blob_size and child < nodes and sibling < nodes
                and terminal <= words, "RADIX_FIELDS")
        try:
            label = data[blob + offset:blob + offset + size].decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            raise ValueError("RADIX_UTF8") from None
        require(len(label) == count and len(prefix) + count <= 32 and 1 <= low <= high <= 32, "RADIX_LABEL")
        require((node == 0 and count == size == terminal == sibling == 0) or (node > 0 and 1 <= count <= 32), "RADIX_ROOT")
        next_byte += size
        word = prefix + label
        if terminal:
            ordinal += 1
            require(terminal == ordinal, "RADIX_ORDINAL")
            digest.update(word.encode("utf-8") + b"\n")
        actual_low = len(word) if terminal else 33
        actual_high = len(word) if terminal else 0
        previous_label = -1
        children = 0
        while child:
            child, child_low, child_high, first = visit(child, word)
            require(first > previous_label, "RADIX_SIBLINGS")
            previous_label = first
            actual_low, actual_high = min(actual_low, child_low), max(actual_high, child_high)
            children += 1
        require((low, high) == (actual_low, actual_high), "RADIX_LENGTHS")
        require(node == 0 or terminal or children != 1, "RADIX_NOT_COMPRESSED")
        return sibling, low, high, ord(label[0]) if label else -1

    visit(0, "")
    require(next_id == nodes and next_byte == blob_size and ordinal == words and digest.hexdigest() == word_sha,
            "RADIX_IDENTITY")
    return {"words": words, "nodes": nodes, "labelBytes": blob_size, "bytes": len(data), "sha256": sha(data)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package = Path(__file__).resolve().parents[1]
    root = package.parents[2]
    output = args.output.resolve()
    require(output.is_relative_to(root / "build") and not output.exists(), "FRESH_BUILD_OUTPUT")
    manifest = (package / "packed-asset-manifest.json").read_bytes()
    require(sha(manifest) == MANIFEST_SHA, "PINNED_MANIFEST")
    output.mkdir(parents=True)
    report = {"productionIntegrated": False, "queryOrHoldoutExecuted": False, "languages": {}}
    for record in json.loads(manifest):
        lang = {"ENGLISH": "en", "RUSSIAN": "ru", "SPANISH": "es"}[record["language"]]
        parts = {}
        for name, suffix in (("trie", ".trie"), ("lengths", ".trie.lengths")):
            parts[name] = (args.index_dir / (lang + suffix)).read_bytes()
            require(len(parts[name]) == record[name]["bytes"] and sha(parts[name]) == record[name]["sha256"], "PINNED_INPUT")
        result = derive(parts["trie"], parts["lengths"], record["canonical_words_sha256"])
        (output / (lang + ".radix")).write_bytes(result)
        report["languages"][lang] = dict(validate(result, record["canonical_words_sha256"]),
            originalNodes=record["nodes"], originalBytes=sum(len(b) for b in parts.values()),
            canonicalWordsSha256=record["canonical_words_sha256"], frequencyRanksUnchanged=True)
        print(lang, report["languages"][lang], flush=True)
    report["sourceSha256"] = sha(Path(__file__).read_bytes())
    report["inputManifestSha256"] = MANIFEST_SHA
    report["pythonVersion"] = platform.python_version()
    report["format"] = "RDX1/v1, little-endian, 20-byte records, strict UTF-8 labels"
    (output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
