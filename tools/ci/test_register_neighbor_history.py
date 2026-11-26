import copy
from collections import Counter
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

import register_neighbor_history as subject


class NeighborHistoryTest(unittest.TestCase):
    def test_project_keeps_typo_and_target_surface_and_context(self):
        row = {'article': '42', 'prefix': 'hello ', 'typed': 'ошипка', 'word': 'ошибка', 'expected': 'ошибка'}
        result = subject.project([row])
        base = {'article': '42', 'language': 'ru', 'prefix': 'hello ',
                'typed': 'ошипка', 'expectedSpelling': 'ошибка'}
        self.assertEqual(subject.lexical.keys_for([base], 'context'), set(result['context']))
        self.assertEqual({subject.control.surface_key('ru', 'ошипка'),
                          subject.control.surface_key('ru', 'ошибка')}, set(result['surface']))
        self.assertEqual(2, len(result['regression']))
        self.assertEqual(1, len(result['article']))

    def test_protected_expected_target_has_its_own_context(self):
        row = {'article': '42', 'prefix': 'hello ', 'typed': 'слово42', 'word': 'слово', 'expected': 'слово42'}
        result = subject.project([row])
        self.assertEqual(2, len(result['context']))
        for target in ('слово', 'слово42'):
            candidate = {'prefix': 'hello ', 'typed': 'слово42', 'expectedSpelling': target}
            self.assertTrue(subject.lexical.keys_for([candidate], 'context') <= set(result['context']))

    def test_retained_inputs_have_exact_scope_and_detect_mutation(self):
        rows, _ = subject.inputs()
        self.assertEqual(15000, len(rows))
        self.assertEqual(2426, len({row['article'] for row in rows}))
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder) / 'fixture'
            shutil.copytree(subject.FIXTURE, fixture)
            with (fixture / 'holdout.jsonl').open('ab') as stream:
                stream.write(b'changed')
            with mock.patch.object(subject, 'FIXTURE', fixture):
                with self.assertRaisesRegex(ValueError, 'NEIGHBOR_HISTORY_ROWS'):
                    subject.inputs()

    def test_numeric_family_ids_are_not_promoted_to_lemma_keys(self):
        entry, controls = subject.entries()
        self.assertEqual({'article', 'context'}, set(entry['keys']))
        self.assertEqual({'family', 'sentence'}, set(entry['missingAxes']))
        self.assertEqual(15000, entry['rowCount'])
        self.assertEqual(30000, controls['rowCount'])
        self.assertEqual(15000, len(controls['surfaceKeys']))

    def test_v6_collision_articles_resolve_to_bound_neighbor_rows(self):
        rows, _ = subject.inputs()
        ledger = subject.lexical.load_ledger(subject.LEXICAL)
        entries = {entry['id']: entry for entry in ledger['entries']}
        neighbor = entries[subject.ENTRY]
        by_key = {next(iter(subject.lexical.keys_for([{'article': article}], 'article'))): article
                  for article in {row['article'] for row in rows}}
        self.assertEqual(set(neighbor['keys']['article']), set(by_key))
        for part, expected in (
            ('calibration', (26, {'train':108, 'calibration':18, 'holdout':54})),
            ('holdout', (25, {'train':66, 'calibration':48, 'holdout':36})),
        ):
            with self.subTest(part=part):
                target = entries['public-right-context-available-v6-' + part]
                keys = set(target['keys']['article']) & set(by_key)
                articles = {by_key[key] for key in keys}
                counts = Counter(row['split'] for row in rows if row['article'] in articles)
                self.assertEqual(expected, (len(articles), dict(counts)))
                self.assertFalse(set(target['keys']['context']) & set(neighbor['keys']['context']))


if __name__ == '__main__':
    unittest.main()
