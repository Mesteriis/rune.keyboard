"""Restore the historical Russian CC0 sentence split and train-only counts."""
import argparse
import bz2
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from import_tatoeba_history import CC0_LOCK_SHA, CC0_SPLIT_SHA, ROOT


SOURCE = ROOT / 'tools/typing_experiments/public_sources/tatoeba-ru-cc0-20261024'
WORDS = re.compile('[а-яёА-ЯЁ]+')
SEED = 'rune-tatoeba-cc0-20261026:'
PARTS = ('train',) * 8 + ('calibration', 'holdout')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def jsonl(rows):
    return ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows).encode()


def restore(source=SOURCE):
    lock_bytes = (source / 'tatoeba-source-lock.json').read_bytes()
    if digest(lock_bytes) != CC0_LOCK_SHA:
        raise ValueError('HISTORICAL_CC0_LOCK')
    lock = json.loads(lock_bytes)
    archived = (source / 'rus_sentences_CC0.tsv.bz2').read_bytes()
    if digest(archived) != lock['compressedSha256']:
        raise ValueError('HISTORICAL_CC0_COMPRESSED')
    decoded = bz2.decompress(archived)
    if digest(decoded) != lock['decodedSha256']:
        raise ValueError('HISTORICAL_CC0_DECODED')

    seen = set()
    splits, occurrences, sentences = Counter(), Counter(), Counter()
    split_rows = []
    for line in decoded.decode('utf-8').splitlines():
        identity, language, text, modified = line.split('\t')
        if language != 'rus':
            raise ValueError('HISTORICAL_CC0_LANGUAGE')
        text = unicodedata.normalize('NFC', text)
        normalized = ' '.join(text.casefold().split())
        if normalized in seen:
            continue
        seen.add(normalized)
        bucket = int(digest((SEED + normalized).encode())[:8], 16) % 10
        split = PARTS[bucket]
        splits[split] += 1
        split_rows.append(dict(id=identity, text=text, modified=modified, split=split,
                               normalizedSha256=digest(normalized.encode())))
        if split != 'train':
            continue
        words = list(WORDS.finditer(text))
        pairs = []
        for left, right in zip(words, words[1:]):
            previous, word = left.group().casefold(), right.group().casefold()
            if text[left.end():right.start()].isspace() and 1 <= len(previous) <= 20 and 3 <= len(word) <= 20:
                pairs.append((previous, word))
        occurrences.update(pairs)
        sentences.update(set(pairs))

    rows = jsonl(split_rows)
    counts = jsonl([*pair, occurrences[pair], sentences[pair]] for pair in sorted(occurrences))
    if (splits != lock['splitCounts'] or digest(rows) != CC0_SPLIT_SHA
            or digest(rows) != lock['sentenceSplitSha256'] or digest(counts) != lock['countsSha256']):
        raise ValueError('HISTORICAL_CC0_OUTPUT')
    return {'tatoeba-sentence-splits.jsonl': rows, 'tatoeba-train-counts.jsonl': counts}, dict(splits)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    output = parser.parse_args().output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'):
        raise ValueError('HISTORICAL_CC0_OUTPUT_PATH')
    files, splits = restore()
    output.mkdir(parents=True, mode=0o700)
    for name, payload in files.items():
        (output / name).write_bytes(payload)
    print(json.dumps(dict(splits=splits, sha256={name: digest(payload) for name, payload in files.items()})))


if __name__ == '__main__':
    main()
