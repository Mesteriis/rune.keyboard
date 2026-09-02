"""Pinned historical text evidence. No executable artifact is distributed or loaded."""
from __future__ import annotations
import base64
import gzip
import hashlib
import io
import json
import re
from pathlib import Path

ORIGINAL_MANIFEST_SHA = '45c2c6c91e69ccb78c042318d481c04b1a16589f0d41ae3f06057fc325648170'
ARCHIVE_SHA = 'dfbd2f1dfdaf84155ab29c12efbaa1d54b81861944063c57842e1825eef87d82'
ARCHIVE_RAW_BYTES = 17_228_152
OMITTED = {'bin/qualification.jar', 'bin/unit_oracle'}

class Failure(ValueError):
    """Public diagnostics carry only a static code, never exception payloads."""

def require(condition: bool, code: str) -> None:
    if not condition:
        raise Failure(code)

def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def sha(path: Path) -> str:
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1_048_576), b''):
            result.update(block)
    return result.hexdigest()

def unique_object(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        require(key not in result, 'DUPLICATE_JSON_KEY')
        result[key] = value
    return result

def read_json(raw: bytes) -> dict | list:
    return json.loads(raw, object_pairs_hook=unique_object)

def load(package: Path) -> dict[str, bytes]:
    manifest_bytes = (package / 'evidence/original-manifest.json').read_bytes()
    require(digest(manifest_bytes) == ORIGINAL_MANIFEST_SHA, 'HISTORICAL_MANIFEST_IDENTITY')
    manifest = read_json(manifest_bytes)
    encoded = (package / 'evidence/records.json.gz.b64').read_bytes()
    require(len(encoded) <= 2_000_000, 'ARCHIVE_ENCODED_LIMIT')
    packed = base64.b64decode(b''.join(encoded.splitlines()), validate=True)
    require(digest(packed) == ARCHIVE_SHA, 'ARCHIVE_IDENTITY')
    with gzip.GzipFile(fileobj=io.BytesIO(packed)) as stream:
        raw = stream.read(ARCHIVE_RAW_BYTES + 1)
    require(len(raw) == ARCHIVE_RAW_BYTES, 'ARCHIVE_LENGTH')
    values = read_json(raw)
    items = manifest['files']
    require(len(items) == 43 and len({r['path'] for r in items}) == 43, 'HISTORICAL_ARTIFACT_SET')
    expected = {r['path'] for r in items} - OMITTED
    require(set(values) == expected and len(expected) == 41, 'HISTORICAL_TEXT_SET')
    records = {}
    for item in items:
        name = item['path']
        if name in OMITTED:
            continue
        require(isinstance(values[name], str), 'HISTORICAL_TEXT_TYPE')
        data = values[name].encode('utf-8')
        require(len(data) == item['bytes'] and digest(data) == item['sha256'], 'HISTORICAL_TEXT_IDENTITY')
        records[name] = data
    return records

def validate_numeric(raw: bytes, inputs: list[dict]) -> list[list[int]]:
    """Strict payload-free envelope before the original semantic comparison module."""
    require(0 < len(raw) <= 8_000_000, 'RECORD_BYTE_LIMIT')
    lines = raw.decode('ascii').splitlines()
    require(len(lines) <= 100_000 and bool(lines), 'RECORD_ROW_LIMIT')
    widths = {0: 5, 1: 13, 2: 17, 3: 6, 4: 7, 5: 9, 6: 3}
    rows = []
    for line in lines:
        require(len(line) <= 512, 'RECORD_LINE_LIMIT')
        cells = line.split('\t')
        require(3 <= len(cells) <= 17 and all(re.fullmatch(r'-?(?:0|[1-9][0-9]{0,9})', x) for x in cells), 'RECORD_NUMERIC')
        row = [int(x) for x in cells]
        require(all(-2_147_483_648 <= x <= 2_147_483_647 for x in row), 'RECORD_INT_RANGE')
        require(row[0] == 1 and row[1] in widths and len(row) == widths[row[1]], 'RECORD_SCHEMA')
        rows.append(row)
    require(rows[:3] == [[1,0,0,121255,272385],[1,0,1,1436553,2255866],[1,0,2,668267,1250979]], 'RECORD_LOADS')
    require(rows[-1] == [1,6,len(inputs)] and sum(r[1] == 6 for r in rows) == 1, 'RECORD_END')
    require(sum(r[1] == 0 for r in rows) == 3, 'RECORD_LOAD_COUNT')
    requests = [r for r in rows if r[1] == 1]
    require([r[2] for r in requests] == list(range(len(inputs))), 'RECORD_REQUEST_SET')
    current = -1
    for row in rows[3:-1]:
        if row[1] == 1:
            current = row[2]
            item = inputs[current]
            require(row[3:5] == [item['group'], item['active']], 'RECORD_INPUT_ASSIGNMENT')
            require(row[5] in range(8) and row[6] in (0,1) and row[7] in (0,1) and row[8] == 1, 'RECORD_FLAGS')
            require(0 <= row[9] <= 8192 and 0 <= row[10] <= 64 and 0 <= row[12] <= 7, 'RECORD_CAPS')
            require(row[7] == int(row[5] != 0 or row[6] == 1 or row[11] >= 0), 'RECORD_VETO')
        else:
            require(row[1] in (2,3,4,5) and row[2] == current and current >= 0, 'RECORD_EVENT_OWNER')
    return rows
