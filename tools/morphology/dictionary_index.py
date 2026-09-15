"""Read the public RUNEMRF1 asset with bounded mmap lookups; retains no queried words."""
from __future__ import annotations

import hashlib
import mmap
from pathlib import Path
import struct
import unicodedata

from export_dictionary import BLOCK_SIZE, MAGIC, accepted


class DictionaryIndex:
    def __init__(self, path: Path):
        self._path = path
        self._file = None
        self._data = None

    def __enter__(self):
        try:
            self._file = self._path.open("rb")
            size = self._file.seek(0, 2)
            if not 64 <= size <= 96 * 1024 * 1024:
                raise ValueError("INVALID_DICTIONARY_INDEX")
            self._data = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_READ)
            data = self._data
            digest = hashlib.sha256()
            for offset in range(0, size - 32, 65536):
                digest.update(data[offset:min(offset + 65536, size - 32)])
            if digest.digest() != data[-32:] or data[:8] != MAGIC:
                raise ValueError("INVALID_DICTIONARY_INDEX")
            width, self._count, self._blocks, self._start = struct.unpack_from("<IIII", data, 8)
            if (width != BLOCK_SIZE or not 1 <= self._count <= 6_000_000 or
                    self._blocks != (self._count + BLOCK_SIZE - 1) // BLOCK_SIZE or
                    self._start != 24 + 4 * (self._blocks + 1) or self._start >= size - 32):
                raise ValueError("INVALID_DICTIONARY_INDEX")
            last = -1
            for block in range(self._blocks + 1):
                offset = self._offset(block)
                if not last < offset <= size - 32 - self._start or (block == 0 and offset != 0):
                    raise ValueError("INVALID_DICTIONARY_INDEX")
                if block < self._blocks and data[self._start + offset] != 0:
                    raise ValueError("INVALID_DICTIONARY_INDEX")
                last = offset
            if last != size - 32 - self._start:
                raise ValueError("INVALID_DICTIONARY_INDEX")
            return self
        except Exception:
            self.__exit__(None, None, None)
            raise ValueError("INVALID_DICTIONARY_INDEX") from None

    def __exit__(self, *_):
        if self._data is not None:
            self._data.close()
            self._data = None
        if self._file is not None:
            self._file.close()
            self._file = None

    def _offset(self, block):
        return struct.unpack_from("<I", self._data, 24 + 4 * block)[0]

    def _read(self, offset, previous):
        prefix, suffix, lemma = struct.unpack_from("<BBI", self._data, offset)
        if prefix > len(previous) or not 0 < suffix <= 64 - prefix or lemma >= 2**31:
            raise ValueError("INVALID_DICTIONARY_INDEX")
        word = previous[:prefix] + self._data[offset + 6:offset + 6 + suffix]
        return word, offset + 6 + suffix, lemma

    def contains(self, word: str) -> bool:
        if self._data is None:
            raise ValueError("DICTIONARY_INDEX_CLOSED")
        word = unicodedata.normalize("NFC", word.lower())
        if not accepted(word):
            return False
        query = word.encode("utf-8")
        low, high, selected = 0, self._blocks - 1, -1
        while low <= high:
            middle = (low + high) // 2
            first, _, _ = self._read(self._start + self._offset(middle), b"")
            if first <= query:
                selected, low = middle, middle + 1
            else:
                high = middle - 1
        if selected < 0:
            return False
        offset = self._start + self._offset(selected)
        end = self._start + self._offset(selected + 1)
        previous = b""
        for _ in range(min(BLOCK_SIZE, self._count - selected * BLOCK_SIZE)):
            value, offset, _ = self._read(offset, previous)
            if offset > end:
                raise ValueError("INVALID_DICTIONARY_INDEX")
            if value == query:
                return True
            if value > query:
                return False
            previous = value
        if offset != end:
            raise ValueError("INVALID_DICTIONARY_INDEX")
        return False
