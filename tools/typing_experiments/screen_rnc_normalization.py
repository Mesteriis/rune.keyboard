"""Measure short-phrase and orthographic coverage without retaining source text."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

from chat_corpus import TOKEN, variants

REVISION = '8fc9c1665e17a8d6e0267000055aba43f19f8a48'
SOURCE_SHA256 = 'fe2d977dfc95a0dbaf1b4015c02d2c6d4726b68400a00e5b4b8357cca2264461'
SOURCE_BYTES = 764416
URL = f'https://huggingface.co/datasets/ruscorpora/normalization/resolve/{REVISION}/data.json'


def verify_source(raw):
    if len(raw) != SOURCE_BYTES or hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError('RNC_NORMALIZATION_SOURCE_IDENTITY')


def short_cyrillic(words):
    return 2 <= len(words) <= 6 and all(TOKEN.fullmatch(word) for word in words)


def screen(raw):
    rows = json.loads(raw)
    if not isinstance(rows, list):
        raise ValueError('RNC_NORMALIZATION_DATASET')
    counts = dict.fromkeys((
        'rows', 'unchangedRows', 'shortCyrillicRows', 'shortCyrillicUnchangedRows',
        'shortCyrillicUnchangedAfterCasefoldRows', 'strictLowercaseUnchangedRows',
        'oneChangedToken', 'oneChangedFinalToken', 'exactGeneratorMatches',
        'exactGeneratorFinalMatches', 'yoOnly',
    ), 0)
    exact, casefolded = set(), set()
    operations = Counter()
    for pair in rows:
        if (not isinstance(pair, list) or len(pair) != 2 or
                any(not isinstance(side, list) or any(not isinstance(token, str) or not token for token in side)
                    for side in pair) or not 1 <= len(pair[0]) == len(pair[1]) <= 51):
            raise ValueError('RNC_NORMALIZATION_PAIR')
        source, normalized = pair
        counts['rows'] += 1
        unchanged = source == normalized
        counts['unchangedRows'] += unchanged
        typed, expected = ([word.casefold() for word in words] for words in pair)
        if not short_cyrillic(typed):
            continue
        counts['shortCyrillicRows'] += 1
        if unchanged:
            counts['shortCyrillicUnchangedRows'] += 1
            counts['strictLowercaseUnchangedRows'] += source == typed
            exact.add(tuple(source))
        if typed == expected:
            counts['shortCyrillicUnchangedAfterCasefoldRows'] += 1
            casefolded.add(tuple(typed))
        if not short_cyrillic(expected):
            continue
        edits = [(original, corrected) for original, corrected in zip(typed, expected, strict=True)
                 if original != corrected]
        if len(edits) != 1:
            continue
        (original, corrected), = edits
        final = typed[-1] != expected[-1]
        matching = {kind for kind, generated in variants(corrected) if generated == original}
        counts['oneChangedToken'] += 1
        counts['oneChangedFinalToken'] += final
        counts['exactGeneratorMatches'] += bool(matching)
        counts['exactGeneratorFinalMatches'] += final and bool(matching)
        counts['yoOnly'] += original.replace('ё', 'е') == corrected.replace('ё', 'е')
        operations.update(matching)
    counts['distinctStrictUnchangedPhrases'] = len(exact)
    counts['distinctCasefoldUnchangedPhrases'] = len(casefolded)
    return {'counts': counts, 'generatedKinds': dict(sorted(operations.items()))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='Local copy of the pinned JSON release')
    args = parser.parse_args()
    if args.source is None:
        with urlopen(URL, timeout=20) as response:
            raw = response.read(SOURCE_BYTES + 1)
    else:
        with args.source.open('rb') as stream:
            raw = stream.read(SOURCE_BYTES + 1)
    verify_source(raw)
    result = screen(raw)
    print(json.dumps({'revision': REVISION, 'sourceSha256': SOURCE_SHA256, 'bytes': SOURCE_BYTES,
                      'independentQualification': False, **result}, sort_keys=True))


if __name__ == '__main__':
    main()
