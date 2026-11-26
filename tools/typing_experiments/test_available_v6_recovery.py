"""Bind recovered v6 inputs to their original evidence."""
import ast
import bz2
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

import check_available_v6_calibration_index
import check_available_v6_rivals
import holdout_ledger
import recover_available_v6_calibration_attribution as attribution
from recover_role_training_groups import compiler_inputs, export_revision
from recover_v6_revision_witnesses import compare as compare_article_revisions, load_cleaner
from refit_historical_role_models import refit, verify_imports
from audit_available_v6_family_exposure import assignment_masks, noun_case_family_keys, refinement_families
from audit_available_v6_article_rows import partition_report
from check_v6_revision_witnesses import (
    CONTRIBUTOR_HISTORY_RECEIPT, CORPUS_RECEIPT, FINEWIKI_RECEIPT, KIWIX_RECEIPT, MIRROR_RECEIPT,
    audit as audit_article_witnesses,
    kiwix_archive_coverage, mirror_archive_coverage, project_attribution, project_corpus, read_finewiki_witnesses,
    verify_partition_binding, verify_rows,
)
from import_joint_history import MANIFESTS as JOINT_MANIFESTS
from import_recovered_rare_ranking import recover_windows
from import_recovered_v6_history import CONTEXTS, PREFIX as V6_HISTORY_PREFIX, checked_bytes, make_entry
from import_tatoeba_history import CC0_SPLITS
from recover_legacy_holdout import ORIGINAL as LEGACY_GENERATOR
from restore_final_available_v6 import assemble as assemble_final_v6
from restore_historical_tatoeba_cc0 import restore as restore_tatoeba_cc0

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / 'tools/typing_experiments/historical_provenance_sources/sentence_pairs_v2_v6_availability.json'
RECEIPT = ROOT / 'docs/acceptance/2026-10-27-right-context-numeric-bridge-evidence.json'
ORIGINAL_PATH = 'build/right-context-sentence-pairs-v2-v6-20261027/availability.json'
ORIGINAL_SHA256 = 'ea94b32ee61b828de62e7e4a4666a2b699031614e34fe77906d6fc3da1e92d83'
MANIFEST = FIXTURE.with_name('available_clean_v6_manifest.json')
MANIFEST_PATH = 'build/right-context-available-clean-v6-20261027/corpus/manifest.json'
MANIFEST_SHA256 = '63a96729330de3d36024ab6d062542bfeed0461d3b3d4202f820c74a30b90691'
IDENTITY_AUDIT = FIXTURE.with_name('available_clean_v6_identity_audit.json')
MODEL = ROOT / 'app/src/test/resources/right-context-model-parity/model.bin'


def find_values(obj, key):
    if isinstance(obj, dict):
        for k, value in obj.items():
            if k == key:
                yield value
            yield from find_values(value, key)
    elif isinstance(obj, list):
        for value in obj:
            yield from find_values(value, key)


class AvailableV6RecoveryTest(unittest.TestCase):
    def test_archived_holdout_window_is_bound_to_missing_page_without_full_article_claim(self):
        origin = ROOT / 'tools/typing_experiments/available-v6-article-origin-v1/revision-witnesses-0014'
        raw = (origin / 'articles.jsonl').read_bytes()
        receipt = json.loads((origin / 'archive-exceptions.json').read_bytes())
        self.assertEqual(hashlib.sha256(raw).hexdigest(), receipt['sourceShardArticlesSha256'])
        missing, = [row['article'] for row in map(json.loads, raw.splitlines()) if row['status'] == 'missing-page']
        capture, = receipt['archiveMetadata']['rows']
        check, = receipt['archivePassages']['checked']
        self.assertEqual(missing, capture['article'])
        self.assertEqual(missing, check['article'])
        self.assertEqual(capture['htmlSha256'], check['captureSha256'])
        self.assertEqual(capture['ids']['wgRevisionId'], check['displayedRevision'])
        self.assertEqual(4, check['rows'])
        self.assertTrue(check['fullWindowMatch'])
        self.assertFalse(receipt['archivePassages']['includesFullCleanedArticleCheck'])

    def test_translation_notice_overlap_with_revision_witnesses_binds_exact_row_counts(self):
        origin = ROOT / 'tools/typing_experiments/available-v6-article-origin-v1'
        outcome = json.loads((RECEIPT.parent / '2026-11-24-q6-v6-translation-witnesses-0011-0014.json').read_bytes())
        self.assertEqual(hashlib.sha256((origin / 'recovered/articles.jsonl').read_bytes()).hexdigest(),
                         outcome['pageIndexSha256'])
        self.assertEqual({f'{shard:04d}.parquet' for shard in range(11, 15)}, set(outcome['witnessShards']))
        captured = set()
        for shard, digest in outcome['witnessShards'].items():
            source = (origin / f'revision-witnesses-{shard[:4]}' / 'articles.jsonl').read_bytes()
            self.assertEqual(digest, hashlib.sha256(source).hexdigest())
            captured.update(row['article'] for row in map(json.loads, source.splitlines())
                            if any(match['timestamp'] <= '2023-11-01T23:59:59Z' for match in row['matches']))
        for part in ('calibration', 'holdout'):
            notice = (origin / f'{part}-attribution' / 'translation-sources.json').read_bytes()
            evidence = outcome['partitions'][part]
            self.assertEqual(hashlib.sha256(notice).hexdigest(), evidence['translationReceiptSha256'])
            flagged = {str(row['article']) for row in json.loads(notice)['articles']}
            index = (origin / f'{part}-recovery' / 'source-index.jsonl').read_bytes()
            self.assertEqual(hashlib.sha256(index).hexdigest(), json.loads(notice)['sourceIndexSha256'])
            for label, ids in (('noticeScope', flagged), ('noticeAndFullContentWitness', flagged & captured)):
                rows = [row for row in map(json.loads, index.splitlines()) if row['article'] in ids]
                self.assertEqual(ids, {row['article'] for row in rows})
                self.assertEqual({'articles': len(ids), 'contexts': len(rows),
                                  'rows': sum(row['rows'] for row in rows)}, evidence[label])
        self.assertFalse(outcome['passageLevelOriginsReviewed'])
        self.assertFalse(outcome['distributionRightsReviewed'])

    def test_archived_v6_passage_leads_do_not_replace_missing_full_text_witnesses(self):
        origin = ROOT / 'tools/typing_experiments/available-v6-article-origin-v1/revision-witnesses-0013'
        raw = (origin / 'articles.jsonl').read_bytes()
        exceptions = json.loads((origin / 'archive-exceptions.json').read_bytes())
        self.assertEqual(hashlib.sha256(raw).hexdigest(), exceptions['sourceShardArticlesSha256'])
        missing = {row['article'] for row in map(json.loads, raw.splitlines()) if row['status'] == 'missing-page'}
        archive = exceptions['archiveMetadata']
        self.assertEqual(missing, {row['article'] for row in archive['rows']})
        self.assertTrue(all(row['pageIdentityMatches'] for row in archive['rows']))
        displayed = {row['article'] for row in archive['rows'] if row['ids']['wgRevisionId'] > 0}
        passage = exceptions['archivePassages']
        self.assertEqual(displayed, {row['article'] for row in passage['checked']})
        self.assertEqual(2, len(displayed))
        self.assertTrue(all(row['rightMatch'] and not row['fullWindowMatch'] for row in passage['checked']))
        self.assertFalse(passage['exactSnapshotRevisionProven'])
        self.assertFalse(passage['publicationRightsReviewed'])

    def test_witness_projection_binds_exact_corpus_and_counts_unchecked_and_missing_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entries = [('12', 'calibration', 'a'), ('12', 'calibration', 'a'),
                       ('14', 'calibration', 'b'), ('16', 'calibration', 'c'),
                       ('18', 'calibration', 'd'), ('20', 'holdout', 'e')]
            index = [dict(article=article, partition=part) for article, part, _ in entries]
            original = {}
            for part in ('calibration', 'holdout'):
                name = part + '.jsonl'
                raw = ''.join(json.dumps(dict(article=article, part=part, contextHash=context)) + '\n'
                              for article, split, context in entries if split == part).encode()
                (root / name).write_bytes(raw)
                original[name] = hashlib.sha256(raw).hexdigest()
            witnesses = [dict(article='12', status='content-match', matches=[dict(timestamp='2023-11-01T00:01:00Z')]),
                         dict(article='14', status='missing-page', matches=[]),
                         dict(article='18', status='content-match', matches=[dict(timestamp='2023-11-02T00:01:00Z')])]
            result, corpus_rows = project_corpus(root, index, witnesses, original)
            statuses = result['calibration']['statuses']
            self.assertEqual({'rows': 2, 'contexts': 1, 'articles': 1}, statuses['content-match-by-dump-date'])
            for status in ('missing-page', 'not-checked', 'content-match-after-dump-date'):
                self.assertEqual({'rows': 1, 'contexts': 1, 'articles': 1}, statuses[status])
            self.assertEqual(1, result['holdout']['statuses']['not-checked']['rows'])
            self.assertEqual([
                {'article': '14', 'status': 'missing-page', 'rows': 1, 'contexts': 1},
                {'article': '18', 'status': 'content-match-after-dump-date', 'rows': 1, 'contexts': 1},
            ], result['calibration']['checkedExceptions'])
            self.assertEqual([], result['holdout']['checkedExceptions'])
            (root / 'holdout.jsonl').write_bytes(b'[]')
            with self.assertRaisesRegex(ValueError, 'V6_WITNESS_CORPUS_DIGEST:holdout'):
                project_corpus(root, index, witnesses, original)

            receipt = {
                'sourceShard': '0016.parquet',
                'corpusRowsSha256': {part: original[part + '.jsonl'] for part in ('calibration', 'holdout')},
                'partitions': {
                    'calibration': dict(indexedArticles=3, indexedRows=4, indexedContexts=3,
                                        withMatchOnOrBeforeDumpDate=1, witnessedRows=2, witnessedContexts=1),
                    'holdout': dict(indexedArticles=0, indexedRows=0, indexedContexts=0,
                                    withMatchOnOrBeforeDumpDate=0, witnessedRows=0, witnessedContexts=0),
                },
            }
            shard_rows = [dict(row, partition='calibration') for row in witnesses]
            verify_partition_binding(receipt, original, shard_rows, corpus_rows)
            receipt['partitions']['calibration']['witnessedRows'] += 1
            with self.assertRaisesRegex(ValueError, 'V6_WITNESS_RECEIPT_PARTITION_COUNTS:0016.parquet'):
                verify_partition_binding(receipt, original, shard_rows, corpus_rows)

    def test_tracked_v6_witness_receipt_refuses_changed_corpus_digest_without_corpus_files(self):
        origin = ROOT / 'tools/typing_experiments/available-v6-article-origin-v1/revision-witnesses-0016'
        with tempfile.TemporaryDirectory() as directory:
            tracked = Path(directory)
            shard = tracked / origin.name
            shard.mkdir()
            for name in ('articles.jsonl', 'archive-exceptions.json'):
                (shard / name).symlink_to(origin / name)
            receipt = json.loads((origin / 'receipt.json').read_bytes())
            receipt['corpusRowsSha256']['holdout'] = '0' * 64
            (shard / 'receipt.json').write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, 'V6_WITNESS_RECEIPT_CORPUS_DIGEST:0016.parquet'):
                audit_article_witnesses(tracked)

    def test_revision_witness_coverage_reports_missing_shards_and_validates_index(self):
        origin = ROOT / 'tools/typing_experiments/available-v6-article-origin-v1'
        with tempfile.TemporaryDirectory() as directory:
            tracked = Path(directory)
            for name in ('revision-witnesses-0011', 'revision-witnesses-0012'):
                (tracked / name).symlink_to(origin / name, target_is_directory=True)
            result = audit_article_witnesses(tracked)
        self.assertEqual(3265, result['indexedArticles'])
        self.assertEqual(647, result['checked']['withMatchOnOrBeforeDumpDate'])
        self.assertEqual(434, result['checked']['multipleMatches'])
        self.assertEqual([f'{number:04d}.parquet' for number in range(13, 21)], result['missingShards'])
        self.assertFalse(result['originalDumpRevisionIdsVerified'])

    def test_attribution_links_public_matching_revision_and_keeps_archive_only_gap(self):
        older = {'revid': 10, 'timestamp': '2023-10-31T08:00:00Z'}
        matching = {'revid': 11, 'timestamp': '2023-11-01T08:00:00Z'}
        later = {'revid': 12, 'timestamp': '2023-11-02T08:00:00Z'}
        pages = [
            {'article': '1', 'partition': 'calibration', 'status': 'content-match', 'matches': [older, later, matching]},
            {'article': '2', 'partition': 'holdout', 'status': 'content-match', 'matches': [older]},
            {'article': '3', 'partition': 'holdout', 'status': 'missing-page', 'matches': []},
        ]
        corpus = {'calibration': [{'article': '1'}] * 2, 'holdout': [{'article': '2'}, {'article': '3'}]}
        original = {'calibration.jsonl': 'calibration-digest', 'holdout.jsonl': 'holdout-digest'}
        finewiki = {'2': {'revision': older['revid'], 'timestamp': older['timestamp']}}
        report = project_attribution(pages, finewiki, corpus, original)
        self.assertEqual(2, report['linkedRows'])
        self.assertEqual(2, report['unlinkedRows'])
        self.assertEqual(matching, report['articles']['1']['matchingRevision'])
        self.assertEqual('https://ru.wikipedia.org/w/index.php?oldid=11', report['articles']['1']['revisionUrl'])
        self.assertEqual(older, report['articles']['2']['matchingRevision'])
        self.assertNotIn('revisionUrl', report['articles']['2'])
        self.assertNotIn('revisionUrl', report['articles']['3'])
        self.assertFalse(report['publicationRightsReviewed'])
        with self.assertRaisesRegex(ValueError, 'V6_ATTRIBUTION_PARTITION_COVERAGE'):
            project_attribution(pages[:-1], finewiki, corpus, original)

    def test_attribution_adds_pinned_archive_credits_without_a_live_revision_link(self):
        origin = ROOT / 'tools/typing_experiments/available-v6-article-origin-v1'
        path = origin / CONTRIBUTOR_HISTORY_RECEIPT
        archive = json.loads(path.read_bytes())
        pages = [dict(record, status='missing-page', matches=[]) for record in archive['articles']]
        corpus = {'calibration': [{'article': '7795183'}] * 5 + [{'article': '8402514'}] * 5, 'holdout': []}
        original = {'calibration.jsonl': 'calibration-digest', 'holdout.jsonl': 'holdout-digest'}
        report = project_attribution(pages, {}, corpus, original, path)
        self.assertEqual(10, report['archivedContributorHistory']['rows'])
        self.assertEqual(0, report['linkedArticles'])
        self.assertEqual(132871704, report['articles']['7795183']['contributorArchive']['matchingRevisions'][-1]['revid'])
        pages[0]['snapshotTextSha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'V6_ATTRIBUTION_CONTRIBUTOR_HISTORY_BINDING'):
            project_attribution(pages, {}, corpus, original, path)

    def test_extended_v6_witness_counts_only_the_pinned_recovery(self):
        origin = ROOT / 'tools/typing_experiments/available-v6-article-origin-v1/revision-witnesses-0017'
        with tempfile.TemporaryDirectory() as directory:
            tracked = Path(directory)
            shard = tracked / origin.name
            shard.mkdir()
            for name in ('articles.jsonl', 'receipt.json', 'archive-exceptions.json'):
                (shard / name).symlink_to(origin / name)
            path = shard / 'extended-history.json'
            evidence = json.loads((origin / path.name).read_bytes())
            path.write_bytes((origin / path.name).read_bytes())
            result = audit_article_witnesses(tracked)
            self.assertEqual(349, result['checked']['withMatchOnOrBeforeDumpDate'])
            self.assertEqual(350, result['byDateWitnessArticles'])
            self.assertEqual(['8122520'], result['extendedHistoryArticles'])
            evidence['matches'][0]['revid'] += 1
            path.write_text(json.dumps(evidence))
            with self.assertRaisesRegex(ValueError, 'V6_WITNESS_EXTENDED_HISTORY_DIGEST:0017.parquet'):
                audit_article_witnesses(tracked)

    def test_v6_archive_windows_preserve_missing_full_articles_and_reject_edits(self):
        origin = ROOT / 'tools/typing_experiments/available-v6-article-origin-v1/revision-witnesses-0018'
        with tempfile.TemporaryDirectory() as directory:
            tracked = Path(directory)
            shard = tracked / origin.name
            shard.mkdir()
            for name in ('articles.jsonl', 'receipt.json'):
                (shard / name).symlink_to(origin / name)
            path = shard / 'archive-exceptions.json'
            raw = (origin / path.name).read_bytes()
            path.write_bytes(raw)
            result = audit_article_witnesses(tracked)
            self.assertEqual(340, result['byDateWitnessArticles'])
            self.assertEqual(3, result['checked']['statusCounts']['missing-page'])
            self.assertEqual({'page-identity-mismatch': 1, 'full-source-window': 2},
                             dict(Counter(row['status'] for row in result['archivePassages'])))
            path.write_bytes(raw + b'\n')
            with self.assertRaisesRegex(ValueError, 'V6_WITNESS_ARCHIVE_DIGEST:0018.parquet'):
                audit_article_witnesses(tracked)

    def test_kiwix_windows_extend_coverage_without_counting_full_article_witnesses(self):
        origin = ROOT / 'tools/typing_experiments/available-v6-article-origin-v1'
        result = audit_article_witnesses(origin)
        self.assertEqual(3241, result['byDateWitnessArticles'])
        self.assertEqual(['8402514', '8441629'], result['fineWikiFullTextArticles'])
        coverage = result['archiveWindowCoverage']
        self.assertEqual(13, coverage['kiwixWitnessedArticles'])
        self.assertEqual(64, coverage['kiwixWitnessedRows'])
        self.assertEqual(1, coverage['mirrorWitnessedArticles'])
        self.assertEqual(5, coverage['mirrorWitnessedRows'])
        self.assertEqual([], coverage['unresolvedArticles'])
        self.assertFalse(result['originalDumpRevisionIdsVerified'])
        self.assertNotIn('unresolvedRows', coverage)

        receipt = origin / KIWIX_RECEIPT
        original = json.loads(CORPUS_RECEIPT.read_bytes())['originalFiles']
        projected = [dict(row, rows=1) for row in result['archivePassages']]
        with self.assertRaisesRegex(ValueError, 'V6_WITNESS_KIWIX_PARTITION_COUNTS'):
            kiwix_archive_coverage(receipt, projected, original)
        with tempfile.TemporaryDirectory() as directory:
            mutant = Path(directory) / receipt.name
            mutant.write_bytes(receipt.read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'V6_WITNESS_KIWIX_DIGEST'):
                kiwix_archive_coverage(mutant, result['archivePassages'], original)
            finewiki = Path(directory) / FINEWIKI_RECEIPT
            finewiki.write_bytes((origin / FINEWIKI_RECEIPT).read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'V6_WITNESS_FINEWIKI_DIGEST'):
                read_finewiki_witnesses(finewiki, set(), {}, set())
            mirror = Path(directory) / MIRROR_RECEIPT
            mirror.write_bytes((origin / MIRROR_RECEIPT).read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'V6_WITNESS_MIRROR_DIGEST'):
                mirror_archive_coverage(mirror, [], coverage, original, None)

    def test_mirror_window_proof_rejects_an_inconsistent_corpus_projection(self):
        origin = ROOT / 'tools/typing_experiments/available-v6-article-origin-v1'
        path = origin / MIRROR_RECEIPT
        original = json.loads(CORPUS_RECEIPT.read_bytes())['originalFiles']
        index = [json.loads(line) for line in
                 (origin / 'revision-witnesses-0020/articles.jsonl').read_text().splitlines()]
        coverage = {'unresolvedArticles': ['10355886'], 'unresolvedRows': 5}

        with self.assertRaisesRegex(ValueError, 'V6_WITNESS_MIRROR_CORPUS_WINDOWS'):
            mirror_archive_coverage(path, index, coverage, original, {'holdout': []})
        with self.assertRaisesRegex(ValueError, 'V6_WITNESS_MIRROR_PARTITION_COUNTS'):
            mirror_archive_coverage(path, index, dict(coverage, unresolvedRows=6), original, None)

    def test_revision_witness_verifier_refuses_page_reassignment_and_duplicate_revision(self):
        row = dict(article='12', partition='calibration', snapshotTextSha256='a' * 64,
                   comparedRevisions=1, matches=[dict(revid=1, timestamp='2023-11-01T01:00:00Z')],
                   status='content-match', hasEarlierContinuation=False)
        next_page = dict(row, article='14')
        with self.assertRaisesRegex(ValueError, 'V6_WITNESS_PAGE_IDENTITY'):
            verify_rows([row], {'12': 'holdout'}, 'test')
        with self.assertRaisesRegex(ValueError, 'V6_WITNESS_REVISION_IDENTITY'):
            verify_rows([row, next_page], {'12': 'calibration', '14': 'calibration'}, 'test')
        with self.assertRaisesRegex(ValueError, 'V6_WITNESS_INDEX_COVERAGE'):
            verify_rows([row], {'12': 'calibration', '14': 'calibration'}, 'test')

    def test_revision_witnesses_keep_multiple_matches_and_distinguish_missing_pages(self):
        def revision(revid, timestamp, content):
            return {'revid': revid, 'timestamp': timestamp, 'slots': {'main': {'content': content}}}

        revisions = [revision(4, '2023-11-02T17:00:00Z', 'changed'),
                     revision(3, '2023-11-01T13:00:00Z', ' match '),
                     revision(2, '2023-11-01T01:00:00Z', 'match'),
                     revision(1, '2023-10-31T00:00:00Z', None)]
        response = {'query': {'pages': [{'pageid': 15, 'revisions': revisions}]}, 'continue': {}}
        result = compare_article_revisions('15', 'holdout', b'match', response, str.strip)
        self.assertEqual('content-match', result['status'])
        self.assertEqual([3, 2], [witness['revid'] for witness in result['matches']])
        self.assertEqual(3, result['comparedRevisions'])
        self.assertTrue(result['hasEarlierContinuation'])
        self.assertEqual('no-content-match', compare_article_revisions(
            '15', 'holdout', b'other', response, str.strip)['status'])
        missing = {'query': {'pages': [{'pageid': 15, 'missing': True}]}}
        self.assertEqual('missing-page', compare_article_revisions(
            '15', 'holdout', b'match', missing, str.strip)['status'])
        with self.assertRaisesRegex(ValueError, 'V6_REVISION_PAGE_IDENTITY'):
            compare_article_revisions('99', 'holdout', b'match', response, str.strip)
        revisions[0]['timestamp'] = '2023-11-04T00:00:00Z'
        with self.assertRaisesRegex(ValueError, 'V6_REVISION_CANDIDATE_IDENTITY'):
            compare_article_revisions('15', 'holdout', b'match', response, str.strip)
        with self.assertRaisesRegex(ValueError, 'V6_REVISION_CLEANER_IDENTITY'):
            load_cleaner(b'altered cleaner')

    def test_available_v6_first_revision_shard_preserves_all_matching_witnesses(self):
        origin = ROOT / 'tools/typing_experiments/available-v6-article-origin-v1'
        fixture = origin / 'revision-witnesses-0011'
        receipt = json.loads((fixture / 'receipt.json').read_bytes())
        source = (origin / 'recovered/articles.jsonl').read_bytes()
        contents = (fixture / 'articles.jsonl').read_bytes()
        self.assertEqual(hashlib.sha256(source).hexdigest(), receipt['sourceIndexSha256'])
        self.assertEqual(hashlib.sha256(contents).hexdigest(), receipt['articlesSha256'])
        rows = list(map(json.loads, contents.splitlines()))
        keys = [(item['article'], item['partition']) for item in rows]
        self.assertCountEqual(keys, [(item['article'], item['partition']) for item in map(json.loads, source.splitlines())
                                    if item['shard'] == receipt['sourceShard']])
        pilot_bytes = (RECEIPT.parent / '2026-11-24-q6-v6-revision-content-pilot.json').read_bytes()
        self.assertEqual(hashlib.sha256(pilot_bytes).hexdigest(), receipt['pilotReceiptSha256'])
        by_article = {item['article']: item for item in rows}
        for row in json.loads(pilot_bytes)['rows']:
            self.assertEqual(row, by_article[row['article']])
        self.assertEqual(355, len(rows))
        self.assertEqual(2816, sum(row['comparedRevisions'] for row in rows))
        self.assertEqual(947, sum(len(row['matches']) for row in rows))
        self.assertEqual(229, sum(len(row['matches']) > 1 for row in rows))
        self.assertTrue(all(any(revision['timestamp'] <= receipt['dumpDateCutoff'] for revision in row['matches'])
                            for row in rows))
        self.assertEqual(0, receipt['unavailableRequests'])
        self.assertFalse(receipt['originalDumpRevisionIdsVerified'])
        self.assertFalse(receipt['independentQualification'])

    def test_available_v6_second_revision_shard_matches_the_original_index(self):
        origin = ROOT / 'tools/typing_experiments/available-v6-article-origin-v1'
        fixture = origin / 'revision-witnesses-0012'
        receipt = json.loads((fixture / 'receipt.json').read_bytes())
        source = (origin / 'recovered/articles.jsonl').read_bytes()
        raw = (fixture / 'articles.jsonl').read_bytes()
        self.assertEqual(hashlib.sha256(source).hexdigest(), receipt['sourceIndexSha256'])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), receipt['articlesSha256'])
        rows = list(map(json.loads, raw.splitlines()))
        expected = [(row['article'], row['partition']) for row in map(json.loads, source.splitlines())
                    if row['shard'] == '0012.parquet']
        self.assertCountEqual(expected, [(row['article'], row['partition']) for row in rows])
        self.assertEqual(292, len(rows))
        self.assertEqual(794, sum(len(row['matches']) for row in rows))
        self.assertEqual(205, sum(len(row['matches']) > 1 for row in rows))
        self.assertTrue(all(any(match['timestamp'] <= receipt['dumpDateCutoff'] for match in row['matches'])
                            for row in rows))
        self.assertEqual(0, receipt['unavailableRequests'])
        self.assertFalse(receipt['originalDumpRevisionIdsVerified'])

    def test_available_v6_revision_pilot_binds_sample_and_records_ambiguity(self):
        origin = ROOT / 'tools/typing_experiments/available-v6-article-origin-v1'
        source = (origin / 'recovered/articles.jsonl').read_bytes()
        lock = (origin / 'source-lock.json').read_bytes()
        pilot = json.loads((RECEIPT.parent / '2026-11-24-q6-v6-revision-content-pilot.json').read_bytes())
        self.assertEqual(hashlib.sha256(source).hexdigest(), pilot['sourceIndexSha256'])
        self.assertEqual(hashlib.sha256(lock).hexdigest(), pilot['sourceLockSha256'])
        shard, = [entry for entry in json.loads(lock)['shards'] if entry['name'] == pilot['sourceShard']]
        self.assertEqual(shard['sha256'], pilot['sourceShardSha256'])
        records = list(map(json.loads, source.splitlines()))
        for part in ('calibration', 'holdout'):
            candidates = [row['article'] for row in records
                          if row['partition'] == part and row['shard'] == shard['name']]
            sampled = sorted(candidates, key=lambda article: hashlib.sha256(
                ('rune-v6-revision-pilot-v1:' + article).encode()).digest())[:16]
            self.assertCountEqual(sampled, [row['article'] for row in pilot['rows'] if row['partition'] == part])
        for row in pilot['rows']:
            self.assertEqual('content-match', row['status'])
            self.assertEqual(8, row['comparedRevisions'])
            self.assertTrue(row['matches'])
            self.assertTrue(all(match['timestamp'] <= pilot['apiUpperBound'] for match in row['matches']))
        self.assertEqual(76, sum(len(row['matches']) for row in pilot['rows']))
        self.assertEqual(16, sum(len(row['matches']) > 1 for row in pilot['rows']))
        self.assertFalse(pilot['originalDumpRevisionIdsVerified'])
        self.assertFalse(pilot['independentQualification'])

    def test_exact_v6_article_overlap_counts_contexts_and_rows_separately(self):
        part = 'calibration'
        rows = [dict(article=article, part=part, split=part, contextHash=context, group=group)
                for article, context, group in [('12', 'a', 'correct'), ('12', 'a', 'typo'),
                                                 ('12', 'b', 'correct'), ('34', 'c', 'correct')]]
        data = '\n'.join(map(json.dumps, rows)).encode()
        sha = hashlib.sha256(data).hexdigest()
        keys = holdout_ledger.keys_for(rows, 'article')
        blocked = holdout_ledger.keys_for([rows[0]], 'article')
        scopes = {'recorded': blocked, 'empty': set()}
        result = partition_report(part, data, sha, keys, scopes)
        self.assertEqual({'articles': 1, 'contexts': 2, 'rows': 3,
                          'groups': {'correct': 2, 'typo': 1}}, result['recorded'])
        self.assertEqual({'articles': 0, 'contexts': 0, 'rows': 0, 'groups': {}}, result['empty'])
        with self.assertRaisesRegex(ValueError, 'V6_ARTICLE_ROWS_INPUT:calibration'):
            partition_report(part, data + b'\n', sha, keys, scopes)
        with self.assertRaisesRegex(ValueError, 'V6_ARTICLE_ROWS_LEDGER_BINDING:calibration'):
            partition_report(part, data, sha, blocked, scopes)
        with self.assertRaisesRegex(ValueError, 'V6_ARTICLE_ROWS_PARTITION:holdout'):
            partition_report('holdout', data, sha, keys, scopes)

    def test_rare_ranking_windows_refuse_ambiguous_or_missing_source(self):
        jobs = [('holdout', [{'article': '1', 'word': 'книга', 'prefix': 'префикс'}], 1, {})]
        generator = SimpleNamespace(bounded_prefix=lambda _: 'префикс')
        windows = recover_windows(jobs, [([1], ['книга на столе'])], generator)
        self.assertEqual(1, len(next(iter(windows.values()))))
        with self.assertRaisesRegex(ValueError, 'RARE_RANKING_MISSING_ARTICLE'):
            recover_windows(jobs, [([2], ['книга на столе'])], generator)
        with self.assertRaisesRegex(ValueError, 'RARE_RANKING_AMBIGUOUS_WINDOW'):
            recover_windows(jobs, [([1], ['книга на столе. книга лежит дома'])], generator)

    def test_recovered_ancestry_entries_keep_source_bindings_and_declared_axes(self):
        ledger = holdout_ledger.load_ledger(ROOT / 'tools/typing_experiments/holdout-ledger.json')
        entries = {entry['id'].removeprefix(V6_HISTORY_PREFIX): entry for entry in ledger['entries']
                   if entry['id'].startswith(V6_HISTORY_PREFIX)}
        archive = FIXTURE.parent / 'v6-inputs'
        parent = json.loads((archive / 'sentence-pairs-v2-v6-plan.json').read_bytes())
        clean = json.loads((archive / 'available-clean-v6-plan.json').read_bytes())
        self.assertFalse(ledger['coverage']['complete'])
        for name, count in CONTEXTS.items():
            entry = entries[name]
            origin = f'build/right-context-{name}-20261027/contexts.unqualified.jsonl'
            expected = (clean['recordsSha256'] if name == 'sentence-pairs-v2-v6'
                        else parent['additionalArticleBindings'][origin])
            self.assertEqual(expected, entry['bindings'][origin])
            self.assertEqual(count, entry['rowCount'])
            self.assertEqual(set(holdout_ledger.KINDS), entry['keys'].keys())
            self.assertEqual([], entry['missingAxes'])
        for part in ('calibration', 'holdout'):
            entry = entries['diagnostic-rare-ranking-' + part]
            origin = f'build/diagnostic-rare-ranking/fresh-corpus/{part}.jsonl'
            self.assertEqual(parent['exclusionBindings'][origin], entry['bindings'][origin])
            self.assertEqual({'article', 'context'}, entry['keys'].keys())
            self.assertEqual(['family', 'sentence'], entry['missingAxes'])

    def test_recovered_ancestry_refuses_mutated_input_and_wrong_count(self):
        raw = b'historical'
        digest = hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'corpus.jsonl'
            path.write_bytes(raw)
            self.assertEqual(raw, checked_bytes(path, digest))
            path.write_bytes(raw + b'\n')
            with self.assertRaisesRegex(ValueError, 'V6_HISTORY_DIGEST'):
                checked_bytes(path, digest)
        with self.assertRaisesRegex(ValueError, 'V6_HISTORY_ROW_COUNT'):
            make_entry('synthetic', [], 1, ('article',), {'source': digest})

    def test_detailed_tatoeba_preparers_preserve_the_packed_family_source(self):
        directory = FIXTURE.parent / 'v6-inputs'
        proof = json.loads((directory / 'tatoeba-detailed-preparer-recovery.json').read_bytes())
        bindings = json.loads((directory / 'sentence-pairs-v2-v6-plan.json').read_bytes())['exclusionBindings']
        self.assertEqual(5, len(proof['sourceBodies']))
        self.assertEqual(3, sum(record['historicalDigestObservedAt'] is not None
                                for record in proof['sourceBodies'].values()))
        self.assertEqual('packed-morphology-id', proof['declaredFamilyKind'])
        direct = {}
        for record in proof['sourceBodies'].values():
            raw = (directory.parent / record['archivedSource']).read_bytes()
            self.assertEqual(record['sha256'], hashlib.sha256(raw).hexdigest())
            tree = ast.parse(raw)
            assignments = {ast.unparse(node.value) for node in ast.walk(tree) if isinstance(node, ast.Assign)
                           and any(isinstance(target, ast.Name) and target.id == 'family' for target in node.targets)}
            self.assertEqual({'lemmas.get(word)'}, assignments)
            self.assertTrue(any(isinstance(node, ast.Call) and ast.unparse(node.func) == 'j.morphology'
                                for node in ast.walk(tree)))
            direct.update(record['files'])
        self.assertEqual(9, len(direct))
        for path, digest in direct.items():
            self.assertEqual(bindings[path], digest)
        self.assertEqual(4, len(proof['duplicateCorpusBindings']))
        for alias, original in proof['duplicateCorpusBindings'].items():
            self.assertEqual(direct[original], bindings[alias])

    def test_final_v6_recovery_binds_original_parent_plan_outputs_and_source(self):
        archive = FIXTURE.parent / 'v6-inputs'
        receipt = json.loads((RECEIPT.parent / '2026-11-24-q6-final-v6-recovery.json').read_bytes())
        evidence = json.loads(RECEIPT.read_bytes())['bindings']
        manifest = json.loads(MANIFEST.read_bytes())
        parent = (archive / 'sentence-pairs-v2-v6-plan.json').read_bytes()
        plan_raw = (archive / 'available-clean-v6-plan.json').read_bytes()
        plan = json.loads(plan_raw)
        availability = json.loads(FIXTURE.read_bytes())
        self.assertEqual(manifest['planSha256'], hashlib.sha256(plan_raw).hexdigest())
        self.assertEqual({**manifest['files'], 'plan.json': manifest['planSha256']},
                         receipt['originalFiles'])
        self.assertEqual(len(json.loads(parent)['sourceBindings']), receipt['sourceShards'])
        for key in ('scannedArticles', 'eligibleArticles', 'blockedArticles'):
            self.assertEqual(availability[key], receipt[key])
        self.assertEqual(hashlib.sha256(parent).hexdigest(), plan['parentPlanSha256'])
        self.assertEqual(receipt['parentPlanSha256'], plan['parentPlanSha256'])
        self.assertEqual(receipt['parentRecordsSha256'], plan['recordsSha256'])
        self.assertEqual(receipt['parentAvailabilitySha256'], plan['failedAvailabilitySha256'])
        self.assertEqual(evidence[ORIGINAL_PATH], plan['failedAvailabilitySha256'])
        self.assertEqual(receipt['originalCleanPreparerSha256'], plan['scriptSha256'])
        source = FIXTURE.with_name('available_clean_v6_reconstructed.py')
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), plan['scriptSha256'])
        exclusions = json.loads(FIXTURE.with_name('available_clean_v6_prior_context_exclusions.json').read_bytes())
        for part, counts in receipt['counts'].items():
            self.assertEqual(availability['parts'][part]['contexts'], counts['parentContexts'])
            self.assertEqual(exclusions[part]['keptRows'], counts['rows'])
            self.assertEqual(counts['parentContexts'] - len(exclusions[part]['removedContextHashes']),
                             counts['contexts'])
        self.assertEqual({'calibration', 'holdout'}, set(receipt['counts']))
        self.assertEqual(0, receipt['modelCalls'])
        self.assertEqual(0, plan['modelCalls'])
        self.assertFalse(plan['fullCohortGatePassed'])
        self.assertFalse(plan['holdoutScoringAllowed'])
        self.assertFalse(receipt['independentQualification'])

    def test_final_assembly_keeps_original_ids_when_exclusions_remove_variants(self):
        item = dict(word='книга', typed='книа', rival=None, part='holdout', prefix='эта',
                    rightContext=' была на столе', familyExposure='previously_bound')
        first = dict(item, contextHash='a' * 64, rival='книги')
        second = dict(item, contextHash='b' * 64)
        parent = '\n'.join(map(json.dumps, (first, second))).encode()
        exclusions = {'calibration': dict(originalRows=0, keptRows=0, removedRows=0, removedContextHashes=[]),
                      'holdout': dict(originalRows=9, keptRows=4, removedRows=5, removedContextHashes=['a' * 64])}
        files = assemble_final_v6(parent, exclusions)
        rows = [json.loads(line) for line in files['holdout.jsonl'].splitlines()]
        self.assertEqual([f'available-v6-holdout-{i:06d}' for i in range(5, 9)], [row['id'] for row in rows])
        self.assertEqual(['typo', 'unfinished', 'correct', 'protected'], [row['group'] for row in rows])
        self.assertEqual([b'0', b'1', b'2', b'3'], [line.split(b'\t')[0] for line in files['holdout.tsv'].splitlines()])
        with self.assertRaisesRegex(ValueError, 'FINAL_V6_EXCLUSIONS:holdout'):
            assemble_final_v6(json.dumps(second).encode(), exclusions)

    def test_final_assembly_rejects_duplicate_context_and_unverified_exposure(self):
        items = [dict(part='holdout', contextHash='a' * 64, familyExposure=None),
                 dict(part='holdout', contextHash='a' * 64, familyExposure='previously_bound')]
        exclusions = {part: dict(removedContextHashes=['a' * 64]) for part in ('calibration', 'holdout')}
        with self.assertRaisesRegex(ValueError, 'FINAL_V6_CONTEXT'):
            assemble_final_v6(json.dumps(items[0]).encode(), exclusions)
        records = '\n'.join(map(json.dumps, [dict(items[1], rival=None)] * 2)).encode()
        with self.assertRaisesRegex(ValueError, 'FINAL_V6_CONTEXT'):
            assemble_final_v6(records, exclusions)

    def test_early_wikipedia_context_feature_rows_match_original_bindings(self):
        directory = FIXTURE.parent / 'v6-inputs'
        proof = json.loads((directory / 'early-wikipedia-context-feature-recovery.json').read_bytes())
        earlier = ROOT / 'docs/acceptance/2026-10-27-legacy-context-history-evidence.json'
        earlier_receipt = json.loads(earlier.read_bytes())['receipt']
        parent = json.loads((directory / 'sentence-pairs-v2-v6-plan.json').read_bytes())
        source = (directory.parent / 'context_feature_wikipedia_preparer.py').read_bytes()
        self.assertEqual(hashlib.sha256(source).hexdigest(), proof['archivedPreparerSha256'])
        self.assertFalse(proof['independentOriginalSourceDigestAvailable'])
        for part, count in proof['rows'].items():
            name = part + '.jsonl'
            path = proof['originalRoot'] + '/' + name
            self.assertEqual(earlier_receipt['counts']['context-feature/' + part]['rows'], count)
            self.assertEqual(earlier_receipt['bindings'][path], proof['files'][name])
            self.assertEqual(parent['exclusionBindings'][path], proof['files'][name])
        self.assertEqual({'calibration': 3563, 'holdout': 5906}, proof['rows'])
        self.assertEqual('packed-morphology-id', proof['declaredFamilyKind'])
        manifest_path = proof['originalRoot'] + '/manifest.json'
        manifest_raw = (directory / 'early-wikipedia-context-feature-manifest.json').read_bytes()
        self.assertEqual(earlier_receipt['bindings'][manifest_path], hashlib.sha256(manifest_raw).hexdigest())
        manifest = json.loads(manifest_raw)
        self.assertEqual(proof['files'], manifest['files'])
        self.assertEqual(proof['rows'], {part: data['rows'] for part, data in manifest['counts'].items()})
        self.assertEqual(earlier_receipt['bindings']['build/joint-correction-20261025/0020.parquet'],
                         manifest['sourceSha256'])
        self.assertEqual(28, len(manifest['priorRows']))
        for path, digest in manifest['priorRows'].items():
            self.assertEqual(parent['exclusionBindings'][path], digest)

    def test_early_wikipedia_word_context_manifests_and_sources_match_bindings(self):
        directory = FIXTURE.parent / 'v6-inputs'
        proof = json.loads((directory / 'early-wikipedia-word-context-recovery.json').read_bytes())
        earlier = ROOT / 'docs/acceptance/2026-10-27-legacy-context-history-evidence.json'
        receipt = json.loads(earlier.read_bytes())['receipt']
        parent = json.loads((directory / 'sentence-pairs-v2-v6-plan.json').read_bytes())
        self.assertEqual({'word-context', 'word-context-extra'}, set(proof['corpora']))
        self.assertEqual(0, proof['modelCalls'])
        total = 0
        for name, corpus in proof['corpora'].items():
            raw = (directory / corpus['archivedManifest']).read_bytes()
            self.assertEqual(corpus['files']['manifest.json'], hashlib.sha256(raw).hexdigest())
            manifest = json.loads(raw)
            source = (directory.parent / corpus['archivedSource']).read_bytes()
            self.assertEqual(corpus['archivedPreparerSha256'], hashlib.sha256(source).hexdigest())
            self.assertFalse(corpus['independentOriginalSourceDigestAvailable'])
            ast.parse(source)
            for filename, digest in corpus['files'].items():
                original = f"{corpus['originalRoot']}/{filename}"
                self.assertEqual(receipt['bindings'][original], digest)
                if filename.endswith('.jsonl'):
                    self.assertEqual(parent['exclusionBindings'][original], digest)
            for part, partition in manifest['partitions'].items():
                self.assertEqual(corpus['rows'][part], partition['rows'])
                self.assertEqual(corpus['files'][part + '.jsonl'], partition['sha256'])
                historical = receipt['counts'][f'{name}/{part}']
                self.assertEqual(historical['rows'], partition['rows'])
                self.assertEqual(historical['articles'], partition['articles'])
                self.assertEqual(500, partition['familyKeys'])
                total += partition['rows']
        self.assertEqual(14508, total)

    def test_word_context_v3_sources_bind_to_historical_outputs(self):
        directory = FIXTURE.parent / 'v6-inputs'
        record = json.loads((directory / 'word-context-v3-count-source-recovery.json').read_bytes())
        lineage = json.loads((directory / 'role-training-v5-v6-lineage.json').read_bytes())
        self.assertIn(record['expectedModelCountsSha256'], lineage['shared']['countsSha256'])
        manifest = json.loads((directory / 'early-wikipedia-word-context-manifest.json').read_bytes())
        self.assertEqual(record['expectedPackedModel']['sha256'], manifest['wordContextModelSha256'])
        self.assertEqual(record['trainingArticleBuckets'], manifest['articleBuckets']['training'])
        self.assertFalse(record['independentOriginalSourceDigestsAvailable'])
        self.assertFalse(record['qualified'])
        self.assertEqual({'word_context_v3_counter.py', 'word_context_v3_packer.py'},
                         set(record['sourceBodies']))
        for name, digest in record['sourceBodies'].items():
            source = (directory.parent / name).read_bytes()
            self.assertEqual(digest, hashlib.sha256(source).hexdigest())
            ast.parse(source)

    def test_word_context_v3_replay_binds_shards_exclusions_and_both_outputs(self):
        directory = FIXTURE.parent / 'v6-inputs'
        replay = json.loads((directory / 'word-context-v3-replay.json').read_bytes())
        archive = json.loads((directory / 'word-context-v3-count-source-recovery.json').read_bytes())
        lock = ROOT / 'tools/typing_experiments/available-v6-article-origin-v1/source-lock.json'
        sources = {item['name']: item['sha256'] for item in json.loads(lock.read_bytes())['shards']
                   if item['name'] != '0020.parquet'}
        self.assertEqual(9, len(sources))
        self.assertEqual(sources, {Path(path).name.removeprefix('ru-'): sha
                                   for path, sha in replay['sourceShards'].items()})
        feature = json.loads((directory / 'early-wikipedia-context-feature-manifest.json').read_bytes())
        excluded = {path: digest for path, digest in feature['priorRows'].items()
                    if not path.startswith('build/context-ranking-20261025/')
                    and path != 'build/joint-correction-20261025/corpus/train.jsonl'}
        self.assertEqual(23, len(excluded))
        self.assertEqual(excluded, replay['priorRowBindings'])
        self.assertEqual(archive['expectedCounts'], replay['counts'])
        self.assertEqual(replay['counts']['pairs'], replay['pairFrequencyCounts']['2'])
        self.assertEqual(archive['expectedPackedModel'], replay['originalFiles']['ru-word-context.bin'])
        self.assertEqual(archive['expectedModelCountsSha256'],
                         replay['originalFiles']['model-counts.jsonl']['sha256'])
        self.assertEqual(archive['expectedPackedModel']['pairs'],
                         replay['originalFiles']['model-counts.jsonl']['rows'])
        self.assertEqual(2, replay['independentlyPinnedFiles'])
        self.assertEqual(0, replay['modelCalls'])
        self.assertFalse(replay['qualified'])

    def test_supervised_v2_rows_and_original_builder_bind_v6_plan(self):
        directory = FIXTURE.parent / 'v6-inputs'
        record = json.loads((directory / 'tatoeba-supervised-v2-recovery.json').read_bytes())
        manifest_raw = (directory / 'supervised-v2-manifest.json').read_bytes()
        manifest = json.loads(manifest_raw)
        parent = json.loads((directory / 'sentence-pairs-v2-v6-plan.json').read_bytes())
        source = (directory.parent / 'conversation_supervised_v2_preparer.py').read_bytes()
        self.assertEqual(manifest['builderSha256'], hashlib.sha256(source).hexdigest())
        self.assertEqual(manifest['builderSha256'], record['originalBuilderSha256'])
        self.assertEqual(manifest['guardSha256'], record['guardSha256'])
        self.assertEqual(hashlib.sha256(manifest_raw).hexdigest(), record['files']['manifest.json'])
        for name, sha in manifest['files'].items():
            self.assertEqual(sha, record['files'][name])
            self.assertEqual(sha, parent['exclusionBindings'][record['originalRoot'] + '/' + name])
        self.assertEqual({part: counts['rows'] for part, counts in manifest['counts'].items()}, record['rows'])
        self.assertEqual(28903, sum(record['rows'].values()))
        self.assertEqual(33, record['exclusions'])
        self.assertEqual(9962, record['excludedSentenceIds'])
        self.assertEqual(35346, record['excludedTargetContexts'])
        self.assertEqual(199, record['removedCrossSplitPredictionContexts'])
        self.assertEqual(0, record['modelCalls'])

    def test_sentence_corpus_v6_recovery_matches_original_and_successor(self):
        directory = FIXTURE.parent / 'v6-inputs'
        record = json.loads((directory / 'sentence-corpus-v6-recovery.json').read_bytes())
        source = record['originalRoot']
        parent = json.loads((directory / 'sentence-pairs-v2-v6-plan.json').read_bytes())
        old = ROOT / 'docs/acceptance/2026-10-27-right-context-source-parity-and-selection-evidence.json'
        availability = (directory / 'sentence-corpus-v6-availability.json').read_bytes()
        report = json.loads(availability)
        self.assertEqual(parent['additionalArticleBindings'][source + '/contexts.unqualified.jsonl'],
                         record['contextsSha256'])
        self.assertEqual(json.loads(old.read_bytes())['bindings'][source + '/availability.json'],
                         record['availabilitySha256'])
        self.assertEqual(hashlib.sha256(availability).hexdigest(), record['availabilitySha256'])
        self.assertEqual({name: details['contexts'] for name, details in report['parts'].items()},
                         record['partCounts'])
        self.assertEqual(2068, record['contextRows'])
        self.assertEqual(report['eligibleArticles'], record['eligibleArticles'])
        self.assertEqual(report['scannedArticles'], record['scannedArticles'])
        self.assertEqual(json.loads(FIXTURE.read_bytes())['blockedArticles'], record['nextBlockedArticles'])
        self.assertEqual(report['blockedArticles'] + record['contextRows'], record['nextBlockedArticles'])
        self.assertEqual(0, record['modelCalls'])
        self.assertFalse(record['independentQualification'])

    def test_cc0_conversation_recovery_matches_original_v6_bindings(self):
        directory = FIXTURE.parent / 'v6-inputs'
        record = json.loads((directory / 'tatoeba-cc0-context-feature-recovery.json').read_bytes())
        old_evidence = ROOT / 'docs/acceptance/2026-10-27-tatoeba-history-evidence.json'
        old_bindings = json.loads(old_evidence.read_bytes())['receipt']['bindings']
        plan = json.loads((directory / 'sentence-pairs-v2-v6-plan.json').read_bytes())
        source = (directory.parent / 'context_feature_conversation_preparer.py').read_bytes()
        self.assertEqual(record['archivedPreparerSha256'], hashlib.sha256(source).hexdigest())
        self.assertEqual(plan['exclusionBindings'][CC0_SPLITS], record['sourceSplitSha256'])
        self.assertEqual({'calibration.jsonl', 'holdout.jsonl', 'manifest.json'}, set(record['files']))
        for name, sha in record['files'].items():
            path = record['originalRoot'] + '/' + name
            self.assertEqual(old_bindings[path], sha)
            if name != 'manifest.json':
                self.assertEqual(plan['exclusionBindings'][path], sha)
        self.assertEqual(4444, sum(part['rows'] for part in record['counts'].values()))
        self.assertEqual('packed-morphology-id', record['declaredFamilyKind'])
        self.assertEqual(0, record['modelCalls'])
        self.assertFalse(record['independentQualification'])

    def test_tatoeba_cc0_replays_both_original_inputs(self):
        payloads, counts = restore_tatoeba_cc0()
        split_sha = hashlib.sha256(payloads['tatoeba-sentence-splits.jsonl']).hexdigest()
        counts_sha = hashlib.sha256(payloads['tatoeba-train-counts.jsonl']).hexdigest()
        self.assertEqual({'train': 18497, 'calibration': 2335, 'holdout': 2245}, counts)
        self.assertEqual(sum(counts.values()), len(payloads['tatoeba-sentence-splits.jsonl'].splitlines()))
        directory = FIXTURE.parent / 'v6-inputs'
        parent = json.loads((directory / 'sentence-pairs-v2-v6-plan.json').read_bytes())
        lineage = json.loads((directory / 'role-training-v5-v6-lineage.json').read_bytes())
        self.assertEqual(split_sha, parent['exclusionBindings'][CC0_SPLITS])
        self.assertIn(counts_sha, lineage['shared']['countsSha256'])

    def test_reliable_side_recovery_matches_both_successor_plans(self):
        directory = FIXTURE.parent / 'v6-inputs'
        proof = json.loads((directory / 'reliable-side-v5-recovery.json').read_bytes())
        source = proof['originalRoot']
        for name in ('sentence-corpus-v6-plan.json', 'sentence-pairs-v2-v6-plan.json'):
            plan = json.loads((directory / name).read_bytes())
            self.assertEqual(proof['contextsSha256'],
                             plan['additionalArticleBindings'][source + '/contexts.unqualified.jsonl'])
        availability = (directory / 'reliable-side-v5-availability.json').read_bytes()
        historic = ROOT / 'docs/acceptance/2026-10-27-right-context-role-kotlin-evidence.json'
        bindings = json.loads(historic.read_bytes())['bindings']
        self.assertEqual(proof['availabilitySha256'], hashlib.sha256(availability).hexdigest())
        self.assertEqual(proof['availabilitySha256'], bindings[source + '/availability.json'])
        self.assertEqual(1690, proof['contextRows'])
        self.assertEqual({'calibration': 844, 'holdout': 846}, proof['partCounts'])
        self.assertEqual(313977, proof['eligibleArticles'])
        self.assertEqual(17886, proof['nextBlockedArticles'])
        self.assertEqual(0, proof['modelCalls'])
        self.assertFalse(proof['independentQualification'])

    def test_original_legacy_spelling_payloads_bind_all_three_selection_plans(self):
        directory = FIXTURE.parent / 'v6-inputs'
        recovery = json.loads((directory / 'legacy-spelling-rows-recovery.json').read_bytes())
        plans = [json.loads((directory / name).read_bytes()) for name in (
            'reliable-side-v5-plan.json', 'sentence-corpus-v6-plan.json', 'sentence-pairs-v2-v6-plan.json',
        )]
        ledger = holdout_ledger.load_ledger(ROOT / 'tools/typing_experiments/holdout-ledger.json')
        registry = {row['id']: row for row in ledger['entries']}
        self.assertEqual(set(map(str, range(6, 13))), set(recovery['corpora']))
        for version, cohort in recovery['corpora'].items():
            with self.subTest(version=version):
                path = cohort['originalPath']
                entry = registry[cohort['registryEntry']]
                self.assertEqual(1700, cohort['rows'])
                self.assertEqual(cohort['rows'], entry['rowCount'])
                self.assertEqual(cohort['families'], cohort['rows'])
                self.assertEqual(cohort['articles'], len(entry['keys']['article']))
                self.assertEqual(cohort['generatorSha256'], entry['generatorBindings'][LEGACY_GENERATOR])
                self.assertEqual(cohort['sourceSha256'], entry['publicSource']['sha256'])
                self.assertEqual(cohort['sha256'], entry['bindings'][path])
                for plan in plans:
                    self.assertEqual(cohort['sha256'], plan['exclusionBindings'][path])
        self.assertEqual(11900, recovery['originalRows'])
        self.assertEqual(11900, recovery['distinctFamilies'])
        self.assertEqual(0, recovery['modelCalls'])
        self.assertFalse(recovery['independentQualification'])

    def test_original_refinement_family_rows_bind_all_three_selection_plans(self):
        directory = FIXTURE.parent / 'v6-inputs'
        plans = ('reliable-side-v5-plan.json', 'sentence-corpus-v6-plan.json',
                 'sentence-pairs-v2-v6-plan.json')
        for name in plans:
            with self.subTest(plan=name):
                original = json.loads((directory / name).read_bytes())['exclusionBindings']
                families, payloads = refinement_families(original)
                self.assertEqual(3668, len(families))
                self.assertEqual(8, len(payloads))
                self.assertEqual(4, len(set(payloads.values())))
        missing = 'build/typing-ranker-v2/candidates-current/rows.jsonl'
        bindings = json.loads((directory / plans[0]).read_bytes())['exclusionBindings']
        del bindings[missing]
        with self.assertRaises(ValueError) as failure:
            refinement_families(bindings)
        self.assertEqual('V6_FAMILY_REFINEMENT_BINDING:' + missing, str(failure.exception))

    def test_joint_and_diagnostic_replay_binds_each_original_payload(self):
        directory = FIXTURE.parent / 'v6-inputs'
        recovery = json.loads((directory / 'joint-diagnostic-recovery.json').read_bytes())
        plan = json.loads((directory / 'reliable-side-v5-plan.json').read_bytes())
        availability = json.loads((directory / 'reliable-side-v5-availability.json').read_bytes())
        rare_raw = (directory / 'diagnostic-rare-ranking-manifest.json').read_bytes()
        manifests = JOINT_MANIFESTS | {'diagnostic-rare-ranking': hashlib.sha256(rare_raw).hexdigest()}
        self.assertEqual(set(manifests), set(recovery['corpora']))
        for corpus, record in recovery['corpora'].items():
            self.assertEqual(manifests[corpus], record['manifestSha256'])
            for name, payload in record['files'].items():
                path = record['originalRoot'] + '/' + name
                self.assertEqual(plan['exclusionBindings'][path], payload['sha256'])
        self.assertEqual(9, sum(len(corpus['files']) for corpus in recovery['corpora'].values()))
        self.assertEqual(54364, recovery['rawRows'])
        self.assertEqual(54364, sum(item['rows'] for c in recovery['corpora'].values()
                                    for item in c['files'].values()))
        self.assertEqual(964, recovery['corpora']['diagnostic-rare-ranking']['articles'])
        self.assertEqual(availability['blockedArticles'], recovery['reliableSideV5BlockedArticles'])
        self.assertRegex(recovery['reliableSideV5ArticleKeyIndexSha256'], r'^[0-9a-f]{64}$')
        self.assertEqual(0, recovery['modelCalls'])

    def test_diagnostic_rare_ranking_recovers_manifest_and_binds_reliable_side_inputs(self):
        directory = FIXTURE.parent / 'v6-inputs'
        manifest = json.loads((directory / 'diagnostic-rare-ranking-manifest.json').read_bytes())
        plan = json.loads((directory / 'reliable-side-v5-plan.json').read_bytes())
        source = 'build/joint-correction-20261025/0020.parquet'
        self.assertEqual(plan['sourceBindings'][source], manifest['sourceSha256'])
        builder = ROOT / 'tools/typing_experiments/frozen_sources/prepare_joint_followup_b9cc4859e08021f8.py'
        self.assertEqual(hashlib.sha256(builder.read_bytes()).hexdigest(), manifest['builderSha256'])
        self.assertEqual({'calibration.jsonl', 'holdout.jsonl'}, set(manifest['files']))
        for name, digest in manifest['files'].items():
            path = 'build/diagnostic-rare-ranking/fresh-corpus/' + name
            self.assertEqual(plan['exclusionBindings'][path], digest)
        self.assertEqual((6480, 7521), (manifest['excludedFamilies'], manifest['excludedArticles']))
        self.assertEqual({'calibration': 4760, 'holdout': 4788},
                         {part: count['rows'] for part, count in manifest['counts'].items()})
        for count in manifest['counts'].values():
            self.assertEqual(500, count['families'])
            self.assertEqual(count['rows'], sum(count['groups'].values()))

    def test_first_letter_admission_protocols_bind_both_original_holdouts(self):
        source = FIXTURE.parent
        directory = source / 'v6-inputs'
        original = json.loads((RECEIPT.parent / '2026-10-25-ambiguous-winner-evidence.json').read_bytes())
        rare = json.loads((directory / 'diagnostic-rare-ranking-manifest.json').read_bytes())
        recovery = json.loads((directory / 'first-letter-admission-recovery.json').read_bytes())
        self.assertEqual(rare['sourceSha256'], recovery['sourceSha256'])
        self.assertEqual(rare['excludedArticles'], recovery['diagnosticRareRankingExcludedArticles'])
        self.assertEqual(5173, recovery['jointArticleKeys'])
        self.assertEqual(rare['excludedArticles'], recovery['jointArticleKeys'] +
                         sum(item['articles'] for item in recovery['holdouts'].values()))
        self.assertEqual(0, recovery['modelCalls'])
        for stage, key, pool_size in (('initial', 'firstSample', 4389), ('confirmatory', 'confirmatory', 3879)):
            with self.subTest(stage=stage):
                raw = (directory / f'first-letter-admission-{stage}-protocol.json').read_bytes()
                protocol = json.loads(raw)
                self.assertEqual(original[key]['protocolSha256'], hashlib.sha256(raw).hexdigest())
                self.assertEqual(original[key]['rowsSha256'], protocol['rowsSha256'])
                self.assertEqual(original[key]['rows'], protocol['rows'])
                self.assertEqual(pool_size, protocol['surfaceFamilies'])
                self.assertEqual(original['unchangedModelSha256'], protocol['model'])
                self.assertEqual(rare['sourceSha256'], protocol['source'])
                recovered = recovery['holdouts'][stage]
                self.assertEqual(original[key]['protocolSha256'], recovered['originalProtocolSha256'])
                self.assertEqual(protocol['rowsSha256'], recovered['originalRowsSha256'])
                self.assertEqual(protocol['rows'], recovered['rows'])
                self.assertEqual(original[key]['selectedSurfaceFamilies'], recovered['surfaceFamilies'])
                preparer = source / f'first_letter_admission_{stage}_preparer.py'
                code = preparer.read_bytes()
                self.assertNotIn(b'/Users/', code)
                compile(code, preparer.name, 'exec')

    def test_sentence_pairs_parent_plan_matches_original_and_all_source_bindings(self):
        historical = json.loads((RECEIPT.parent / '2026-10-27-right-context-source-parity-and-selection-evidence.json').read_bytes())
        natural = json.loads((RECEIPT.parent / '2026-10-27-natural-context-history-evidence.json').read_bytes())
        directory = FIXTURE.parent / 'v6-inputs'
        raw = (directory / 'sentence-pairs-v2-v6-plan.json').read_bytes()
        expected = historical['bindings']['build/right-context-sentence-pairs-v2-v6-20261027/plan.json']
        self.assertEqual(expected, hashlib.sha256(raw).hexdigest())
        plan = json.loads(raw)
        lock = check_available_v6_calibration_index.DIRECTORY.parent / 'source-lock.json'
        shards = {item['name']: item['sha256'] for item in json.loads(lock.read_bytes())['shards']}
        bound = {Path(path).name.removeprefix('ru-'): digest for path, digest in plan['sourceBindings'].items()}
        self.assertEqual(shards, bound)
        self.assertEqual(64, len(plan['exclusionBindings']))
        self.assertEqual(7, len(plan['sourceContextBindings']))
        self.assertEqual(5, len(plan['additionalArticleBindings']))
        self.assertLessEqual(plan['sourceContextBindings'].items(), natural['receipt']['bindings'].items())
        noun_case = json.loads((directory / 'noun-focus-v3-manifest.json').read_bytes())
        self.assertLess(noun_case['exclusionBindings'].items(), plan['exclusionBindings'].items())
        self.assertEqual(json.loads(MANIFEST.read_bytes())['modelSha256'], plan['modelSha256'])
        self.assertEqual(0, plan['modelCalls'])
        self.assertFalse(plan['modelScoresMayAffectSelection'])

    def test_earlier_selection_plans_match_original_digests_and_parent_bindings(self):
        directory = FIXTURE.parent / 'v6-inputs'
        snapshots = (
            ('first-wikipedia', 'natural-context-history', 'right-context-wikipedia', True),
            ('fresh-side-v4', 'right-context-role-training', 'right-context-fresh-side-v4', False),
            ('reliable-side-v5', 'right-context-other-part-training', 'right-context-reliable-side-v5', False),
            ('sentence-corpus-v6', 'right-context-role-kotlin', 'right-context-sentence-corpus-v6', False),
        )
        for file, acceptance, original, nested in snapshots:
            with self.subTest(plan=file):
                evidence = json.loads((RECEIPT.parent / f'2026-10-27-{acceptance}-evidence.json').read_bytes())
                bindings = evidence['receipt' if nested else 'bindings']
                if nested:
                    bindings = bindings['bindings']
                raw = (directory / f'{file}-plan.json').read_bytes()
                self.assertEqual(bindings[f'build/{original}-20261027/plan.json'], hashlib.sha256(raw).hexdigest())

        focused = (directory / 'right-context-focused-v2-plan.json').read_bytes()
        wikipedia = json.loads((directory / 'first-wikipedia-plan.json').read_bytes())
        self.assertEqual(wikipedia['parentNaturalPlanSha256'], hashlib.sha256(focused).hexdigest())
        self.assertEqual(wikipedia['exclusionBindings'], json.loads(focused)['exclusionBindings'])
        self.assertEqual(60, len(wikipedia['exclusionBindings']))
        self.assertEqual(24, len(json.loads(focused)['trainingFamilies']))

    def test_side_plan_and_manifest_match_original_exclusions_and_payload_bindings(self):
        directory = FIXTURE.parent / 'v6-inputs'
        original = json.loads((RECEIPT.parent / '2026-10-27-frozen-context-descendants-evidence.json').read_bytes())
        bindings = original['receipt']['bindings']
        prefix = 'build/right-context-side-20261027/'
        plan_raw = (directory / 'side-plan.json').read_bytes()
        manifest_raw = (directory / 'side-manifest.json').read_bytes()
        plan, manifest = map(json.loads, (plan_raw, manifest_raw))
        self.assertEqual(bindings[prefix + 'plan.json'], hashlib.sha256(plan_raw).hexdigest())
        self.assertEqual(bindings[prefix + 'corpus/manifest.json'], hashlib.sha256(manifest_raw).hexdigest())
        self.assertEqual(hashlib.sha256(plan_raw).hexdigest(), manifest['planSha256'])
        self.assertEqual(plan['sourceBindings'], manifest['sourceBindings'])
        self.assertEqual(plan['exclusionBindings'], manifest['exclusionBindings'])
        families = manifest['excludedFamilies']
        self.assertEqual(sorted(set(families)), families)
        self.assertEqual(92, len(families))
        v6 = json.loads((directory / 'sentence-pairs-v2-v6-plan.json').read_bytes())
        self.assertLessEqual(plan['exclusionBindings'].items(), v6['exclusionBindings'].items())
        for name, digest in manifest['files'].items():
            self.assertEqual(bindings[prefix + 'corpus/' + name], digest)
            if name.endswith('.jsonl'):
                self.assertEqual(v6['exclusionBindings'][prefix + 'corpus/' + name], digest)

    def test_fresh_matched_v5_recovery_binds_original_payload_and_article_keys(self):
        directory = FIXTURE.parent / 'v6-inputs'
        recovered = json.loads((directory / 'fresh-matched-v5-context-recovery.json').read_bytes())
        parent_raw = (directory / 'sentence-pairs-v2-v6-plan.json').read_bytes()
        parent = json.loads(parent_raw)
        self.assertEqual(hashlib.sha256(parent_raw).hexdigest(), recovered['parentPlanSha256'])
        self.assertEqual(parent['additionalArticleBindings'][recovered['originalPath']], recovered['originalSha256'])
        sources = {Path(path).name.removeprefix('ru-'): digest for path, digest in parent['sourceBindings'].items()}
        self.assertEqual(sources, recovered['sources'])
        self.assertEqual(926220, recovered['scannedArticles'])
        self.assertEqual(41214, recovered['candidateContexts'])
        self.assertEqual(1877200, recovered['exactProjectionHypotheses'])
        rows = recovered['records']
        self.assertEqual(45, len(rows))
        self.assertEqual(len(rows), len({row['article'] for row in rows}))
        self.assertEqual(len(rows), len({row['contextHash'] for row in rows}))
        self.assertEqual(['calibration'] * 25 + ['holdout'] * 20, [row['provisionalSplit'] for row in rows])
        for row in rows:
            self.assertEqual({'article', 'source', 'contextHash', 'selectionHash', 'provisionalSplit'}, set(row))
            self.assertTrue(row['article'].isascii() and row['article'].isdigit())
            self.assertIn(row['source'].removeprefix('ru-'), sources)
            for key in ('contextHash', 'selectionHash'):
                self.assertRegex(row[key], r'^[0-9a-f]{64}$')
        for partition in (rows[:25], rows[25:]):
            order = [row['selectionHash'] for row in partition]
            self.assertEqual(sorted(order), order)
        self.assertEqual(0, recovered['modelCalls'])
        self.assertFalse(recovered['qualificationPassed'])

    def test_original_authored_noun_case_is_excluded_by_family_and_context(self):
        full = holdout_ledger.load_ledger(ROOT / 'tools/typing_experiments/holdout-ledger.json')
        entries = [item for item in full['entries'] if item['id'].startswith('authored-noun-case-training-v1-')]
        self.assertEqual(2, len(entries))
        self.assertEqual([25, 576], [len(next(iter(item['keys'].values()))) for item in entries])
        scoped = dict(full, entries=entries)
        checks = (
            ('family', {'families': ['песня']}),
            ('context', {'prefix': 'я вижу', 'typed': 'песн', 'expectedSpelling': 'песней'}),
        )
        for kind, proposed in checks:
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:' + kind):
                holdout_ledger.assert_disjoint([proposed], scoped, kinds=[kind], require_complete=False)

    def test_early_noun_case_plans_and_audits_match_historical_receipt(self):
        origin = json.loads((RECEIPT.parent / '2026-10-26-noun-case-training-evidence.json').read_bytes())
        directory = FIXTURE.parent / 'v6-inputs'
        cases = {
            'noun-focus-plan.json': 'noun-case-focus-20261026/plan.json',
            'noun-focus-v2-plan.json': 'noun-case-focus-v2-20261026/plan.json',
            'noun-focus-v3-plan.json': 'noun-case-focus-v3-20261026/plan.json',
            'noun-focus-availability.json': 'noun-case-focus-20261026/availability.json',
            'noun-focus-v3-separation-audit.json': 'noun-case-focus-v3-20261026/separation-audit.json',
        }
        for saved, original in cases.items():
            with self.subTest(saved=saved):
                self.assertEqual(origin['artifactHashes']['build/' + original],
                                 hashlib.sha256((directory / saved).read_bytes()).hexdigest())
        plans = [json.loads((directory / name).read_bytes()) for name in list(cases)[:3]]
        self.assertEqual([24, 64, 64], [p['maximumContextsPerFamily'] for p in plans])
        for field in ('seed', 'contextsPerPart', 'calibrationPrecision', 'holdoutPrecision'):
            self.assertEqual(1, len({plan[field] for plan in plans}))
        self.assertTrue(plans[2]['disclosedFamiliesExcluded'])

    def test_noun_case_regression_results_and_selection_parameters(self):
        origin = json.loads((RECEIPT.parent / '2026-10-26-noun-case-offline-evidence.json').read_bytes())
        directory = FIXTURE.parent / 'v6-inputs'
        focused = json.loads((directory / 'noun-focus-v3-plan.json').read_bytes())
        specifications = (
            ('broad-v2', 'contexts', 3000, 4, 12000, 6000),
            ('instrumental', 'maximumContexts', 512, 32, 68, 51),
        )
        for kind, cap_name, cap, cap_per_family, rows, controls in specifications:
            with self.subTest(kind=kind):
                result_raw = (directory / f'noun-{kind}-result.json').read_bytes()
                original = f'build/noun-case-{kind}-20261026/result.json'
                self.assertEqual(origin['artifactHashes'][original], hashlib.sha256(result_raw).hexdigest())
                result = json.loads(result_raw)
                self.assertEqual((rows, controls, 0), tuple(result['metrics'][key] for key in
                                 ('rows', 'controls', 'scopeEligible')))
                self.assertIsNone(result['metrics']['precision'])
                plan = json.loads((directory / f'noun-{kind}-plan.json').read_bytes())
                self.assertEqual((cap, cap_per_family), (plan[cap_name], plan['maximumContextsPerFamily']))
                self.assertEqual(focused['sourceSha256'], plan['sourceSha256'])
                self.assertEqual(origin['modelSha256'], plan['modelSha256'])
                self.assertEqual(result['policySha256'], plan['policySha256'])

    def test_grammar_focused_plan_and_logged_availability(self):
        origin = json.loads((RECEIPT.parent / '2026-10-26-infinitive-revision-offline-evidence.json').read_bytes())
        directory = FIXTURE.parent / 'v6-inputs'
        raw = (directory / 'grammar-focused-plan.json').read_bytes()
        self.assertEqual(origin['policy']['planSha256'], hashlib.sha256(raw).hexdigest())
        plan = json.loads(raw)
        historical = json.loads((directory / 'grammar-focused-availability.json').read_bytes())
        for part, count in origin['focusedCounts'].items():
            with self.subTest(part=part):
                self.assertEqual(plan['contextsPerPart'], historical['selected'][part])
                self.assertEqual(count['contexts'], historical['selected'][part])
                self.assertEqual(count['families'], historical['familyCounts'][part])

    def test_recovered_tatoeba_manifests_preserve_original_exclusion_chain(self):
        directory = FIXTURE.parent / 'v6-inputs'
        imported = json.loads((RECEIPT.parent / '2026-10-27-tatoeba-history-evidence.json').read_bytes())
        derived = json.loads((RECEIPT.parent / '2026-10-27-tatoeba-derived-history-evidence.json').read_bytes())
        grammar = json.loads((RECEIPT.parent / '2026-10-26-infinitive-revision-offline-evidence.json').read_bytes())
        noun = json.loads((RECEIPT.parent / '2026-10-26-noun-case-training-evidence.json').read_bytes())
        supervised_path = 'build/conversation-supervised-20261026/corpus-v2/manifest.json'
        grammar_path = 'build/grammar-focused-eval-20261026/corpus/manifest.json'
        noun_path = 'build/noun-case-focus-v3-20261026/corpus/manifest.json'
        self.assertEqual(grammar['focusedManifestSha256'], derived['receipt']['bindings'][grammar_path])
        self.assertEqual(noun['artifactHashes'][noun_path], derived['receipt']['bindings'][noun_path])
        manifests = []
        for name, expected in (
            ('supervised-v2', imported['receipt']['bindings'][supervised_path]),
            ('grammar-focused', grammar['focusedManifestSha256']),
            ('noun-focus-v3', noun['artifactHashes'][noun_path]),
        ):
            with self.subTest(name=name):
                raw = (directory / f'{name}-manifest.json').read_bytes()
                self.assertEqual(expected, hashlib.sha256(raw).hexdigest())
                manifests.append(json.loads(raw))
        supervised_manifest, grammar_manifest, noun_manifest = manifests
        grammar_bindings = grammar_manifest['exclusionBindings']
        noun_bindings = noun_manifest['exclusionBindings']
        self.assertEqual((33, 47, 56), (len(supervised_manifest['exclusions']),
                                        len(grammar_bindings), len(noun_bindings)))
        self.assertLess(supervised_manifest['exclusions'].items(), grammar_bindings.items())
        self.assertLess(grammar_bindings.items(), noun_bindings.items())
        self.assertEqual(32, grammar_manifest['excludedContrastFamilies'])
        self.assertEqual(0, grammar_manifest['modelCalls'])
        self.assertEqual(0, noun_manifest['modelCalls'])
        binding_digest = hashlib.sha256(json.dumps(noun_bindings, sort_keys=True).encode()).hexdigest()
        self.assertEqual(noun['cohortManifest']['exclusionBindingsSha256'], binding_digest)

    def test_right_context_focused_v2_availability_records_insufficient_selection(self):
        directory = FIXTURE.parent / 'v6-inputs'
        grammar = json.loads((directory / 'grammar-focused-availability.json').read_bytes())
        historical = json.loads((directory / 'right-context-focused-v2-availability.json').read_bytes())
        self.assertEqual(grammar['scannedSourceRows'], historical['scannedSourceRows'])
        self.assertEqual({'calibration': 83, 'holdout': 14}, historical['selected'])
        self.assertEqual({'calibration': 14, 'holdout': 9}, historical['families'])
        self.assertEqual(historical['blockedPriorSentenceIds'], historical['blockedSentenceHashes'])

    def test_frozen_natural_v2_model_binding_matches_original_receipt(self):
        original = json.loads((RECEIPT.parent / '2026-10-27-right-context-training-evidence.json').read_bytes())
        directory = FIXTURE.parent / 'v6-inputs'
        binding_raw = (directory / 'natural-frozen-model-v2-binding.json').read_bytes()
        manifest_raw = (directory / 'natural-frozen-manifest.json').read_bytes()
        binding = json.loads(binding_raw)
        manifest = json.loads(manifest_raw)
        self.assertEqual(original['modelBindingSha256'], hashlib.sha256(binding_raw).hexdigest())
        self.assertEqual(binding['corpusManifestSha256'], hashlib.sha256(manifest_raw).hexdigest())
        self.assertEqual(original['naturalPlanSha256'], manifest['planSha256'])
        self.assertEqual(original['corpusFiles'], manifest['files'])
        self.assertEqual(manifest['modelSha256'], binding['previousModelSha256'])
        self.assertEqual(original['modelSha256'], binding['modelSha256'])
        self.assertTrue(binding['corpusFilesUnchanged'])
        self.assertTrue(binding['trainingFamiliesUnchanged'])
        self.assertFalse(binding['independentModelScoresRead'])

    def test_role_training_lineage_preserves_historical_bindings_and_v6_reuse(self):
        directory = FIXTURE.parent / 'v6-inputs'
        lineage = json.loads((directory / 'role-training-v5-v6-lineage.json').read_bytes())
        shared = lineage['shared']
        archive = ROOT / 'tools/typing_experiments/late_training_sources'
        history = json.loads((RECEIPT.parent / '2026-10-27-late-authored-history-evidence.json').read_bytes())
        families = shared['trainingFamilies']
        self.assertEqual(sorted(set(families)), families)
        self.assertEqual(38, len(families))

        for version, name, source in (
            ('v5', 'other-part-training', 'train_53f9615d6f5aa10e.py'),
            ('v6', 'role-kotlin', 'train_d13526c080876cba.py'),
        ):
            with self.subTest(version=version):
                original = json.loads((RECEIPT.parent / f'2026-10-27-right-context-{name}-evidence.json').read_bytes())
                recorded = lineage['versions'][version]
                prefix = f'build/right-context-training-{version}-20261027/'
                self.assertEqual(original['bindings'][prefix + 'plan.json'], recorded['originalPlanSha256'])
                self.assertEqual(original['bindings'][prefix + 'frozen-model.json'], recorded['originalModelBindingSha256'])
                self.assertEqual(original['modelSha256'], recorded['modelSha256'])
                self.assertEqual(original['training']['groups'], shared['trainingGroups'])
                self.assertEqual(original['training']['candidateRows'], shared['candidateRows'])
                self.assertEqual(history['receipt']['bindings'][prefix + 'groups.jsonl'], shared['groupsSha256'])
                self.assertEqual(hashlib.sha256((archive / source).read_bytes()).hexdigest(),
                                 recorded['featureSources'][prefix + 'train.py'])
                self.assertTrue(all(not path.startswith('/') and '..' not in Path(path).parts
                                    for path in recorded['featureSources']))
                self.assertTrue(recorded['installedAssetsUnchanged'])
                self.assertFalse(recorded['qualified'])

        v5, v6 = (lineage['versions'][version] for version in ('v5', 'v6'))
        self.assertEqual(v5['modelSha256'], v6['parentModelSha256'])
        self.assertLess(v5['featureSources'].items(), v6['featureSources'].items())
        self.assertFalse(v6['corpusAndCandidatePoolsChanged'])

    def test_role_replay_compiler_uses_the_digest_pinned_jar(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            android = root / 'platforms/android-37.0/android.jar'
            android.parent.mkdir(parents=True)
            android.touch()
            cache = root / 'caches/modules-2/files-2.1/example/compiler/1.0'
            pinned = cache / 'one/compiler.jar'
            other = cache / 'two/compiler.jar'
            for jar, payload in ((pinned, b'original'), (other, b'different')):
                jar.parent.mkdir(parents=True)
                jar.write_bytes(payload)
            toolchain = root / 'toolchain.json'
            toolchain.write_text(json.dumps({'jars': [{
                'group': 'example', 'artifact': 'compiler', 'version': '1.0',
                'sha256': hashlib.sha256(b'original').hexdigest(),
            }]}))
            replay = {'TOOLCHAIN': toolchain, 'REPO': root,
                      'final_product_sources': lambda: [], 'HARNESS': root / 'Harness.kt'}
            environment = {'ANDROID_HOME': folder, 'GRADLE_USER_HOME': folder}
            java = SimpleNamespace(stderr=b'openjdk version "17.0.18"')
            with (patch.dict(os.environ, environment),
                  patch('recover_role_training_groups.subprocess.run', return_value=java)):
                _, jars, stub = compiler_inputs(replay, root / 'java')
                self.assertEqual([pinned], jars)
                self.assertEqual(android.resolve(), stub)
                pinned.unlink()
                with self.assertRaisesRegex(ValueError, 'PINNED_KOTLIN_CACHE:compiler'):
                    compiler_inputs(replay, root / 'java')

    def test_role_replay_exports_a_detached_commit_fetched_into_a_shallow_clone(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            remote, checkout, export = (root / name for name in ('remote', 'checkout', 'export'))
            remote.mkdir()

            def git(directory, *args):
                return subprocess.run(['git', '-c', 'user.name=Fixture', '-c',
                                       'user.email=fixture@example.invalid', '-c',
                                       'commit.gpgsign=false', *args], cwd=directory,
                                      check=True, capture_output=True, text=True).stdout.strip()

            git(remote, 'init', '--quiet')
            (remote / 'source.txt').write_text('historical')
            git(remote, 'add', 'source.txt')
            git(remote, 'commit', '--quiet', '-m', 'historical')
            revision = git(remote, 'rev-parse', 'HEAD')
            (remote / 'source.txt').write_text('current')
            git(remote, 'commit', '--quiet', '-am', 'current')
            git(root, 'clone', '--quiet', '--depth=1', remote.as_uri(), str(checkout))
            self.assertEqual('true', git(checkout, 'rev-parse', '--is-shallow-repository'))
            git(checkout, 'fetch', '--no-tags', '--depth=1', 'origin', revision)
            with (patch('recover_role_training_groups.ROOT', checkout),
                  patch('recover_role_training_groups.REVISION', revision)):
                export_revision(export)
            self.assertEqual('historical', (export / 'source.txt').read_text())
            self.assertEqual('current', (checkout / 'source.txt').read_text())
            self.assertFalse((export / '.git').exists())

    def test_role_refit_rejects_an_altered_count_table_before_fitting(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            groups, wiki, tatoeba = (root / name for name in ('groups', 'wiki', 'tatoeba'))
            for path in (groups, wiki, tatoeba):
                path.write_bytes(b'original')
            original = hashlib.sha256(b'original').hexdigest()
            lineage = root / 'lineage.json'
            lineage.write_text(json.dumps({
                'shared': {'groupsSha256': original, 'countsSha256': [original, original]},
                'versions': {'v5': {}, 'v6': {}},
            }))
            tatoeba.write_bytes(b'changed')
            output = root / 'output'
            with patch('refit_historical_role_models.LINEAGE', lineage):
                with self.assertRaisesRegex(ValueError, 'ROLE_COUNT_TABLE_IDENTITY:tatoeba'):
                    refit(groups, (wiki, tatoeba), output)
            self.assertFalse(output.exists())

    def test_role_refit_import_receipt_checks_the_pinned_tree_and_exported_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            repo = root / 'repo'
            sources = root / 'export'
            repo.mkdir()
            sources.mkdir()
            original = b'VALUE = 1\n'
            (repo / 'helper.py').write_bytes(original)
            (sources / 'helper.py').write_bytes(original)
            git = ['git', '-C', str(repo), '-c', 'user.name=Rune QA', '-c', 'user.email=qa@example.invalid']
            for command in (('init', '-q'), ('add', 'helper.py'), ('commit', '-qm', 'fixture')):
                subprocess.run(git + list(command), check=True)
            revision = subprocess.check_output(git + ['rev-parse', 'HEAD'], text=True).strip()
            path = root / 'imports.json'
            receipt = {'helper': {'path': 'helper.py', 'sha256': hashlib.sha256(original).hexdigest()}}
            path.write_text(json.dumps(receipt))
            with (patch('refit_historical_role_models.ROOT', repo),
                  patch('refit_historical_role_models.REVISION', revision)):
                self.assertEqual(receipt, verify_imports(path, sources))
                (sources / 'helper.py').write_bytes(b'VALUE = 2\n')
                with self.assertRaisesRegex(ValueError, 'ROLE_REFIT_IMPORT_IDENTITY'):
                    verify_imports(path, sources)
                receipt['helper']['sha256'] = hashlib.sha256(b'VALUE = 2\n').hexdigest()
                path.write_text(json.dumps(receipt))
                with self.assertRaisesRegex(ValueError, 'ROLE_REFIT_IMPORT_IDENTITY'):
                    verify_imports(path, sources)
                receipt['helper']['path'] = '../repo/helper.py'
                path.write_text(json.dumps(receipt))
                with self.assertRaisesRegex(ValueError, 'ROLE_REFIT_IMPORT_PATH'):
                    verify_imports(path, sources)

    def test_v6_exposure_permutations_keep_confirmed_flags_and_deduplicate(self):
        groups = [{'known', 'a'}, {'a', 'b'}, {'c'}, {'untouched'}]
        floor, masks = assignment_masks(groups, {'known'}, {'a', 'b', 'c', 'outside'})
        self.assertEqual(0b0001, floor)
        self.assertEqual({0b0001, 0b0011, 0b0101, 0b0111}, masks)

    def test_noun_case_v3_family_projection_binds_original_payload_counts(self):
        entries = {entry['id']: entry for entry in holdout_ledger.load_ledger(
            ROOT / 'tools/typing_experiments/holdout-ledger.json')['entries']}
        self.assertEqual(325, len(noun_case_family_keys(entries)))

    def test_three_earlier_availability_reports_match_original_hashes(self):
        records = {
            'fresh-matched-v5': ('2026-10-27-right-context-other-part-training-evidence.json',
                                 'available', (25, 20)),
            'reliable-side-v5': ('2026-10-27-right-context-role-kotlin-evidence.json',
                                 'parts', (844, 846)),
            'sentence-corpus-v6': ('2026-10-27-right-context-source-parity-and-selection-evidence.json',
                                   'parts', (1043, 1025)),
        }
        for name, (evidence, key, counts) in records.items():
            with self.subTest(name=name):
                bindings = json.loads((RECEIPT.parent / evidence).read_bytes())['bindings']
                original = f'build/right-context-{name}-20261027/availability.json'
                raw = (FIXTURE.parent / 'v6-inputs' / f'{name}-availability.json').read_bytes()
                self.assertEqual(bindings[original], hashlib.sha256(raw).hexdigest())
                record = json.loads(raw)[key]
                self.assertEqual(counts, tuple(record[p]['contexts'] for p in ('calibration', 'holdout')))

    def test_rivals_cover_all_remaining_historical_target_keys(self):
        self.assertEqual(
            {"newTargetKeys": 2488, "matches": 2492,
             "ambiguousTargetKeys": 3, "unmappedTargetKeys": 0},
            check_available_v6_rivals.check(),
        )

    def test_calibration_attribution_covers_bound_article_metadata(self):
        directory = check_available_v6_calibration_index.DIRECTORY.parent / "calibration-attribution"
        raw = (directory / "articles.jsonl").read_bytes()
        receipt = json.loads((directory / "receipt.json").read_bytes())
        self.assertEqual("52879ff76c1362c617d5910c4e75455c884e4a720034322a1a9593afe9e06fec",
                         hashlib.sha256(raw).hexdigest())
        self.assertEqual(receipt["articlesSha256"], hashlib.sha256(raw).hexdigest())
        rows = [json.loads(line) for line in raw.splitlines()]
        expected = attribution.expected_articles()
        self.assertEqual(receipt["articleCount"], len(rows))
        self.assertEqual(len(rows), len(expected))
        self.assertEqual(expected, {row["article"]: row["shard"] for row in rows})
        self.assertEqual(len(rows), len({row["url"] for row in rows}))
        for row in rows:
            parsed = urlsplit(row["url"])
            self.assertEqual(("https", "ru.wikipedia.org", "", ""),
                             (parsed.scheme, parsed.netloc, parsed.query, parsed.fragment))
            self.assertTrue(parsed.path.startswith("/wiki/"))
            self.assertEqual(row["title"], unquote(parsed.path.removeprefix("/wiki/")).replace("_", " "))
        self.assertEqual(926220, sum(shard["sourceRows"] for shard in receipt["scannedShards"].values()))
        bindings = dict(receipt["bindings"])
        archive = check_available_v6_calibration_index.DIRECTORY / 'calibration.tsv.bz2'
        digest = bindings.pop(archive.relative_to(ROOT).as_posix())
        catalog = json.loads((directory.parent / 'archive-catalog.json').read_bytes())
        self.assertEqual(catalog['archives'][archive.name]['archiveSha256'], digest)
        for name, digest in bindings.items():
            self.assertEqual(digest, hashlib.sha256((ROOT / name).read_bytes()).hexdigest())
        self.assertIs(receipt["revisionIdsVerified"], False)
        self.assertIs(receipt["publicationRightsReviewed"], False)

    def test_changed_calibration_index_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "index.jsonl"
            changed.write_bytes(check_available_v6_calibration_index.INDEX.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "V6_CALIBRATION_INDEX_DIGEST"):
                check_available_v6_calibration_index.check(changed)

    def test_holdout_attribution_matches_original_article_assignments(self):
        root = check_available_v6_calibration_index.DIRECTORY.parent
        directory = root / 'holdout-attribution'
        raw = (directory / 'articles.jsonl').read_bytes()
        receipt = json.loads((directory / 'receipt.json').read_bytes())
        recovery = json.loads((root / 'holdout-recovery/receipt.json').read_bytes())
        expected = {
            row['article']: row['shard']
            for row in map(json.loads, (root / 'recovered/articles.jsonl').read_bytes().splitlines())
            if row['partition'] == 'holdout'
        }
        records = list(map(json.loads, raw.splitlines()))
        ids = [int(row['article']) for row in records]
        self.assertEqual(sorted(set(ids)), ids)
        self.assertEqual(expected, {row['article']: row['shard'] for row in records})
        self.assertEqual(1614, len(records))
        self.assertEqual(len(records), len({row['url'] for row in records}))
        self.assertEqual(receipt['articleCount'], len(records))
        self.assertEqual(receipt['articlesSha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(receipt['decodedHoldoutTSVSha256'], recovery['decodedSha256'])
        self.assertEqual(926220, sum(item['sourceRows'] for item in receipt['scannedShards'].values()))
        self.assertEqual(1614, sum(item['articles'] for item in receipt['scannedShards'].values()))
        for row in records:
            url = urlsplit(row['url'])
            self.assertEqual(('https', 'ru.wikipedia.org', '', ''), (url.scheme, url.netloc, url.query, url.fragment))
            self.assertTrue(url.path.startswith('/wiki/'))
            self.assertEqual(row['title'], unquote(url.path.removeprefix('/wiki/')).replace('_', ' '))
        for path, digest in receipt['bindings'].items():
            self.assertEqual(digest, hashlib.sha256((ROOT / path).read_bytes()).hexdigest())
        self.assertIs(receipt['revisionIdsVerified'], False)
        self.assertIs(receipt['publicationRightsReviewed'], False)

    def test_historical_holdout_translation_revisions_match_source_index_and_outcomes(self):
        root = check_available_v6_calibration_index.DIRECTORY.parent
        directory = root / 'holdout-attribution'
        evidence = json.loads((directory / 'translation-sources.json').read_bytes())
        index = (root / 'holdout-recovery/source-index.jsonl').read_bytes()
        mapping = (directory / 'articles.jsonl').read_bytes()
        receipt = json.loads((directory / 'receipt.json').read_bytes())
        self.assertEqual(hashlib.sha256(index).hexdigest(), evidence['sourceIndexSha256'])
        self.assertEqual(hashlib.sha256(mapping).hexdigest(), evidence['sourceArticleMapSha256'])
        self.assertEqual(receipt['decodedHoldoutTSVSha256'], evidence['decodedHoldoutTSVSha256'])
        self.assertEqual('2023-11-01T23:59:59Z', evidence['queryCutoff'])
        self.assertFalse(evidence['publicationRightsReviewed'])
        self.assertFalse(evidence['articleRevisionsVerified'])

        articles = evidence['articles']
        ids = [int(row['article']) for row in articles]
        article_ids = set(ids)
        self.assertEqual(sorted(article_ids), ids)
        self.assertEqual(243, len(articles))
        self.assertTrue(article_ids <= {int(json.loads(line)['article']) for line in mapping.splitlines()})
        bound = [row for row in map(json.loads, index.splitlines()) if int(row['article']) in article_ids]
        self.assertEqual(244, len(bound))
        self.assertEqual(1155, sum(row['rows'] for row in bound))
        summary = evidence['summary']
        self.assertEqual(len(articles), summary['projectedArticles'])
        self.assertEqual(len(bound), summary['projectedContexts'])
        self.assertEqual(sum(row['rows'] for row in bound), summary['projectedRows'])

        counts = Counter()
        references = set()
        for article in articles:
            self.assertLessEqual(article['discussionTimestamp'], evidence['queryCutoff'])
            self.assertGreater(article['discussionRevision'], 0)
            for notice in article['sources']:
                self.assertRegex(notice['language'], r'^[a-z][a-z0-9-]{1,15}$')
                for role, site in (('source', notice['language']), ('receiving', 'ru')):
                    revision = role + 'Revision'
                    self.assertEqual(revision in notice, revision + 'Check' in notice)
                    if revision in notice:
                        self.assertGreater(notice[revision], 0)
                        references.add((site, notice[revision]))
                        counts[role + '-' + notice[revision + 'Check']['status']] += 1
        self.assertEqual(251, sum(len(row['sources']) for row in articles))
        self.assertEqual(41, len(references))
        self.assertEqual(41, evidence['revisionReferences']['distinctQueries'])
        self.assertEqual({'source-title-matches': 23, 'source-resolves-to-same-page': 2,
                          'source-different-page': 5, 'receiving-article-matches': 10,
                          'receiving-unavailable': 2}, dict(counts))
        self.assertEqual(dict(counts), evidence['revisionReferences']['outcomes'])

    def test_holdout_source_index_covers_registered_articles_contexts_and_families(self):
        directory = check_available_v6_calibration_index.DIRECTORY.parent / 'holdout-recovery'
        raw = (directory / 'source-index.jsonl').read_bytes()
        self.assertEqual('d56fb9d7fa167f599e8414dac7190a057a2a7667ad3cad07694dbe3c850e03eb',
                         hashlib.sha256(raw).hexdigest())
        ledger = holdout_ledger.load_ledger(ROOT / 'tools/typing_experiments/holdout-ledger.json')
        registered = next(entry['keys'] for entry in ledger['entries']
                          if entry['id'] == 'public-right-context-available-v6-holdout')
        offset = 0
        articles, sentences, families = set(), set(), set()
        for record in map(json.loads, raw.splitlines()):
            self.assertEqual({'firstRow', 'rows', 'article', 'sentenceKey', 'familyKeys'}, set(record))
            self.assertEqual(offset, record['firstRow'])
            self.assertIn(record['rows'], (4, 5))
            self.assertNotIn(record['sentenceKey'], sentences)
            offset += record['rows']
            articles.update(holdout_ledger.keys_for([record], 'article'))
            sentences.add(record['sentenceKey'])
            families.update(record['familyKeys'])
        manifest = json.loads(MANIFEST.read_bytes())
        self.assertEqual(manifest['counts']['holdout']['rows'], offset)
        for axis, actual in (('article', articles), ('sentence', sentences), ('family', families)):
            self.assertEqual(set(registered[axis]), actual)

    def test_modified_rival_archive_is_refused(self):
        raw = bz2.decompress(check_available_v6_rivals.ARCHIVE.read_bytes())
        with tempfile.TemporaryDirectory() as directory:
            altered = Path(directory) / "altered.jsonl.bz2"
            altered.write_bytes(bz2.compress(raw.replace(b"dictionary-rival", b"dictionary-fault", 1)))
            with self.assertRaisesRegex(ValueError, "V6_RIVAL_ARTIFACT"):
                check_available_v6_rivals.check(altered)

    def test_aggregate_bytes_match_historical_receipt_and_failed_gate(self):
        raw = FIXTURE.read_bytes()
        self.assertEqual(ORIGINAL_SHA256, hashlib.sha256(raw).hexdigest())
        receipt = json.loads(RECEIPT.read_bytes())
        self.assertEqual([ORIGINAL_SHA256], list(find_values(receipt, ORIGINAL_PATH)))
        result = json.loads(raw)
        self.assertEqual({'calibration', 'holdout'}, set(result['parts']))
        self.assertEqual(926220, result['scannedArticles'])
        for name, expected in (('calibration', 75), ('holdout', 72)):
            part = result['parts'][name]
            self.assertEqual(expected, part['groups']['matched_copula_positive'])
            self.assertLess(expected, 400)
            self.assertEqual(part['contexts'], sum(part['groups'].values()))
            self.assertEqual(part['contexts'], sum(part['cueTypes'].values()))

    def test_altered_fixture_no_longer_matches_receipt(self):
        altered = json.loads(FIXTURE.read_bytes())
        altered['parts']['holdout']['groups']['matched_copula_positive'] = 400
        self.assertNotEqual(ORIGINAL_SHA256,
            hashlib.sha256((json.dumps(altered, indent=2) + '\n').encode()).hexdigest())

    def test_recovered_manifest_binds_exact_files_and_never_claims_qualification(self):
        raw = MANIFEST.read_bytes()
        self.assertEqual(MANIFEST_SHA256, hashlib.sha256(raw).hexdigest())
        receipt = json.loads(RECEIPT.read_bytes())
        self.assertEqual([MANIFEST_SHA256], list(find_values(receipt, MANIFEST_PATH)))
        manifest = json.loads(raw)
        self.assertEqual({'calibration.jsonl', 'calibration.tsv', 'holdout.jsonl', 'holdout.tsv'},
                         set(manifest['files']))
        for digest in manifest['files'].values():
            self.assertRegex(digest, r'^[0-9a-f]{64}$')
        self.assertEqual(7905, manifest['counts']['calibration']['rows'])
        self.assertEqual(7750, manifest['counts']['holdout']['rows'])
        self.assertFalse(manifest['fullCohortGatePassed'])
        self.assertFalse(manifest['holdoutScoringAllowed'])
        self.assertEqual(0, manifest['modelCalls'])

    def test_recovered_identity_audit_and_model_match_manifest(self):
        manifest = json.loads(MANIFEST.read_bytes())
        raw = IDENTITY_AUDIT.read_bytes()
        self.assertEqual(manifest['identityAuditSha256'], hashlib.sha256(raw).hexdigest())
        receipt = json.loads(RECEIPT.read_bytes())
        self.assertEqual([manifest['identityAuditSha256']], list(find_values(receipt,
            'build/right-context-available-clean-v6-20261027/identity-audit.json')))
        self.assertEqual(manifest['modelSha256'], hashlib.sha256(MODEL.read_bytes()).hexdigest())
        audit = json.loads(raw)
        self.assertTrue(audit['passed'])
        self.assertFalse(audit['qualityQualificationPerformed'])
        self.assertTrue(audit['priorFamilyMetadataIsNotExhaustive'])
        self.assertTrue(audit['earlierEvaluationFamiliesAllowed'])
        for part in ('calibration', 'holdout'):
            self.assertEqual(manifest['counts'][part]['rows'], audit['parts'][part]['rows'])
            self.assertEqual(manifest['counts'][part]['contexts'], audit['parts'][part]['contexts'])

    def test_recovered_exclusions_match_original_receipt_and_retained_rows(self):
        raw = FIXTURE.with_name('available_clean_v6_prior_context_exclusions.json').read_bytes()
        digest = '76e48ec2bca6d1e4dd180e83630ea080ae50e07510dbd29b324fede7e9f146c0'
        receipt = json.loads(RECEIPT.read_bytes())
        self.assertEqual([digest], list(find_values(receipt,
            'build/right-context-available-clean-v6-20261027/prior-context-exclusions.json')))
        self.assertEqual(digest, hashlib.sha256(raw).hexdigest())
        excluded = json.loads(raw)
        self.assertEqual(receipt['priorContextExclusions'], excluded)
        manifest = json.loads(MANIFEST.read_bytes())
        for part, record in excluded.items():
            self.assertEqual(manifest['counts'][part]['rows'], record['keptRows'])
            self.assertEqual(record['originalRows'] - record['keptRows'], record['removedRows'])
        self.assertEqual(2, len(excluded['holdout']['removedContextHashes']))
        self.assertEqual(10, excluded['holdout']['removedRows'])

    def test_excluded_context_anchors_bind_original_report_and_holdout_gaps(self):
        directory = check_available_v6_calibration_index.DIRECTORY.parent / 'holdout-recovery'
        raw = (directory / 'excluded-contexts.json').read_bytes()
        self.assertEqual('dc051d487f213e77682052b8a56daa60df7e6d35b7ac135035883da733145ad0',
                         hashlib.sha256(raw).hexdigest())
        receipt = json.loads(raw)
        for path, digest in receipt['inputBindings'].items():
            self.assertEqual(digest, hashlib.sha256((ROOT / path).read_bytes()).hexdigest())
        excluded = json.loads(FIXTURE.with_name('available_clean_v6_prior_context_exclusions.json').read_bytes())
        anchors = receipt['excludedContexts']
        self.assertEqual(excluded['holdout']['removedContextHashes'],
                         sorted(anchor['contextHash'] for anchor in anchors))
        recovery = json.loads((directory / 'receipt.json').read_bytes())
        self.assertEqual([gap['finalRowIndex'] for gap in recovery['sourceIDGaps']],
                         [anchor['retainedRowIndex'] for anchor in anchors])
        availability = json.loads(FIXTURE.read_bytes())['parts']
        self.assertEqual(sum(part['contexts'] for part in availability.values()), receipt['parentContexts'])
        self.assertFalse(receipt['familyExposureVerified'])
        self.assertFalse(receipt['parentContextsDigestVerified'])
        self.assertFalse(receipt['holdoutScoringAllowed'])


if __name__ == '__main__':
    unittest.main()
