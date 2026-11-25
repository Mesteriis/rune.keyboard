"""Summarize disclosed phrase changes by Tatoeba source account."""
import argparse
import bz2
from collections import Counter
import io
import json
from pathlib import Path
import re

import register_tatoeba_phrase_observed as observed
from chat_corpus_report import wilson


CONTROL_ID = re.compile(r'chat-regression-([0-9]+)-control')
TIMESTAMP = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}')


def match_accounts(sentence_ids, source_lines, detailed_lines):
    source = {}
    for line in source_lines:
        sentence, language, text, modified = line.rstrip('\n').split('\t')
        if sentence not in sentence_ids:
            continue
        if language != 'rus' or sentence in source or not TIMESTAMP.fullmatch(modified):
            raise ValueError('TATOEBA_CONTRIBUTOR_SOURCE_ROW')
        source[sentence] = (text, modified)
    if source.keys() != sentence_ids:
        raise ValueError('TATOEBA_CONTRIBUTOR_CONTROL_ID')

    accounts = {}
    coverage = dict(exactWithOwner=0, differentText=0, differentModificationTime=0, missingOwner=0)
    for line in detailed_lines:
        sentence, language, text, account, _, modified = line.rstrip('\n').split('\t')
        if sentence not in source:
            continue
        if language != 'rus' or sentence in accounts:
            raise ValueError('TATOEBA_CONTRIBUTOR_DETAILED_ROW')
        accounts[sentence] = None
        if text != source[sentence][0]:
            coverage['differentText'] += 1
        elif modified != source[sentence][1]:
            coverage['differentModificationTime'] += 1
        elif account in ('', r'\N', '\\N'):
            coverage['missingOwner'] += 1
        elif TIMESTAMP.fullmatch(account):
            raise ValueError('TATOEBA_CONTRIBUTOR_OWNER_FIELD')
        else:
            coverage['exactWithOwner'] += 1
            accounts[sentence] = account
    coverage['missingSentence'] = len(source) - len(accounts)
    return accounts, dict(coverage)


def account_groups(phrases, source_lines, detailed_lines):
    changes = {}
    for phrase_id, changed in phrases:
        match = CONTROL_ID.fullmatch(phrase_id)
        if not match or match[1] in changes or type(changed) is not bool:
            raise ValueError('TATOEBA_CONTRIBUTOR_CONTROL_ID')
        changes[match[1]] = changed
    accounts, coverage = match_accounts(set(changes), source_lines, detailed_lines)
    cluster_sizes = Counter()
    changed_clusters = set()
    unknown_changes = 0
    for sentence, changed in changes.items():
        account = accounts.get(sentence)
        if account is None:
            unknown_changes += changed
            continue
        cluster_sizes[account] += 1
        if changed:
            changed_clusters.add(account)

    sizes = cluster_sizes.values()
    changed_phrases = sum(changes.values())
    matched_phrases = sum(sizes)
    return {
        'phrases': len(changes),
        'changedPhrases': changed_phrases,
        'phraseWilson95': wilson(changed_phrases, len(changes)),
        'matchedPhraseWilson95': wilson(changed_phrases - unknown_changes, matched_phrases),
        'phrasesWithAccount': matched_phrases,
        'phrasesWithoutAccount': len(changes) - matched_phrases,
        'changedPhrasesWithoutAccount': unknown_changes,
        'accounts': len(cluster_sizes),
        'accountsWithChangedPhrase': len(changed_clusters),
        'accountAnyChangeWilson95': wilson(len(changed_clusters), len(cluster_sizes)),
        'singlePhraseAccounts': sum(size == 1 for size in sizes),
        'largestAccountPhraseCount': max(sizes, default=0),
        'topTenAccountPhraseCount': sum(size for _, size in cluster_sizes.most_common(10)),
        'detailedJoin': coverage,
    }


def summarize(run_dir, detailed):
    fixture, receipt_raw = observed.extract(run_dir)
    receipt = json.loads(receipt_raw)
    if receipt.get('sourceLabelsQualified') is not False:
        raise ValueError('TATOEBA_CONTRIBUTOR_SCOPE')
    archive = observed.source.SOURCE
    archive_key = str(archive.relative_to(observed.ROOT))
    archive_digest = receipt['inputSha256'][archive_key]
    raw = (run_dir / 'run-1.jsonl').read_bytes()
    if observed.sha(raw) != fixture['resultSha256']:
        raise ValueError('TATOEBA_CONTRIBUTOR_REPLAY_DRIFT')
    rows = (json.loads(line) for line in raw.splitlines())
    phrases = ((row['id'], any(stage['changed'] for stage in row['phraseStages'])) for row in rows)
    archive_raw = archive.read_bytes()
    if observed.sha(archive_raw) != archive_digest:
        raise ValueError('TATOEBA_CONTRIBUTOR_ARCHIVE_DRIFT')
    detailed_raw = detailed.read_bytes()
    with bz2.open(io.BytesIO(detailed_raw), 'rt', encoding='utf-8') as detailed_lines:
        grouping = account_groups(phrases, io.StringIO(bz2.decompress(archive_raw).decode('utf-8')),
                                  detailed_lines)
    if grouping['changedPhrases'] != receipt['metrics']['changedPhrases']:
        raise ValueError('TATOEBA_CONTRIBUTOR_CHANGED_COUNT')
    return {
        'schema': 1,
        'scope': 'disclosed-tatoeba-source-account-diagnostic',
        'independentQualification': False,
        'sourceLabelsQualified': False,
        'sourceSha256': archive_digest,
        'detailedSha256': observed.sha(detailed_raw),
        'replayReceiptSha256': fixture['receiptSha256'],
        'resultSha256': fixture['resultSha256'],
        'unregisteredControlKeys': len(fixture['controlKeys']),
        'unregisteredContextKeys': len(fixture['contextKeys']),
        'phraseMetrics': receipt['metrics'],
        'grouping': grouping,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--detailed', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(summarize(args.run, args.detailed), sort_keys=True, indent=2))
