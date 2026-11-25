"""Verify captured revision witnesses and report coverage of the pinned v6 article index."""

import argparse
from collections import Counter
import json
from pathlib import Path
import re

from check_available_v6_articles import ARTICLES_SHA256, DIRECTORY
from holdout_ledger import source_segment_hash
from recover_available_v6_articles import ROOT, read_lock
from recover_v6_revision_witnesses import (
    CLEANER_REVISION, CLEANER_SHA256, DUMP_DAY_END, REVISION_LIMIT, UPPER_BOUND, digest,
)


PARTITIONS = ('calibration', 'holdout')
STATUSES = {'content-match', 'no-content-match', 'missing-page', 'no-readable-content', 'api-unavailable'}
SHA256 = re.compile(r'[a-f0-9]{64}')
TIMESTAMP = re.compile(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ')
CORPUS_RECEIPT = ROOT / 'docs/acceptance/2026-11-24-q6-final-v6-recovery.json'
FINEWIKI_RECEIPT = 'finewiki-revision-witnesses.json'
FINEWIKI_RECEIPT_SHA256 = 'a268460401eb4d91602478c68c372b7ab46429f131add4908512caaedaba23b7'
KIWIX_RECEIPT = 'kiwix-source-windows.json'
KIWIX_RECEIPT_SHA256 = '0fa4daa19a84561523b310ef07d42a2d9339283b492c0eaa447f37acf8b80f9e'
MIRROR_RECEIPT = 'mirror-source-window.json'
MIRROR_RECEIPT_SHA256 = '03c4f078f1cab4ce1b7b0f107c81a43f1ebf1a82082266affab21d497f4f9472'
EXTENDED_HISTORY_SHA256 = {
    '0017.parquet': '228e093682d29cbf6e25f9f9d88b19becd6efa32d045200038e0ffe1ea3a1ff9',
}
ARCHIVE_EXCEPTIONS_SHA256 = {
    '0013.parquet': '6eb77fcc78371530cd78bd3ef3b07d416d932623ea57c9e6748f0104da0f94ee',
    '0014.parquet': 'b3c4181adff79a790cffe893c268fef8c69a8e9878e29d6b7c81e08a4426456d',
    '0015.parquet': '4847a1b8758e8413926cdcc970cbe24cb9790f7cd613acb943429a184eb65777',
    '0016.parquet': '8377b1aa797968120fc64729da917bab424a6f6c1a9841aa18dc241e56eeba6c',
    '0017.parquet': 'bc467ae77c4bfb0100327fc7e87f217761e5c1ceb97967bbf4f8cdffe6c747d9',
    '0018.parquet': '85b59c36aeac603652b078ae902fcd857642d0d262622dfbe7ef36e7a09b3a59',
    '0019.parquet': 'fc33a82efc6b7e1d64eb46eb51408b65cf455c93e7961e93cc1e027d21bd40d2',
    '0020.parquet': '22b54ca72e381f809f2054bd7ca863ddb20832f26adc0bb07b40e6493a509d27',
}


def verify_rows(rows, expected, shard_name):
    actual = {}
    revision_pages = {}
    for row in rows:
        article, partition = row['article'], row['partition']
        if article in actual or expected.get(article) != partition:
            raise ValueError('V6_WITNESS_PAGE_IDENTITY:' + shard_name)
        actual[article] = partition
        compared, matches, status = row['comparedRevisions'], row['matches'], row['status']
        snapshot_digest = row['snapshotTextSha256']
        if (status not in STATUSES or type(compared) is not int or
                not isinstance(matches, list) or not len(matches) <= compared <= REVISION_LIMIT or
                (status == 'content-match') != bool(matches) or
                (status in ('content-match', 'no-content-match')) != (compared > 0) or
                type(row['hasEarlierContinuation']) is not bool or not isinstance(snapshot_digest, str) or
                not SHA256.fullmatch(snapshot_digest)):
            raise ValueError('V6_WITNESS_ROW_SCHEMA:' + shard_name)
        for item in matches:
            revid, timestamp = item['revid'], item['timestamp']
            if (type(revid) is not int or revid < 1 or revid in revision_pages or
                    not isinstance(timestamp, str) or not TIMESTAMP.fullmatch(timestamp) or timestamp > UPPER_BOUND):
                raise ValueError('V6_WITNESS_REVISION_IDENTITY:' + shard_name)
            revision_pages[revid] = article
    if actual != expected:
        raise ValueError('V6_WITNESS_INDEX_COVERAGE:' + shard_name)
    return revision_pages


def summarize(rows):
    return {'articles': len(rows), 'statusCounts': dict(Counter(row['status'] for row in rows)),
            'comparedRevisions': sum(row['comparedRevisions'] for row in rows),
            'matchingRevisions': sum(len(row['matches']) for row in rows),
            'multipleMatches': sum(len(row['matches']) > 1 for row in rows),
            'earlierContinuation': sum(row['hasEarlierContinuation'] for row in rows),
            'withMatchOnOrBeforeDumpDate': sum(any(item['timestamp'] <= DUMP_DAY_END for item in row['matches'])
                                               for row in rows)}


def checked_shard(directory, shard, expected, lock_sha):
    receipt = json.loads((directory / 'receipt.json').read_bytes())
    raw = (directory / 'articles.jsonl').read_bytes()
    bindings = {'schema': 1, 'articlesSha256': digest(raw), 'sourceShard': shard['name'],
                'sourceShardSha256': shard['sha256'], 'sourceLockSha256': lock_sha,
                'sourceIndexSha256': ARTICLES_SHA256, 'cleanerRevision': CLEANER_REVISION,
                'cleanerSha256': CLEANER_SHA256, 'parserVersion': '0.6.5',
                'apiUpperBound': UPPER_BOUND, 'apiRevisionLimitPerPage': REVISION_LIMIT,
                'dumpDateCutoff': DUMP_DAY_END}
    if (any(receipt.get(key) != value for key, value in bindings.items()) or
            receipt.get('originalDumpRevisionIdsVerified') is not False or
            receipt.get('independentQualification') is not False):
        raise ValueError('V6_WITNESS_RECEIPT:' + shard['name'])
    rows = list(map(json.loads, raw.splitlines()))
    revisions = verify_rows(rows, expected, shard['name'])
    summary = summarize(rows)
    if any(receipt.get(key) != value for key, value in summary.items()
           if key != 'statusCounts' or key in receipt):
        raise ValueError('V6_WITNESS_COUNTS:' + shard['name'])
    return rows, revisions, summary, receipt


def count_corpus_rows(rows):
    return {'rows': len(rows), 'contexts': len({row['contextHash'] for row in rows}),
            'articles': len({row['article'] for row in rows})}


def project_corpus(corpus, index, witness_rows, original):
    statuses = {}
    for row in witness_rows:
        status = row['status']
        if status == 'content-match':
            by_date = any(item['timestamp'] <= DUMP_DAY_END for item in row['matches'])
            status = 'content-match-by-dump-date' if by_date else 'content-match-after-dump-date'
        statuses[row['article']] = status
    result, corpus_rows = {}, {}
    for part in PARTITIONS:
        name = part + '.jsonl'
        raw = (corpus / name).read_bytes()
        if digest(raw) != original[name]:
            raise ValueError('V6_WITNESS_CORPUS_DIGEST:' + part)
        rows = list(map(json.loads, raw.splitlines()))
        targets = {row['article'] for row in index if row['partition'] == part}
        if {row['article'] for row in rows} != targets or any(row['part'] != part for row in rows):
            raise ValueError('V6_WITNESS_CORPUS_INDEX:' + part)
        corpus_rows[part] = rows
        by_status, exceptions = {}, {}
        for row in rows:
            article = row['article']
            status = statuses.get(article, 'not-checked')
            by_status.setdefault(status, []).append(row)
            if status not in ('not-checked', 'content-match-by-dump-date'):
                exceptions.setdefault(article, []).append(row)
        result[part] = {
            'sha256': original[name], 'rows': len(rows),
            'statuses': {status: count_corpus_rows(group) for status, group in by_status.items()},
            'checkedExceptions': [
                {'article': article, 'status': statuses[article], 'rows': len(exceptions[article]),
                 'contexts': len({row['contextHash'] for row in exceptions[article]})}
                for article in sorted(exceptions, key=int)],
        }
    return result, corpus_rows


def partition_projection(witness_rows, corpus_rows, *, legacy=False):
    projection = {}
    for part in PARTITIONS:
        pages = {row['article']: row for row in witness_rows if row['partition'] == part}
        indexed = [row for row in corpus_rows[part] if row['article'] in pages]
        by_date = {article for article, page in pages.items()
                   if any(match['timestamp'] <= DUMP_DAY_END for match in page['matches'])}
        witnessed = [row for row in indexed if row['article'] in by_date]
        indexed_counts, witnessed_counts = count_corpus_rows(indexed), count_corpus_rows(witnessed)
        if legacy:
            multiple = sum(len(page['matches']) > 1 for page in pages.values())
            projection[part] = {**indexed_counts, 'multipleMatches': multiple,
                                'singleMatch': sum(len(page['matches']) == 1 for page in pages.values())}
        else:
            projection[part] = {
                'indexedArticles': indexed_counts['articles'],
                'indexedRows': indexed_counts['rows'],
                'indexedContexts': indexed_counts['contexts'],
                'withMatchOnOrBeforeDumpDate': len(by_date),
                'witnessedRows': witnessed_counts['rows'],
                'witnessedContexts': witnessed_counts['contexts'],
            }
    return projection


def verify_partition_binding(receipt, original, witness_rows, corpus_rows):
    shard = receipt['sourceShard']
    if receipt['corpusRowsSha256'] != {part: original[part + '.jsonl'] for part in PARTITIONS}:
        raise ValueError('V6_WITNESS_RECEIPT_CORPUS_DIGEST:' + shard)
    if corpus_rows is not None:
        expected = partition_projection(witness_rows, corpus_rows, legacy=shard in ('0011.parquet', '0012.parquet'))
        if receipt['partitions'] != expected:
            raise ValueError('V6_WITNESS_RECEIPT_PARTITION_COUNTS:' + shard)


def read_extended_history(directory, shard_receipt, shard_rows):
    shard = shard_receipt['sourceShard']
    path = directory / 'extended-history.json'
    if not path.is_file() or digest(raw := path.read_bytes()) != EXTENDED_HISTORY_SHA256[shard]:
        raise ValueError('V6_WITNESS_EXTENDED_HISTORY_DIGEST:' + shard)
    evidence = json.loads(raw)
    row = next((row for row in shard_rows if row['article'] == evidence['article']), None)
    if (row is None or row['status'] != 'no-content-match' or
            evidence['sourceShardArticlesSha256'] != shard_receipt['articlesSha256'] or
            evidence['snapshotTextSha256'] != row['snapshotTextSha256'] or
            evidence['corpusProjection']['partition'] != row['partition']):
        raise ValueError('V6_WITNESS_EXTENDED_HISTORY_SOURCE:' + shard)
    return evidence


def read_archive_exceptions(directory, shard_receipt, shard_rows):
    shard = shard_receipt['sourceShard']
    path = directory / 'archive-exceptions.json'
    if not path.is_file() or digest(raw := path.read_bytes()) != ARCHIVE_EXCEPTIONS_SHA256[shard]:
        raise ValueError('V6_WITNESS_ARCHIVE_DIGEST:' + shard)
    evidence = json.loads(raw)
    partitions = {row['article']: row['partition'] for row in shard_rows if row['status'] == 'missing-page'}
    archived = {row['article']: row for row in evidence['archiveMetadata']['rows']}
    if archived.keys() != partitions.keys() or evidence['sourceShardArticlesSha256'] != shard_receipt['articlesSha256']:
        raise ValueError('V6_WITNESS_ARCHIVE_SOURCE:' + shard)
    cases = {}
    for article, row in archived.items():
        if row.get('replayStatus') != 200:
            status = 'capture-unavailable'
        elif not row['pageIdentityMatches']:
            status = 'page-identity-mismatch'
        elif not row['ids'].get('wgRevisionId'):
            status = 'revision-not-displayed'
        else:
            status = 'source-window-unchecked'
        cases[article] = {'article': article, 'partition': partitions[article], 'status': status}

    reports = evidence['archivePassages']
    if 'checked' in reports:
        reports = {part: reports for part in PARTITIONS if f'historical{part.title()}Sha256' in reports}
    for part, report in reports.items():
        if report[f'historical{part.title()}Sha256'] != shard_receipt['corpusRowsSha256'][part]:
            raise ValueError('V6_WITNESS_ARCHIVE_CORPUS_DIGEST:' + shard)
        for row in report['checked']:
            article = row['article']
            metadata = archived[article]
            if (partitions[article] != part or not metadata['pageIdentityMatches'] or
                    metadata['ids']['wgRevisionId'] != row['displayedRevision'] or
                    metadata['htmlSha256'] != row['captureSha256']):
                raise ValueError('V6_WITNESS_ARCHIVE_CAPTURE:' + shard)
            status = 'source-window-unmatched'
            if row['fullWindowMatch']:
                status = 'full-source-window'
            elif row['rightMatch'] and not row['leftMatch']:
                status = 'right-context-only'
            elif row['leftMatch'] and not row['rightMatch']:
                status = 'left-context-only'
            cases[article].update(status=status, rows=row['rows'], contexts=row['contexts'])
    return list(cases.values())


def archive_projection(cases, corpus_rows):
    projected = []
    for item in cases:
        if corpus_rows is None:
            projected.append({key: item[key] for key in ('article', 'partition', 'status')})
            continue
        counts = count_corpus_rows([row for row in corpus_rows[item['partition']]
                                    if row['article'] == item['article']])
        if any(key in item and counts[key] != item[key] for key in ('rows', 'contexts')):
            raise ValueError('V6_WITNESS_ARCHIVE_PARTITION_COUNTS:' + item['article'])
        projected.append(dict(item, rows=counts['rows'], contexts=counts['contexts']))
    return projected


def kiwix_archive_coverage(path, archive_passages, original):
    if not path.is_file() or digest(raw := path.read_bytes()) != KIWIX_RECEIPT_SHA256:
        raise ValueError('V6_WITNESS_KIWIX_DIGEST')
    evidence = json.loads(raw)
    if (evidence['schema'] != 1 or
            evidence['corpusRowsSha256'] != {part: original[part + '.jsonl'] for part in PARTITIONS}):
        raise ValueError('V6_WITNESS_KIWIX_CORPUS_DIGEST')

    incomplete = {row['article']: row for row in archive_passages if row['status'] != 'full-source-window'}
    covered = set()
    revisions = set()
    for passage in evidence['passages']:
        article = passage['article']
        revision = passage['revision']
        if (article not in incomplete or article in covered or revision in revisions or
                revision < 1 or passage['blob'] < 0 or passage['rows'] < 1 or
                not 0 <= passage['firstByte'] <= passage['lastByte'] < evidence['archive']['bytes'] or
                not SHA256.fullmatch(passage['htmlSha256'])):
            raise ValueError('V6_WITNESS_KIWIX_PASSAGE:' + article)
        if 'rows' in incomplete[article] and incomplete[article]['rows'] != passage['rows']:
            raise ValueError('V6_WITNESS_KIWIX_PARTITION_COUNTS:' + article)
        covered.add(article)
        revisions.add(revision)

    unresolved = sorted(incomplete.keys() - covered, key=int)
    coverage = {
        'kiwixReceiptSha256': KIWIX_RECEIPT_SHA256,
        'kiwixWitnessedArticles': len(covered),
        'kiwixWitnessedRows': sum(row['rows'] for row in evidence['passages']),
        'unresolvedArticles': unresolved,
    }
    if all('rows' in row for row in archive_passages):
        coverage['unresolvedRows'] = sum(incomplete[article]['rows'] for article in unresolved)
    return coverage


def read_finewiki_witnesses(path, missing_articles, index_rows, prior_revisions):
    if not path.is_file() or digest(raw := path.read_bytes()) != FINEWIKI_RECEIPT_SHA256:
        raise ValueError('V6_WITNESS_FINEWIKI_DIGEST')
    evidence = json.loads(raw)
    if (evidence['schema'] != 1 or evidence['cleanerSha256'] != CLEANER_SHA256 or
            evidence['parserVersion'] != '0.6.5'):
        raise ValueError('V6_WITNESS_FINEWIKI_CLEANER')
    articles = {}
    revisions = set(prior_revisions)
    for witness in evidence['articles']:
        article, revid, timestamp = witness['article'], witness['revision'], witness['timestamp']
        if (article not in missing_articles or article in articles or revid in revisions or revid < 1 or
                not TIMESTAMP.fullmatch(timestamp) or timestamp > DUMP_DAY_END or
                witness['cleanedSha256'] != index_rows[article]['snapshotTextSha256'] or
                not SHA256.fullmatch(witness['wikitextSha256']) or witness['rows'] < 1):
            raise ValueError('V6_WITNESS_FINEWIKI_ARTICLE:' + article)
        articles[article] = witness
        revisions.add(revid)
    return articles


def mirror_archive_coverage(path, rows, coverage, original, corpus_rows):
    if not path.is_file() or digest(raw := path.read_bytes()) != MIRROR_RECEIPT_SHA256:
        raise ValueError('V6_WITNESS_MIRROR_DIGEST')
    evidence = json.loads(raw)
    article, part = evidence['article'], evidence['partition']
    indexed = next((row for row in rows if row['article'] == article), {})
    if (evidence['schema'] != 1 or article not in coverage['unresolvedArticles'] or
            part not in PARTITIONS or indexed.get('partition') != part or
            evidence['corpusSha256'] != original[part + '.jsonl'] or
            evidence['snapshotTextSha256'] != indexed.get('snapshotTextSha256') or
            evidence['cleanedSha256'] == evidence['snapshotTextSha256'] or
            evidence['cleanerSha256'] != CLEANER_SHA256 or evidence['parserVersion'] != '0.6.5' or
            not DUMP_DAY_END < evidence['mirrorTimestamp'] < evidence['deletionTimestamp']):
        raise ValueError('V6_WITNESS_MIRROR_BINDING')

    windows = evidence['windows']
    witnessed = Counter({(item['sha256'], item['full']): item['rows'] for item in windows})
    if (len(witnessed) != len(windows) or {full for _, full in witnessed} != {True, False} or
            any(not SHA256.fullmatch(item['sha256']) or type(item['full']) is not bool or
                item['rows'] < 1 or item['occurrences'] != 1 for item in windows)):
        raise ValueError('V6_WITNESS_MIRROR_WINDOWS')
    if corpus_rows is not None:
        observed = Counter()
        for row in corpus_rows[part]:
            if row['article'] == article:
                window = source_segment_hash(row['prefix'] + ' ' + row['word'] + row['rightContext'])
                observed[window, window == row['contextHash']] += 1
        if observed != witnessed:
            raise ValueError('V6_WITNESS_MIRROR_CORPUS_WINDOWS')

    count = witnessed.total()
    result = dict(coverage, mirrorReceiptSha256=MIRROR_RECEIPT_SHA256,
                  mirrorWitnessedArticles=1, mirrorWitnessedRows=count,
                  unresolvedArticles=[item for item in coverage['unresolvedArticles'] if item != article])
    if 'unresolvedRows' in coverage:
        result['unresolvedRows'] = coverage['unresolvedRows'] - count
        if result['unresolvedRows'] < 0 or (not result['unresolvedArticles'] and result['unresolvedRows']):
            raise ValueError('V6_WITNESS_MIRROR_PARTITION_COUNTS')
    return result


def audit(tracked, local=None, corpus=None):
    lock, lock_bytes = read_lock()
    index_raw = (DIRECTORY / 'articles.jsonl').read_bytes()
    if digest(index_raw) != ARTICLES_SHA256:
        raise ValueError('V6_WITNESS_ARTICLE_INDEX')
    index = list(map(json.loads, index_raw.splitlines()))
    rows, missing, summaries, seen, bound_receipts = [], [], {}, set(), []
    extended, archive_cases = {}, []
    for shard in lock['shards']:
        name = shard['name'].removesuffix('.parquet')
        directory = tracked / f'revision-witnesses-{name}'
        is_tracked = directory.exists()
        if local is not None and not is_tracked:
            directory = local / f'v6-revision-witnesses-{name}'
        if not directory.exists():
            missing.append(shard['name'])
            continue
        expected = {item['article']: item['partition'] for item in index if item['shard'] == shard['name']}
        shard_rows, revisions, summary, receipt = checked_shard(directory, shard, expected, digest(lock_bytes))
        if is_tracked or 'partitions' in receipt or 'corpusRowsSha256' in receipt:
            if 'partitions' not in receipt or 'corpusRowsSha256' not in receipt:
                raise ValueError('V6_WITNESS_RECEIPT_PARTITION_BINDING:' + shard['name'])
            bound_receipts.append((receipt, shard_rows))
        if seen.intersection(revisions):
            raise ValueError('V6_WITNESS_CROSS_SHARD_REVISION')
        seen.update(revisions)
        if is_tracked and shard['name'] in EXTENDED_HISTORY_SHA256:
            history = read_extended_history(directory, receipt, shard_rows)
            extended[history['article']] = history
        if is_tracked and shard['name'] in ARCHIVE_EXCEPTIONS_SHA256:
            archive_cases.extend(read_archive_exceptions(directory, receipt, shard_rows))
        rows.extend(shard_rows)
        summaries[shard['name']] = summary
    result = {'indexedArticles': len(index), 'missingShards': missing, 'shards': summaries,
              'checked': summarize(rows), 'partitions': {
                  part: summarize([row for row in rows if row['partition'] == part]) for part in PARTITIONS},
              'originalDumpRevisionIdsVerified': False, 'independentQualification': False}
    original = json.loads(CORPUS_RECEIPT.read_bytes())['originalFiles']
    for evidence in extended.values():
        revisions = {match['revid'] for match in evidence['matches']}
        if seen.intersection(revisions):
            raise ValueError('V6_WITNESS_CROSS_SHARD_REVISION')
        seen.update(revisions)
        seen.update(revisions)
        projection = evidence['corpusProjection']
        if projection['rowsSha256'] != original[projection['partition'] + '.jsonl']:
            raise ValueError('V6_WITNESS_EXTENDED_HISTORY_CORPUS_DIGEST')
    result['extendedHistoryArticles'] = sorted(extended, key=int)
    finewiki_path = tracked / FINEWIKI_RECEIPT
    canonical = tracked.resolve() == DIRECTORY.parent.resolve()
    finewiki = {}
    if finewiki_path.exists() or canonical:
        archive_missing = {row['article'] for row in archive_cases if row['status'] != 'full-source-window'}
        indexed_rows = {row['article']: row for row in rows}
        finewiki = read_finewiki_witnesses(finewiki_path, archive_missing - extended.keys(), indexed_rows, seen)
        result['fineWikiFullTextArticles'] = sorted(finewiki, key=int)
    result['byDateWitnessArticles'] = result['checked']['withMatchOnOrBeforeDumpDate'] + len(extended) + len(finewiki)
    corpus_rows = None
    if corpus is not None:
        new_matches = {article: evidence['matches'] for article, evidence in extended.items()}
        for article, witness in finewiki.items():
            new_matches[article] = [{'revid': witness['revision'], 'timestamp': witness['timestamp']}]
        resolved = [dict(row, status='content-match', matches=new_matches[row['article']])
                    if row['article'] in new_matches else row for row in rows]
        result['historicalCorpus'], corpus_rows = project_corpus(corpus, index, resolved, original)
        for article, evidence in extended.items():
            projection = evidence['corpusProjection']
            counts = count_corpus_rows([row for row in corpus_rows[projection['partition']]
                                        if row['article'] == article])
            if any(counts[key] != projection[key] for key in ('rows', 'contexts')):
                raise ValueError('V6_WITNESS_EXTENDED_HISTORY_PARTITION_COUNTS')
        for article, witness in finewiki.items():
            part = indexed_rows[article]['partition']
            if sum(row['article'] == article for row in corpus_rows[part]) != witness['rows']:
                raise ValueError('V6_WITNESS_FINEWIKI_PARTITION_COUNTS:' + article)
    for receipt, shard_rows in bound_receipts:
        verify_partition_binding(receipt, original, shard_rows, corpus_rows)
    result['archivePassages'] = archive_projection(archive_cases, corpus_rows)
    kiwix = tracked / KIWIX_RECEIPT
    if kiwix.exists() or canonical:
        archive_only = [row for row in result['archivePassages'] if row['article'] not in finewiki]
        coverage = kiwix_archive_coverage(kiwix, archive_only, original)
        mirror = tracked / MIRROR_RECEIPT
        if mirror.exists() or canonical:
            coverage = mirror_archive_coverage(mirror, rows, coverage, original, corpus_rows)
        result['archiveWindowCoverage'] = coverage
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local-root', type=Path, help='Directory with additional locally recovered shard reports')
    parser.add_argument('--corpus', type=Path, help='Directory with both exact restored v6 JSONL partitions')
    parser.add_argument('--require-all', action='store_true')
    args = parser.parse_args()
    result = audit(DIRECTORY.parent, args.local_root, args.corpus)
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.require_all and result['missingShards']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
