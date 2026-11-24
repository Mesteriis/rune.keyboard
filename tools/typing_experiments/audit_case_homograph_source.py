#!/usr/bin/env python3
"""Screen source-attested homographs; outputs are disclosed regression evidence."""
import argparse
import bz2
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from holdout_ledger import keys_for, load_ledger

SOURCE_SHA = '982264e0857d2574ada9d1c07897e816ab9c4a8fb139f05320b5836f53d4d7ed'
TARGETS = frozenset(('клавы', 'читы', 'моника'))
WORD = re.compile(r'(?<![а-яё])[а-яё]+(?![а-яё])', re.IGNORECASE)


def scan(lines, blocked):
    seen = set()
    hits = []
    for line in lines:
        row = line.rstrip('\n').split('\t')
        if len(row) != 4 or row[1] != 'rus' or not row[0].isascii() or not row[0].isdecimal():
            raise ValueError('HOMOGRAPH_SOURCE_ROW')
        if row[0] in seen:
            raise ValueError('HOMOGRAPH_DUPLICATE_ARTICLE')
        seen.add(row[0])
        matches = [m for m in WORD.finditer(row[2]) if m.group().casefold() in TARGETS]
        if not matches:
            continue
        article = {'sourceRepository': 'tatoeba', 'article': 'tatoeba:' + row[0], 'language': 'ru'}
        if keys_for([article], 'article') - blocked:
            raise ValueError('HOMOGRAPH_SOURCE_NOT_EXCLUDED')
        for match in matches:
            hits.append({'article': article['article'], 'typed': match.group().casefold(),
                         'sourceCase': 'title' if match.group()[0].isupper() else 'lower',
                         'sentenceInitial': not row[2][:match.start()].strip()})
    if not hits:
        raise ValueError('HOMOGRAPH_NO_HITS')
    counts = Counter((r['typed'], r['sourceCase'], r['sentenceInitial']) for r in hits)
    return {'occurrences': len(hits), 'articles': len({h['article'] for h in hits}),
            'buckets': [{'token': token, 'sourceCase': case, 'sentenceInitial': initial, 'occurrences': count}
                        for (token, case, initial), count in sorted(counts.items())],
            'hits': hits}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'ledger', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    paths = {'source': args.source, 'ledger': args.ledger, 'tool': Path(__file__),
             'ledgerTool': Path(__file__).with_name('holdout_ledger.py'),
             'identityTool': Path(__file__).with_name('source_identities.py'),
             'splitTool': Path(__file__).with_name('conversation_split_checks.py')}
    hashes = {key: digest(path) for key, path in paths.items()}
    if hashes['source'] != SOURCE_SHA:
        raise ValueError('HOMOGRAPH_SOURCE_IDENTITY')
    ledger = load_ledger(args.ledger)
    blocked = {key for entry in ledger['entries'] for key in entry['keys'].get('article', [])}
    with bz2.open(args.source, 'rt', encoding='utf-8', newline='') as stream:
        result = scan(stream, blocked)
    if any(digest(path) != hashes[key] for key, path in paths.items()):
        raise ValueError('HOMOGRAPH_INPUT_DRIFT')
    report = {'schema': 1, 'purpose': 'DISCLOSED_SOURCE_SCREEN_NOT_QUALIFICATION',
              'bindings': hashes, 'independentQualification': False, 'result': result}
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(result['buckets'], ensure_ascii=False))


if __name__ == '__main__':
    main()
