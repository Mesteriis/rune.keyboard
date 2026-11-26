"""Aggregate-only screen of the pinned public RuLexNorm source, not a holdout.

The source contains real social-media comments. Do not write text, token
fingerprints or identifiers to the report. An unchanged annotation is not proof
of correct spelling, natural chat representativeness or independent provenance.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

SOURCE_REVISION = '59a8ebc3d314fafe25f918f50e5048f8ac00bed8'
SOURCE_SHA256 = '896a0915301cdc0ccd208550f71f8dd4dd4d15f9b4ecb0f2dd55744eba7f6565'
SOURCE_GIT_BLOB = 'cbe58698805229ed0b7901631fdccc53020094de'
SOURCE_BYTES = 1699640
CYRILLIC = re.compile(r'[А-Яа-яЁё]+\Z')
LOWER_WORD = re.compile(r'[а-яё]{2,20}\Z')


def verify_source(raw):
    if (not isinstance(raw, bytes) or len(raw) != SOURCE_BYTES or
            hashlib.sha256(raw).hexdigest() != SOURCE_SHA256 or
            hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() != SOURCE_GIT_BLOB):
        raise ValueError('RULEXNORM_SOURCE_IDENTITY')


def screen(raw):
    """Summarize group and token shapes; raw content never leaves this function."""
    text = raw.decode('utf-8').replace('\r\n', '\n')
    groups = [group for group in re.split(r'\n\s*\n', text) if group.strip()]
    stats = Counter(groups=len(groups))
    strict = set()
    column_counts = Counter()
    for group in groups:
        rows = [line.split('\t') for line in group.splitlines()]
        column_counts.update(len(row) for row in rows)
        stats['lines'] += len(rows)
        if any(len(row) != 2 for row in rows):
            stats['excludedMalformedGroups'] += 1
            continue
        unchanged = all(original == normalized for original, normalized in rows)
        if unchanged:
            stats['unchangedGroups'] += 1
            words = sum(bool(LOWER_WORD.fullmatch(original)) for original, _ in rows)
            stats['unchangedGroupsLowercaseWords'] += words
            stats['unchangedGroupsWithLowercaseWord'] += bool(words)
            stats['unchangedGroupsTwoToSixTokens'] += 2 <= len(rows) <= 6
            if 2 <= len(rows) <= 6 and all(CYRILLIC.fullmatch(original) for original, _ in rows):
                stats['strictShortOccurrences'] += 1
                strict.add(tuple(original.casefold() for original, _ in rows))
        for index, (original, normalized) in enumerate(rows):
            if LOWER_WORD.fullmatch(original) and original == normalized:
                stats['unchangedLowercaseWords'] += 1
                stats['unchangedLowercaseWordsWithPrecedingToken'] += index > 0
                stats['unchangedLowercaseWordsInUnchangedGroups'] += unchanged
    stats['strictShortDistinctCasefolded'] = len(strict)
    # Stable zeros avoid confusing absent categories with missing measurements.
    for key in ('excludedMalformedGroups', 'unchangedGroups', 'unchangedGroupsLowercaseWords',
                'unchangedGroupsWithLowercaseWord', 'unchangedGroupsTwoToSixTokens',
                'strictShortOccurrences', 'unchangedLowercaseWords',
                'unchangedLowercaseWordsWithPrecedingToken', 'unchangedLowercaseWordsInUnchangedGroups'):
        stats.setdefault(key, 0)
    return {'counts': dict(sorted(stats.items())),
            'columnCounts': {str(k): v for k, v in sorted(column_counts.items())}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    raw = args.source.read_bytes()
    verify_source(raw)
    result = screen(raw)
    if args.source.read_bytes() != raw:
        raise ValueError('RULEXNORM_SOURCE_DRIFT')
    print(json.dumps({'revision': SOURCE_REVISION, 'sourceSha256': SOURCE_SHA256,
                      'independentQualification': False, **result}, sort_keys=True))


if __name__ == '__main__':
    main()
