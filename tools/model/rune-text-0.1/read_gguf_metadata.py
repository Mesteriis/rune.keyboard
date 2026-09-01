#!/usr/bin/env python3
import json
import struct
import sys

TYPES = {0: ("B", 1), 1: ("b", 1), 2: ("H", 2), 3: ("h", 2), 4: ("I", 4),
         5: ("i", 4), 6: ("f", 4), 7: ("?", 1), 10: ("Q", 8), 11: ("q", 8), 12: ("d", 8)}

def read_exact(stream, length):
    value = stream.read(length)
    if len(value) != length:
        raise ValueError("truncated GGUF")
    return value

def scalar(stream, type_id):
    fmt, length = TYPES[type_id]
    return struct.unpack("<" + fmt, read_exact(stream, length))[0]

def text(stream):
    length = scalar(stream, 10)
    if length > 16 * 1024 * 1024:
        raise ValueError("unreasonable GGUF string")
    return read_exact(stream, length).decode("utf-8")

def value(stream, type_id):
    if type_id == 8:
        return text(stream)
    if type_id == 9:
        element_type = scalar(stream, 4)
        count = scalar(stream, 10)
        return [value(stream, element_type) for _ in range(count)]
    return scalar(stream, type_id)

with open(sys.argv[1], "rb") as stream:
    if read_exact(stream, 4) != b"GGUF":
        raise ValueError("invalid GGUF magic")
    version = scalar(stream, 4)
    tensor_count = scalar(stream, 10)
    metadata_count = scalar(stream, 10)
    metadata = {}
    for _ in range(metadata_count):
        key = text(stream)
        metadata[key] = value(stream, scalar(stream, 4))

selected = {
    "gguf.version": version,
    "tensor_count": tensor_count,
    "metadata_count": metadata_count,
    "general.architecture": metadata.get("general.architecture"),
    "general.file_type": metadata.get("general.file_type"),
    "general.name": metadata.get("general.name"),
    "general.quantization_version": metadata.get("general.quantization_version"),
}
print(json.dumps(selected, ensure_ascii=False, sort_keys=True, indent=2))
