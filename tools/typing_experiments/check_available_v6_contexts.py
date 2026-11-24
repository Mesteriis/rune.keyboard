"""Check the retained v6 source-context anchors without downloading text."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

import recover_available_v6_contexts as recovery

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'tools/typing_experiments/available-v6-article-origin-v1/context-recovery'
ANCHORS_SHA256 = '2fc6aecbc3616ffdb80c124b16e2d5bd7c6c74d0eb7be3731ab9034845bfb472'


def check(directory=DIRECTORY):
    directory = Path(directory)
    raw = (directory / 'anchors.jsonl').read_bytes()
    receipt = json.loads((directory / 'receipt.json').read_bytes())
    recovery.article_check.check()
    lock, lock_raw = recovery.articles.read_lock()
    mapping_raw = recovery.MAPPING.read_bytes()
    mapping = [json.loads(line) for line in mapping_raw.splitlines()]
    ledger = recovery.holdout_ledger.load_ledger(recovery.LEDGER)
    targets = recovery.sentence_targets(ledger)
    if (receipt.get('schema') != 1 or
            receipt.get('scope') != 'source-context-anchor-diagnostic-not-corpus-reproduction' or
            receipt.get('independentQualification') is not False or
            receipt.get('corpusRowsRecovered') is not False or
            receipt.get('sourceDecoderAttested') is not False or
            receipt.get('offsets') != 'zero-based NFC Unicode code points' or
            receipt.get('sourceLockSha256') != hashlib.sha256(lock_raw).hexdigest() or
            receipt.get('articleMappingSha256') != hashlib.sha256(mapping_raw).hexdigest() or
            receipt.get('anchorsSha256') != ANCHORS_SHA256 or
            hashlib.sha256(raw).hexdigest() != ANCHORS_SHA256):
        raise ValueError('V6_CONTEXT_RECEIPT')
    helpers = receipt.get('helperSha256')
    expected_helpers = {'tools/typing_experiments/recover_available_v6_contexts.py',
        'tools/typing_experiments/right_context_sentence_selection.py',
        'tools/eval/smart-typing-0.3/qualification-v2/generate_corpus.py',
        'tools/typing_experiments/recover_available_v6_articles.py',
        'tools/typing_experiments/check_available_v6_articles.py',
        'tools/typing_experiments/holdout_ledger.py',
        'tools/typing_experiments/prepare_external_spelling_holdout.py',
        'tools/typing_experiments/source_identities.py',
        'tools/typing_experiments/conversation_split_checks.py',
        'tools/typing_experiments/frozen_sources/prepare_60f079e28a18fd98.py'}
    if not isinstance(helpers, dict) or set(helpers) != expected_helpers or any(
            recovery.articles.sha_file(ROOT / name) != digest for name, digest in helpers.items()):
        raise ValueError('V6_CONTEXT_HELPER_BINDING')
    if not isinstance(receipt.get('ledgerSha256'), str) or not re.fullmatch('[0-9a-f]{64}', receipt['ledgerSha256']):
        raise ValueError('V6_CONTEXT_LEDGER_BINDING')
    by_article = {row['article']: row for row in mapping}
    anchors = [json.loads(line) for line in raw.splitlines()]
    source_anchors = Counter()
    seen = set()
    for row in anchors:
        if (not isinstance(row, dict) or set(row) != {'article', 'articlePartition', 'source', 'wordStart',
                'wordEnd', 'contextHash', 'sentenceKey', 'sentencePartition'} or
                row['article'] not in by_article or type(row['wordStart']) is not int or
                type(row['wordEnd']) is not int or row['wordStart'] < 0 or
                not 3 <= row['wordEnd'] - row['wordStart'] <= 20 or
                not isinstance(row['contextHash'], str) or not re.fullmatch('[0-9a-f]{64}', row['contextHash'])):
            raise ValueError('V6_CONTEXT_ANCHOR')
        article = by_article[row['article']]
        key = next(iter(recovery.holdout_ledger.keys_for([{'contextHash': row['contextHash']}], 'sentence')))
        identity = (row['source'], row['article'], row['wordStart'], row['wordEnd'], key)
        if (article['shard'] != row['source'] or article['partition'] != row['articlePartition'] or
                key != row['sentenceKey'] or targets.get(key) != row['sentencePartition'] or identity in seen):
            raise ValueError('V6_CONTEXT_ANCHOR_IDENTITY')
        seen.add(identity)
        source_anchors[row['source']] += 1
    if anchors != sorted(anchors, key=lambda a: (a['sentencePartition'], a['sentenceKey'], int(a['article']), a['wordStart'])):
        raise ValueError('V6_CONTEXT_ORDER')
    source_counts = receipt.get('sourceCounts')
    shard_names = {s['name'] for s in lock['shards']}
    article_counts = Counter(row['shard'] for row in mapping)
    if not isinstance(source_counts, dict) or set(source_counts) != shard_names or any(
            source_counts[name] != {'sourceRows': 92622, 'articles': article_counts[name],
                                    'foldingRefusals': 0, 'anchors': source_anchors[name]}
            for name in shard_names):
        raise ValueError('V6_CONTEXT_SOURCE_COUNTS')
    summary = recovery.summarize(targets, anchors)
    if (receipt.get('targetCounts') != dict(Counter(targets.values())) or
            receipt.get('totalTargets') != len(targets) or
            any(receipt.get(k) != v for k, v in summary.items())):
        raise ValueError('V6_CONTEXT_COUNTS')
    return dict(targets=len(targets), anchors=len(anchors), **summary, independentQualification=False)


if __name__ == '__main__':
    print(json.dumps(check(), sort_keys=True))
