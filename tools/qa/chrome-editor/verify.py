#!/usr/bin/env python3
"""Require native input completion AND independent ordered numeric DOM outcomes."""
import argparse
import json
import re
from pathlib import Path

FIELDS = {'profile', 'length', 'words', 'corrections', 'lastCorrected', 'firstFive',
          'undo', 'sixth', 'literalFive', 'literalBackspace'}


def verify(records, native):
    if not 1 <= len(records) <= 512:
        raise ValueError('DOM_RECEIPT_COUNT')
    profiles = {'ordinary': [], 'no-suggestions': []}
    for value in records:
        if not isinstance(value, dict) or value.keys() != FIELDS or type(value['profile']) is not str or value['profile'] not in profiles:
            raise ValueError('DOM_RECEIPT_FIELDS')
        if any(type(v) is not int or not 0 <= v <= 512 for k, v in value.items() if k != 'profile'):
            raise ValueError('DOM_RECEIPT_NUMBERS')
        if any(value[k] not in (0, 1) for k in FIELDS - {'profile', 'length', 'words', 'corrections'}):
            raise ValueError('DOM_RECEIPT_FLAGS')
        if value['corrections'] > value['words'] or value['words'] > value['length']:
            raise ValueError('DOM_RECEIPT_COUNTS')
        profiles[value['profile']].append(value)
    required = {
        'ordinary': [('firstFive', 20, 5, 5, 1), ('undo', 19, 5, 4, 0), ('sixth', 24, 6, 5, 1)],
        'no-suggestions': [('literalFive', 20, 5, 0, 0), ('literalBackspace', 19, 5, 0, 0)],
    }
    outcomes = {}
    for profile, stages in required.items():
        rows = profiles[profile]
        if not any(row['length'] == row['words'] == row['corrections'] == 0 for row in rows):
            raise ValueError('DOM_FRESH_EDITOR_MISSING')
        start = 0
        for flag, length, words, corrections, last in stages:
            for index in range(start, len(rows)):
                row = rows[index]
                if row[flag] == 1 and (row['length'], row['words'], row['corrections'], row['lastCorrected']) == (length, words, corrections, last):
                    start = index + 1
                    break
            else:
                raise ValueError('DOM_STAGE_MISSING_' + profile + '_' + flag)
        outcomes[profile] = {'passed': True, 'orderedStages': len(stages), 'records': len(rows)}
    if ('OK (2 tests)' not in native or 'FAILURES!!!' in native or 'INSTRUMENTATION_FAILED' in native or
        len(re.findall(r'^INSTRUMENTATION_STATUS_CODE: 0$', native, re.M)) != 2 or
        re.search(r'^INSTRUMENTATION_STATUS_CODE: -(?:3|4)$', native, re.M)):
        raise ValueError('NATIVE_RUN_INCOMPLETE')
    return {'passed': True, 'nativeTests': 2, 'profiles': outcomes, 'numericOnly': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', required=True, type=Path)
    parser.add_argument('--native-log', required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.receipt.stat().st_size > 256 * 1024 or args.native_log.stat().st_size > 1024 * 1024:
            raise ValueError('INPUT_SIZE')
        records = [json.loads(line) for line in args.receipt.read_text().splitlines()]
        result = verify(records, args.native_log.read_text())
    except (ValueError, OSError) as error:
        # Never echo input or JSON parsing excerpts that could contain unexpected payload.
        print('Chrome editor verification FAILED:', type(error).__name__)
        raise SystemExit(1)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
