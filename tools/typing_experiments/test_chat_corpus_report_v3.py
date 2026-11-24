import copy
import bz2
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import chat_corpus_report_v2 as old
import chat_corpus_report_v3 as subject
from test_chat_corpus_report_v2 import sample


def source_sample():
    row, observation = sample()
    row.update(article='tatoeba:1', clusterId='tatoeba:1', sourceRepository='tatoeba', sentenceHash='a'*64)
    return row, observation


class ClusterIntegrityTest(unittest.TestCase):
    def test_split_article_cannot_inflate_cluster_count(self):
        row, observation = source_sample()
        other = dict(row, id='two', clusterId='tatoeba:2')
        other_observation = dict(observation, id='two')
        self.assertEqual(2, old.report([row, other], [observation, other_observation])['controlClusters']['total'])
        with self.assertRaisesRegex(ValueError, 'CHAT_CLUSTER_IDENTITY'):
            subject.report([row, other], [observation, other_observation])

    def test_requires_one_control_and_consistent_source_per_article(self):
        row, observation = source_sample()
        self.assertEqual(1, subject.report([row], [observation])['controlClusters']['total'])
        with self.assertRaisesRegex(ValueError, 'CHAT_CLUSTER_CONTROL_COUNT'):
            subject.validate_clusters([row, dict(row, id='two')])
        for field, value in [('sentenceHash', 'b'*64), ('prefix', 'другой'), ('expectedSpelling', 'текст')]:
            with self.subTest(field=field):
                changed = dict(row, id='two', edit_kind='vowel_oa', **{field: value})
                with self.assertRaisesRegex(ValueError, 'CHAT_CLUSTER_INCONSISTENT'):
                    subject.validate_clusters([row, changed])

    def test_missing_identity_and_false_undo_are_refused(self):
        row, observation = source_sample()
        for field in ('sourceRepository', 'article', 'sentenceHash', 'clusterId'):
            altered = dict(row)
            del altered[field]
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'CHAT_CLUSTER_IDENTITY'):
                subject.report([altered], [observation])
        altered = copy.deepcopy(observation)
        altered['afterBackspace']['text'] = 'другое'
        with self.assertRaisesRegex(ValueError, 'CHAT_UNDO_FLAG_MISMATCH'):
            subject.report([row], [altered])

    def test_cli_rejects_invalid_cluster_without_output(self):
        row, observation = source_sample()
        row['clusterId'] = 'tatoeba:2'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows, observations, output = (root/name for name in ('rows.jsonl', 'obs.jsonl', 'out.json'))
            rows.write_text(json.dumps(row, ensure_ascii=False)+'\n')
            observations.write_text(json.dumps(observation, ensure_ascii=False)+'\n')
            source, lock, ledger = (root/name for name in ('source', 'lock', 'ledger'))
            for path in (source, lock, ledger):
                path.write_bytes(b'fixture')
            result = subprocess.run([sys.executable, str(Path(subject.__file__)), '--rows', str(rows),
                                     '--observations', str(observations), '--source', str(source),
                                     '--lock', str(lock), '--ledger', str(ledger), '--output', str(output)],
                                    capture_output=True, text=True)
            self.assertNotEqual(0, result.returncode)
            self.assertIn('CHAT_CLUSTER_IDENTITY', result.stderr)
            self.assertFalse(output.exists())

    def test_real_source_reproduction_rejects_consistent_but_forged_identity(self):
        root = Path(subject.__file__).resolve().parent
        source = (root/'public_sources/tatoeba-ru-cc0-20261024/rus_sentences_CC0.tsv.bz2').read_bytes()
        lock = (root/'public_sources/tatoeba-ru-cc0-20261024/tatoeba-source-lock.json').read_bytes()
        ledger_raw = (root/'holdout-ledger.json').read_bytes()
        ledger = subject.holdout_ledger.validate_ledger(json.loads(ledger_raw))
        excluded = {v for entry in ledger['entries'] for v in entry['keys'].get('article', [])}
        rows, _ = subject.chat_corpus.generate(bz2.decompress(source).decode('utf-8').splitlines(keepends=True), excluded)
        payload = lambda values: ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':'))+'\n'
                                         for r in values).encode()
        raw = payload(rows)
        subject.verify_source_rows(raw, source, lock, ledger_raw)
        old_article = rows[0]['article']
        for row in rows:
            if row['article'] == old_article:
                row['article'] = row['clusterId'] = 'tatoeba:999999999999999'
        subject.validate_clusters(rows)
        with self.assertRaisesRegex(ValueError, 'CHAT_SOURCE_ROWS_MISMATCH'):
            subject.verify_source_rows(payload(rows), source, lock, ledger_raw)
        with self.assertRaisesRegex(ValueError, 'CHAT_SOURCE_IDENTITY'):
            subject.verify_source_rows(raw, source+b'x', lock, ledger_raw)
        with self.assertRaisesRegex(ValueError, 'CHAT_SOURCE_LOCK'):
            subject.verify_source_rows(raw, source, lock+b' ', ledger_raw)


if __name__ == '__main__':
    unittest.main()
