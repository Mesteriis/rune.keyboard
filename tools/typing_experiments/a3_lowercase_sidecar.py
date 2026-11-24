#!/usr/bin/env python3
"""Extract observed lowercase short forms from the rare-word source shards.

Development artifact only: presence is not proof that a form is not a name.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import unicodedata

import rare_word_supplement as rare

WORD = re.compile(r'(?<![\w-])([а-яё]{3,4})(?![\w-])')


def lowercase_forms(text):
    text = unicodedata.normalize('NFC', text or '')
    def mark(index):
        return 0 <= index < len(text) and unicodedata.category(text[index]).startswith('M')
    return [m.group(1) for m in WORD.finditer(text) if not mark(m.start() - 1) and not mark(m.end())]


def extract(paths, output):
    import pyarrow
    import pyarrow.parquet as parquet
    root = output.resolve()
    if root.exists() or not root.is_relative_to(rare.ROOT / 'build'): raise ValueError('FRESH_BUILD_OUTPUT_REQUIRED')
    if len(paths) != len(rare.PINNED_SOURCES): raise ValueError('PINNED_SOURCE_SET_REQUIRED')
    bindings = {}
    for path in paths:
        path = path.resolve(strict=True)
        digest = rare.file_hash(path)
        if path.name in bindings or rare.PINNED_SOURCES.get(path.name) != digest:
            raise ValueError('PUBLIC_PARQUET_IDENTITY')
        bindings[path.name] = digest
    if set(bindings) != set(rare.PINNED_SOURCES): raise ValueError('PINNED_SOURCE_SET_REQUIRED')
    counts = Counter(); documents = 0
    for path in sorted(paths, key=lambda p: p.name):
        for batch in parquet.ParquetFile(path).iter_batches(batch_size=128, columns=['text']):
            for text in batch.column(0).to_pylist():
                counts.update(set(lowercase_forms(text)))
                documents += 1
    for path in paths:
        if rare.file_hash(path) != bindings[path.name]: raise ValueError('PUBLIC_PARQUET_DRIFT')
    root.mkdir(parents=True, mode=0o700)
    target = root / 'words.tsv'
    with target.open('x', encoding='utf-8') as stream:
        for word in sorted(counts): stream.write(f'{word}\t{counts[word]}\n')
    receipt = {'purpose': 'disclosed_lowercase_source_screen_not_qualification', 'shards': bindings,
        'source': 'Wikimedia Wikipedia 20231101.ru', 'documents': documents, 'uniqueWords': len(counts),
        'wordsSha256': rare.file_hash(target), 'extractorSha256': rare.file_hash(Path(__file__)),
        'pyarrowVersion': pyarrow.__version__, 'minimumDocumentCount': 1,
        'warning': 'lowercase occurrence does not exclude names, false labels, or source leakage'}
    (root / 'receipt.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'documents': documents, 'uniqueWords': len(counts), 'wordsSha256': receipt['wordsSha256']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shard', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); extract(args.shard, args.output)
