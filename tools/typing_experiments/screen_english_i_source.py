"""Describe standalone I/i positions in the disclosed CC0 source, without labels."""
import bz2
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'tools/typing_experiments/public_sources/tatoeba-en-cc0-20261024/eng_sentences_CC0.tsv.bz2'
SHA256 = 'a144a0c52f8be13bee7cc30eb109eb5836803f22128a8ef8376c1ca5c6c5cf8a'
TOKEN = re.compile(r'(?<!\w)[Ii](?!\w)')


def category(text, end):
    if end == len(text):
        return 'end'
    next_char = text[end]
    if next_char in "'’":
        return 'apostrophe'
    if next_char == '.':
        return 'period'
    if next_char.isspace():
        return 'space'
    if next_char in ',!?;:':
        return 'other_admitted_punctuation'
    return 'other'


def screen(data):
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise ValueError('EN_I_SOURCE_DIGEST')
    counts = Counter()
    ids = set()
    for line in bz2.decompress(data).decode('utf-8').splitlines():
        fields = line.split('\t')
        if len(fields) != 4 or fields[1] != 'eng' or not fields[0].isascii() or not fields[0].isdecimal() or int(fields[0]) <= 0:
            raise ValueError('EN_I_SOURCE_ROW')
        identity = int(fields[0])
        if identity in ids or not fields[2].strip():
            raise ValueError('EN_I_SOURCE_ROW')
        ids.add(identity)
        counts['source_rows'] += 1
        for match in TOKEN.finditer(fields[2]):
            kind = 'upper' if match.group() == 'I' else 'lower'
            boundary = category(fields[2], match.end())
            counts[kind + '_' + boundary] += 1
            if match.start() > 0 and fields[2][match.start() - 1] in "'’":
                counts[kind + '_preceded_by_apostrophe'] += 1
                if boundary in ('space', 'other_admitted_punctuation'):
                    counts[kind + '_preceded_by_apostrophe_admitted_boundary'] += 1
    if not ids:
        raise ValueError('EN_I_SOURCE_EMPTY')
    return dict(sorted(counts.items()))


if __name__ == '__main__':
    print(json.dumps(screen(SOURCE.read_bytes()), sort_keys=True, indent=2))
