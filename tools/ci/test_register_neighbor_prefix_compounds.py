import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

import register_neighbor_prefix_compounds as subject


class NeighborPrefixCompoundsTest(unittest.TestCase):
    def setUp(self):
        self.prefix = 'Текст северо-запад и Cлово дальше'
        self.rows = [{'shard': 11, 'article': '42', 'prefix': self.prefix}]

    def test_projects_full_tokens_without_inventing_families(self):
        rows = subject.project(self.rows + self.rows)
        self.assertEqual({'северо-запад', 'Cлово'}, {r['typed'] for r in rows})
        self.assertTrue(all('families' not in r for r in rows))
        self.assertEqual(1, subject.verify_sources(self.rows, {(11, '42'): self.prefix})['frames'])

    def test_prefix_edges_are_not_treated_as_complete_tokens(self):
        rows = [{'shard': 11, 'article': '42', 'prefix': 'северо-запад внутри юго-восток'}]
        self.assertEqual([], subject.project(rows))
        rows[0]['prefix'] = 'слово юго-восток-'
        self.assertEqual([], subject.project(rows))
        subject.verify_sources(rows, {(11, '42'): 'слово юго-восток-западный'})

    def test_missing_source_and_article_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'SOURCE_MISMATCH'):
            subject.verify_sources(self.rows, {(11, '42'): 'другой текст'})
        with self.assertRaisesRegex(ValueError, 'ARTICLES'):
            subject.verify_sources(self.rows, {})

    def test_fixture_mutation_rejected_even_after_rehash(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / 'fixture'
            shutil.copytree(subject.FIXTURE, fixture)
            path = fixture / 'contexts.jsonl'
            rows = [json.loads(line) for line in path.read_bytes().splitlines()]
            rows[0]['typed'] = 'подмена'
            raw = ''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in rows).encode()
            path.write_bytes(raw)
            receipt_path = fixture / 'receipt.json'
            receipt = json.loads(receipt_path.read_bytes())
            receipt['contextsSha256'] = hashlib.sha256(raw).hexdigest()
            receipt_path.write_text(json.dumps(receipt))
            with mock.patch.object(subject, 'FIXTURE', fixture):
                with self.assertRaisesRegex(ValueError, 'NEIGHBOR_COMPOUND_BINDING'):
                    subject.entries()

    def test_new_surface_is_excluded(self):
        first, _ = subject.entries()
        controls = subject.control.load(subject.CONTROL)
        old = dict(controls, entries=[e for e in controls['entries'] if e['id'] != subject.ENTRY])
        old_keys = {key for entry in old['entries'] for key in entry.get('surfaceKeys', [])}
        rows = [json.loads(line) for line in (subject.FIXTURE / 'contexts.jsonl').read_bytes().splitlines()]
        row = next(row for row in rows if subject.control.surface_key('ru', row['typed']) not in old_keys)
        row = {k: v for k, v in (row | {'prefix': 'Другой контекст'}).items() if k != 'article'}
        self.assertIn(subject.control.surface_key('ru', row['typed']), first['surfaceKeys'])
        with self.assertRaisesRegex(ValueError, 'CONTROL_SURFACE_OVERLAP'):
            subject.control.assert_disjoint([row], controls, 'regression')

    def test_new_context_is_excluded_from_lexical_holdout(self):
        ledger = subject.lexical.load_ledger(subject.LEXICAL)
        old_keys = {key for entry in ledger['entries'] if entry['id'] != subject.ENTRY+'-contexts'
                    for key in entry['keys'].get('context', [])}
        rows = [json.loads(line) for line in (subject.FIXTURE / 'contexts.jsonl').read_bytes().splitlines()]
        row = next(row for row in rows if subject.lexical.keys_for([row], 'context') - old_keys)
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:context'):
            subject.lexical.assert_disjoint([row], ledger, kinds=('context',), require_complete=False)


if __name__ == '__main__':
    unittest.main()
