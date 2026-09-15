"""Reproducible exact Russian membership + conservative lemma-family APK index.

Only iterates pinned dictionary records. No prediction, corpus, or user input is read.
Binary v1 (little endian): magic(8), blockSize/count/blocks/dataOffset(u32 each),
block offsets(u32, relative to data, including terminal offset), front-coded records,
SHA-256(all preceding bytes). Record: prefix/suffix byte lengths(u8), lemma(u32),
UTF-8 suffix. Each block of 32 starts with prefix=0. Lemma 0 means ambiguous.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import re
import struct
import tempfile
import unicodedata

BLOCK_SIZE = 32
MAGIC = b"RUNEMRF1"
WORD = re.compile(r"[а-яё]+(?:-[а-яё]+)*\Z")


def accepted(word: str) -> bool:
    return 1 <= len(word) <= 32 and WORD.fullmatch(word) is not None and unicodedata.normalize("NFC", word) == word


def write_index(records, output: Path) -> dict:
    """Consume sorted unique (word, lemma-id) records with bounded encoding memory."""
    offsets = []
    count = 0
    previous = b""
    with tempfile.TemporaryFile() as body:
        for word, lemma in records:
            encoded = word.encode("utf-8")
            if not accepted(word) or not 0 <= lemma < 2**31:
                raise ValueError("INVALID_DICTIONARY_RECORD")
            if count and encoded <= previous:
                raise ValueError("UNSORTED_DICTIONARY")
            prefix = 0
            if count % BLOCK_SIZE == 0:
                offsets.append(body.tell())
            else:
                while prefix < min(len(previous), len(encoded)) and previous[prefix] == encoded[prefix]:
                    prefix += 1
            suffix = encoded[prefix:]
            body.write(struct.pack("<BBI", prefix, len(suffix), lemma))
            body.write(suffix)
            previous = encoded
            count += 1
        if not count:
            raise ValueError("EMPTY_DICTIONARY")
        offsets.append(body.tell())
        data_offset = 24 + 4 * len(offsets)
        header = MAGIC + struct.pack("<IIII", BLOCK_SIZE, count, len(offsets) - 1, data_offset)
        digest = hashlib.sha256()
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("wb") as target:
            def emit(chunk):
                target.write(chunk)
                digest.update(chunk)
            emit(header)
            emit(struct.pack(f"<{len(offsets)}I", *offsets))
            body.seek(0)
            for chunk in iter(lambda: body.read(65536), b""):
                emit(chunk)
            target.write(digest.digest())
    with output.open("rb") as source:
        sha256 = hashlib.file_digest(source, "sha256").hexdigest()
    return {"words": count, "blocks": len(offsets) - 1, "bytes": output.stat().st_size, "sha256": sha256}


def dictionary_records(dictionary, stats):
    # IDs distinguish normal-form + paradigm families, not semantic homonyms. Multiple
    # families veto automatically; grammatical alternatives within one family are retained.
    families = {}
    for word, rows in itertools.groupby(dictionary.words.iteritems(), key=lambda row: row[0]):
        if not accepted(word):
            continue
        keys = {(dictionary.build_normal_form(para, idx, word), para) for _, (para, idx) in rows}
        if len(keys) != 1:
            stats["ambiguousWords"] += 1
            yield word, 0
        else:
            key = next(iter(keys))
            if key not in families:
                families[key] = len(families) + 1
            yield word, families[key]
    stats["lemmaFamilies"] = len(families)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    from ranker import PymorphyLexicon
    lexicon = PymorphyLexicon()
    receipt = lexicon.receipt()  # Pins versions and installed files before loading public data.
    lexicon._load()
    stats = {"ambiguousWords": 0}
    result = write_index(dictionary_records(lexicon._analyzer.dictionary, stats), args.output)
    if receipt != lexicon.receipt():
        raise ValueError("DICTIONARY_CHANGED")
    manifest = {"schemaVersion": 1, "asset": args.output.name, "format": "RUNEMRF1",
                "blockSize": BLOCK_SIZE, **result, **stats,
                "source": {"name": "OpenCorpora", "url": "https://opencorpora.org/",
                           "version": "0.92", "revision": "417150", "license": "CC-BY-SA-3.0",
                           "licenseUrl": "https://creativecommons.org/licenses/by-sa/3.0/"},
                "transformation": "Exact NFC lowercase Russian dictionary words and hyphenated words, 1-32 scalars; no predictions or е/ё expansion. Lemma family = dictionary normal form and paradigm; multiple families = ambiguous. Front-coded UTF-8 with deterministic IDs.",
                "exporterSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "installedPackages": receipt}
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({**result, **stats}, sort_keys=True))


if __name__ == "__main__":
    main()
