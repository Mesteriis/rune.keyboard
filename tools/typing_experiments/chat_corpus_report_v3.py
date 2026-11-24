#!/usr/bin/env python3
"""Describe the disclosed Tatoeba chat replay with checked source clusters."""
import argparse
import bz2
import hashlib
import json
from pathlib import Path
import re

import chat_corpus_report_v2 as previous
import chat_corpus
import holdout_ledger

ARTICLE = re.compile(r'tatoeba:[0-9]+\Z')
SHA256 = re.compile(r'[0-9a-f]{64}\Z')


def validate_clusters(rows):
    groups = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('CHAT_CLUSTER_ROW')
        article = row.get('article')
        sentence = row.get('sentenceHash')
        if (not isinstance(article, str) or not ARTICLE.fullmatch(article) or
                row.get('sourceRepository') != 'tatoeba' or row.get('clusterId') != article or
                not isinstance(sentence, str) or not SHA256.fullmatch(sentence)):
            raise ValueError('CHAT_CLUSTER_IDENTITY')
        identity = (sentence, row.get('prefix'), row.get('expectedSpelling'))
        if not all(isinstance(value, str) and value for value in identity):
            raise ValueError('CHAT_CLUSTER_IDENTITY')
        if article not in groups:
            groups[article] = [identity, 0]
        if groups[article][0] != identity:
            raise ValueError('CHAT_CLUSTER_INCONSISTENT')
        groups[article][1] += row.get('edit_kind') == 'control'
    if not groups or any(count != 1 for _, count in groups.values()):
        raise ValueError('CHAT_CLUSTER_CONTROL_COUNT')


def report(rows, observations):
    validate_clusters(rows)
    result = previous.report(rows, observations)
    result['schema'] = 3
    result['clusterVerification'] = 'tatoeba-article-identity-and-one-control-per-group'
    return result


def verify_source_rows(rows_raw, source_raw, lock_raw, ledger_raw):
    if hashlib.sha256(lock_raw).hexdigest() != chat_corpus.CC0_LOCK_SHA:
        raise ValueError('CHAT_SOURCE_LOCK')
    lock = json.loads(lock_raw)
    if (lock.get('url') != chat_corpus.URL or lock.get('license') != 'CC0-1.0' or
            lock.get('compressedSha256') != hashlib.sha256(source_raw).hexdigest()):
        raise ValueError('CHAT_SOURCE_IDENTITY')
    ledger = holdout_ledger.validate_ledger(json.loads(ledger_raw))
    excluded = {value for entry in ledger['entries'] for value in entry['keys'].get('article', [])}
    lines = bz2.decompress(source_raw).decode('utf-8').splitlines(keepends=True)
    rows, _ = chat_corpus.generate(lines, excluded)
    regenerated = ''.join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
                          for row in rows).encode()
    if regenerated != rows_raw:
        raise ValueError('CHAT_SOURCE_ROWS_MISMATCH')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('rows', 'observations', 'source', 'lock', 'ledger', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('CHAT_OUTPUT_EXISTS')
    paths = {'rows': args.rows, 'observations': args.observations, 'source': args.source,
             'lock': args.lock, 'ledger': args.ledger}
    raw = {name: path.read_bytes() for name, path in paths.items()}
    helper_paths = [Path(__file__), Path(previous.__file__), Path(previous.historical.__file__),
                    Path(previous.historical.__file__).with_name('typing_quality_slices.py'),
                    Path(chat_corpus.__file__), Path(holdout_ledger.__file__),
                    Path(chat_corpus.__file__).with_name('import_tatoeba_history.py'),
                    Path(chat_corpus.__file__).with_name('recover_legacy_families.py'),
                    Path(chat_corpus.__file__).with_name('conversation_split_checks.py'),
                    Path(chat_corpus.__file__).with_name('source_identities.py')]
    helpers = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in helper_paths}
    parsed = {name: [json.loads(line) for line in raw[name].decode('utf-8').splitlines() if line.strip()]
              for name in ('rows', 'observations')}
    validate_clusters(parsed['rows'])
    verify_source_rows(raw['rows'], raw['source'], raw['lock'], raw['ledger'])
    result = report(parsed['rows'], parsed['observations'])
    result['sourceVerification'] = 'pinned-source-and-ledger-regenerated-byte-identical-rows'
    if any(path.read_bytes() != raw[name] for name, path in paths.items()):
        raise ValueError('CHAT_INPUT_DRIFT')
    if any(hashlib.sha256(path.read_bytes()).hexdigest() != helpers[path.name] for path in helper_paths):
        raise ValueError('CHAT_HELPER_DRIFT')
    result['inputs'] = {name: hashlib.sha256(data).hexdigest() for name, data in raw.items()}
    result['helpers'] = helpers
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()
