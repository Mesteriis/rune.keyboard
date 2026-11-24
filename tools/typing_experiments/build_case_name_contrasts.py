#!/usr/bin/env python3
"""Extract disclosed title-case contrasts from excluded pinned public articles."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from holdout_ledger import keys_for, load_ledger

ROOT = Path(__file__).resolve().parents[2]
SOURCE_SHA = 'bf3781c558a3a2b8125e567f060895ead704577943832e6047bcc71f202975fd'
WORD = re.compile(r'(?<!\w)[а-яё]+(?!\w)', re.IGNORECASE)
PREFIX = re.compile(r'([а-яё]+(?:[ \t]+[а-яё]+){0,5})[ \t]+$', re.IGNORECASE)
COMPOUND = frozenset("-‐‑‒–—'’")


def extract(articles, keys, blocked):
    seen = set()
    rows = []
    for article in articles:
        if set(article) != {'id', 'text'} or not isinstance(article['id'], str) or not isinstance(article['text'], str):
            raise ValueError('NAME_CONTRAST_SOURCE_ROW')
        identity = article['id']
        if identity in seen:
            raise ValueError('NAME_CONTRAST_DUPLICATE_ARTICLE')
        seen.add(identity)
        if keys_for([{'article': identity}], 'article') - blocked:
            continue
        text = article['text']
        for match in WORD.finditer(text):
            token = match.group()
            if token.lower() not in keys or not token.istitle():
                continue
            # Do not treat a fragment of a hyphenated or apostrophized name as a whole token.
            if (match.start() and text[match.start() - 1] in COMPOUND) or (match.end() < len(text) and text[match.end()] in COMPOUND):
                continue
            start = max(0, match.start() - 256)
            prefix = PREFIX.search(text[start:match.start()])
            if not prefix or (start > 0 and prefix.start() == 0):
                continue
            rows.append({'id': f'case-wiki-{identity}-{match.start()}', 'split': 'calibration', 'language': 'ru',
                         'prefix': prefix.group(1).lower(), 'typed': token.lower(), 'expectedSpelling': token,
                         'article': identity, 'clusterId': 'wikipedia:' + identity, 'cohort': 'name_contrast',
                         'noAuto': False, 'sourceProfile': 'excluded-public-wikipedia',
                         'purpose': 'DISCLOSED_NAME_CONTRAST_NOT_QUALIFICATION'})
    if not rows:
        raise ValueError('NAME_CONTRAST_EMPTY')
    return rows


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'screen', 'ledger', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    args = p.parse_args()
    output = args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'):
        raise ValueError('NAME_CONTRAST_OUTPUT')
    import pyarrow
    import pyarrow.parquet as pq
    if pyarrow.__version__ != '25.0.1':
        raise ValueError('NAME_CONTRAST_PYARROW_VERSION')
    paths = {'source': args.source, 'screen': args.screen, 'ledger': args.ledger, 'tool': Path(__file__),
             'ledgerTool': Path(__file__).with_name('holdout_ledger.py'),
             'identityTool': Path(__file__).with_name('source_identities.py'),
             'splitTool': Path(__file__).with_name('conversation_split_checks.py')}
    hashes = {name: digest(path) for name, path in paths.items()}
    if hashes['source'] != SOURCE_SHA:
        raise ValueError('NAME_CONTRAST_SOURCE_IDENTITY')
    screen = json.loads(args.screen.read_text())
    if screen.get('purpose') != 'DISCLOSED_LOWERCASE_EVIDENCE_SCREEN_NOT_QUALIFICATION' or screen.get('bindings', {}).get('ledger') != hashes['ledger']:
        raise ValueError('NAME_CONTRAST_SCREEN')
    keys = {item['token'] for item in screen['result']['lowercaseEvidence'] if item['lowerArticles'] > 0}
    if not keys:
        raise ValueError('NAME_CONTRAST_KEYS')
    ledger = load_ledger(args.ledger)
    blocked = {key for entry in ledger['entries'] for key in entry['keys'].get('article', [])}
    def articles():
        for batch in pq.ParquetFile(args.source).iter_batches(batch_size=256, columns=['id', 'text']):
            yield from batch.to_pylist()
    rows = extract(articles(), keys, blocked)
    if any(digest(path) != hashes[name] for name, path in paths.items()):
        raise ValueError('NAME_CONTRAST_INPUT_DRIFT')
    payload = ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n' for r in rows).encode()
    output.mkdir(mode=0o700, parents=True)
    (output / 'rows.jsonl').write_bytes(payload)
    report = {'schema': 1, 'purpose': 'DISCLOSED_NAME_CONTRAST_NOT_QUALIFICATION', 'independentQualification': False,
              'bindings': hashes, 'rowsSha256': hashlib.sha256(payload).hexdigest(), 'pyarrowVersion': pyarrow.__version__,
              'counts': {'rows': len(rows), 'articles': len({r['article'] for r in rows}),
                         'tokens': dict(sorted(Counter(r['typed'] for r in rows).items()))}}
    (output / 'manifest.json').write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps(report['counts'], ensure_ascii=False))


if __name__ == '__main__':
    main()
