#!/usr/bin/env python3
"""Screen lowercase corpus evidence against frozen canonical-case keys (no policy change)."""
import argparse
import bz2
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import struct
import unicodedata

from audit_case_homograph_source import SOURCE_SHA
from holdout_ledger import keys_for, load_ledger
from chat_case_review import PURPOSE, LABELS

CASE_SHA = '845144afb06ae7881f0db2f577f340694b8c7dfa5fee9685563ec4852939c81b'
WORD = re.compile(r'(?<!\w)[а-яё]+(?!\w)', re.IGNORECASE)


def parse_case(data):
    if len(data) < 12 or data[:4] != b'RNC1':
        raise ValueError('CASE_ASSET_HEADER')
    count = struct.unpack_from('>I', data, 4)[0]
    start = 8 + 4 * (count + 1)
    if count > 100_000 or start > len(data):
        raise ValueError('CASE_ASSET_OFFSETS')
    offsets = struct.unpack_from(f'>{count + 1}I', data, 8)
    if offsets[0] != 0 or offsets[-1] != len(data) - start or any(a > b for a, b in zip(offsets, offsets[1:])):
        raise ValueError('CASE_ASSET_OFFSETS')
    keys = set()
    previous = b''
    for first, last in zip(offsets, offsets[1:]):
        record = data[start + first:start + last]
        if len(record) < 3:
            raise ValueError('CASE_ASSET_RECORD')
        flag, key_len, value_len = record[:3]
        if flag not in (0, 1) or key_len == 0 or value_len == 0 or len(record) != 3 + key_len + value_len:
            raise ValueError('CASE_ASSET_RECORD')
        key_bytes = record[3:3 + key_len]
        if key_bytes <= previous:
            raise ValueError('CASE_ASSET_ORDER')
        previous = key_bytes
        key = key_bytes.decode('utf-8')
        value = record[3 + key_len:].decode('utf-8')
        if unicodedata.normalize('NFC', key) != key or key.lower() != key or value.lower() != key:
            raise ValueError('CASE_ASSET_TEXT')
        if flag:
            keys.add(key)
    return keys


def scan(lines, keys, blocked):
    seen = set()
    lower = defaultdict(set)
    title = defaultdict(set)
    source_rows = 0
    for line in lines:
        row = line.rstrip('\n').split('\t')
        if len(row) != 4 or row[1] != 'rus' or not row[0].isascii() or not row[0].isdecimal():
            raise ValueError('CASE_SCREEN_SOURCE_ROW')
        if row[0] in seen:
            raise ValueError('CASE_SCREEN_DUPLICATE')
        seen.add(row[0])
        matches = [m for m in WORD.finditer(row[2])
                   if m.group().lower() in keys and row[2][:m.start()].strip()]
        if not matches:
            continue
        identity = {'sourceRepository': 'tatoeba', 'article': 'tatoeba:' + row[0], 'language': 'ru'}
        if keys_for([identity], 'article') - blocked:
            continue
        source_rows += 1
        for match in matches:
            value = match.group()
            key = value.lower()
            if value == key:
                lower[key].add(row[0])
            elif value.istitle():
                title[key].add(row[0])
    return lower, title, source_rows


def summarize(keys, lower, title, rows, review):
    if review.get('schema') != 1 or review.get('purpose') != PURPOSE:
        raise ValueError('CASE_SCREEN_REVIEW')
    cases = review.get('cases')
    if not isinstance(cases, list) or not cases or len({c['id'] for c in cases}) != len(cases):
        raise ValueError('CASE_SCREEN_REVIEW')
    groups = Counter()
    for case in cases:
        if set(case) != {'id', 'typed', 'baseline', 'label'} or case['label'] not in LABELS or case['typed'] not in keys:
            raise ValueError('CASE_SCREEN_REVIEW')
        groups[(case['label'], bool(lower.get(case['typed'])), bool(title.get(case['typed'])))] += 1
    return {'eligibleCaseKeys': len(keys), 'excludedSourceArticlesWithMatches': rows,
            'keysWithLowerEvidence': len(lower), 'keysWithBothCases': len(lower.keys() & title.keys()),
            'lowercaseEvidence': [{'token': key, 'lowerArticles': len(lower[key]), 'titleArticles': len(title.get(key, set()))}
                                  for key in sorted(lower)],
            'reviewCases': [{'label': label, 'lowerEvidence': lo, 'titleEvidence': hi, 'occurrences': count}
                            for (label, lo, hi), count in sorted(groups.items())]}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'case', 'ledger', 'review', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    args = p.parse_args()
    paths = {'source': args.source, 'case': args.case, 'ledger': args.ledger, 'review': args.review,
             'tool': Path(__file__), 'ledgerTool': Path(__file__).with_name('holdout_ledger.py'),
             'identityTool': Path(__file__).with_name('source_identities.py'),
             'splitTool': Path(__file__).with_name('conversation_split_checks.py')}
    hashes = {name: digest(path) for name, path in paths.items()}
    if hashes['source'] != SOURCE_SHA or hashes['case'] != CASE_SHA:
        raise ValueError('CASE_SCREEN_INPUT_IDENTITY')
    ledger = load_ledger(args.ledger)
    blocked = {key for entry in ledger['entries'] for key in entry['keys'].get('article', [])}
    keys = parse_case(args.case.read_bytes())
    with bz2.open(args.source, 'rt', encoding='utf-8', newline='') as stream:
        lower, title, rows = scan(stream, keys, blocked)
    result = summarize(keys, lower, title, rows, json.loads(args.review.read_text()))
    if any(digest(path) != hashes[name] for name, path in paths.items()):
        raise ValueError('CASE_SCREEN_INPUT_DRIFT')
    report = {'schema': 1, 'purpose': 'DISCLOSED_LOWERCASE_EVIDENCE_SCREEN_NOT_QUALIFICATION',
              'independentQualification': False, 'bindings': hashes, 'result': result}
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write('\n')
    print(json.dumps({k: result[k] for k in ('eligibleCaseKeys', 'keysWithLowerEvidence', 'reviewCases')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
