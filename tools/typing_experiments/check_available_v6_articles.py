"""Check the retained public v6 article mapping without downloading source text."""
import hashlib
import json
from pathlib import Path
import re

import recover_available_v6_articles as recovery

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'tools/typing_experiments/available-v6-article-origin-v1/recovered'
ARTICLES_SHA256 = '0f55e171539de0b476041a960f2a8f212ff6b4bfac23625aed8eecd84d8b2d88'


def check(directory=DIRECTORY):
    directory = Path(directory)
    raw = (directory / 'articles.jsonl').read_bytes()
    receipt = json.loads((directory / 'receipt.json').read_bytes())
    lock, lock_raw = recovery.read_lock()
    ledger = recovery.holdout_ledger.load_ledger(recovery.LEDGER)
    recovery.verify_historical_source_bindings(lock, ledger)
    targets = recovery.target_index(ledger)
    if (receipt.get('schema') != 1 or
            receipt.get('scope') != 'public-article-identity-not-corpus-reproduction' or
            receipt.get('independentQualification') is not False or
            receipt.get('corpusRowsRecovered') is not False or
            receipt.get('sourceDecoderAttested') is not False or
            receipt.get('sourceLockSha256') != hashlib.sha256(lock_raw).hexdigest() or
            receipt.get('articlesSha256') != ARTICLES_SHA256 or
            hashlib.sha256(raw).hexdigest() != ARTICLES_SHA256):
        raise ValueError('V6_ARTICLE_RECEIPT')
    helpers = receipt.get('helperSha256')
    expected_helpers = {'tools/typing_experiments/recover_available_v6_articles.py',
        'tools/typing_experiments/holdout_ledger.py', 'tools/typing_experiments/source_identities.py',
        'tools/typing_experiments/conversation_split_checks.py',
        'tools/typing_experiments/frozen_sources/prepare_60f079e28a18fd98.py'}
    if not isinstance(helpers, dict) or set(helpers) != expected_helpers or any(
            recovery.sha_file(ROOT / name) != digest for name, digest in helpers.items()):
        raise ValueError('V6_ARTICLE_HELPER_BINDING')
    if not isinstance(receipt.get('ledgerSha256'), str) or not re.fullmatch('[0-9a-f]{64}', receipt['ledgerSha256']):
        raise ValueError('V6_ARTICLE_LEDGER_BINDING')
    rows = [json.loads(line) for line in raw.splitlines()]
    shards = {item['name'] for item in lock['shards']}
    seen = set()
    counts = {p: 0 for p in ('calibration', 'holdout')}
    per_shard = {name: 0 for name in shards}
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {'article', 'articleKey', 'partition', 'shard'} or
                not isinstance(row['article'], str) or not row['article'].isascii() or
                not row['article'].isdecimal() or row['article'] != str(int(row['article'])) or
                row['partition'] not in counts or row['shard'] not in shards):
            raise ValueError('V6_ARTICLE_ROW')
        key = next(iter(recovery.holdout_ledger.keys_for([{'article': row['article']}], 'article')))
        if key != row['articleKey'] or targets.get(key) != row['partition'] or key in seen:
            raise ValueError('V6_ARTICLE_ROW_IDENTITY')
        seen.add(key)
        counts[row['partition']] += 1
        per_shard[row['shard']] += 1
    if seen != set(targets) or rows != sorted(rows, key=lambda r: (r['partition'], int(r['article']))):
        raise ValueError('V6_ARTICLE_COVERAGE')
    source_counts = receipt.get('sourceCounts')
    if (receipt.get('partitionCounts') != counts or not isinstance(source_counts, dict) or
            set(source_counts) != shards or any(source_counts[name] !=
                {'sourceRows': 92622, 'matches': per_shard[name]} for name in shards)):
        raise ValueError('V6_ARTICLE_COUNTS')
    return {'partitions': counts, 'articles': len(rows), 'independentQualification': False}


if __name__ == '__main__':
    print(json.dumps(check(), sort_keys=True))
