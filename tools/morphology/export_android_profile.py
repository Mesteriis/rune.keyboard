#!/usr/bin/env python3
"""Export a local style model as dictionary-validated manual Android phrase hints.

This command performs no network calls. The output is private typing data: keep
it out of source control and APK assets. It contains no correction approvals,
message identifiers, source hashes, raw messages, or unigram spelling claims.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import unicodedata

from telegram_style import ImportFailure, MAX_FILE_BYTES, StyleModel

PROFILE_HEADER = 'RUNE_PERSONAL_PHRASES_V1'
MAX_PROFILE_BYTES = 1024 * 1024
MAX_PHRASES = 1024
MAX_WORD_CHARS = 48
MAX_COUNT = 255
MIN_SUPPORT = 3
LANGUAGES = {'en': 'ENGLISH', 'ru': 'RUSSIAN', 'es': 'SPANISH'}


def _valid_word(word: str) -> bool:
    return (0 < len(word) <= MAX_WORD_CHARS and word == unicodedata.normalize('NFC', word).lower()
            and all(unicodedata.category(char).startswith('L') for char in word))


def export_profile(payload: dict, language: str, dictionary_contains, *, min_support: int = MIN_SUPPORT) -> bytes:
    """Validated frequency changes manual phrase ordering only; dictionary membership is mandatory."""
    StyleModel(payload)
    if language not in LANGUAGES or type(min_support) is not int or min_support < MIN_SUPPORT:
        raise ImportFailure('INVALID_EXPORT_OPTIONS')
    rows = {}
    for size, field in ((2, 'bigrams'), (3, 'trigrams')):
        for gram, count in payload[field].items():
            words = gram.split(' ')
            if count < min_support or not all(_valid_word(word) and dictionary_contains(word) for word in words):
                continue
            # A trigram supports both a two-word context and a two-word continuation.
            for split in range(1, size):
                key = (' '.join(words[:split]), ' '.join(words[split:]))
                rows[key] = max(rows.get(key, 0), min(count, MAX_COUNT))
    selected = sorted(rows.items(), key=lambda row: (-row[1], row[0]))[:MAX_PHRASES]
    lines = [PROFILE_HEADER] + [f'{LANGUAGES[language]}\t{prefix}\t{target}\t{count}'
                                for (prefix, target), count in selected]
    result = ('\n'.join(lines) + '\n').encode('utf-8')
    if len(result) > MAX_PROFILE_BYTES:
        raise ImportFailure('PROFILE_LIMIT_EXCEEDED')
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--dictionary', type=Path, required=True,
                        help='Public morphology .morph index produced by export_dictionary.py')
    parser.add_argument('--language', choices=['ru'], required=True,
                        help='The current public morphology index is Russian only')
    parser.add_argument('--min-support', type=int, default=MIN_SUPPORT)
    parser.add_argument('--output', type=Path, required=True, help='New private output file; existing files are refused')
    args = parser.parse_args(argv)
    try:
        with args.model.open('rb') as source:
            raw = source.read(MAX_FILE_BYTES + 1)
        if len(raw) > MAX_FILE_BYTES:
            raise ImportFailure('MODEL_LIMIT_EXCEEDED')
        payload = json.loads(raw)
        from dictionary_index import DictionaryIndex
        with DictionaryIndex(args.dictionary) as dictionary:
            result = export_profile(payload, args.language, dictionary.contains, min_support=args.min_support)
        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, 'wb') as output:
                output.write(result)
                output.flush()
                os.fsync(output.fileno())
        except BaseException:
            args.output.unlink(missing_ok=True)
            raise
        print(json.dumps({'schemaVersion': 1, 'phraseEntries': result.count(b'\n') - 1, 'bytes': len(result)}, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, ImportError):
        print('ANDROID_PROFILE_EXPORT_FAILED', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
