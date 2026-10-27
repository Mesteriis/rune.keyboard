import json
from pathlib import Path
import tempfile
import unittest

from holdout_ledger import KEY_SCHEMA, KINDS, assert_disjoint, keys_for, load_ledger, validate_ledger


def row(**changes):
    return dict(article='123', family='готовый', families=['готовый'], prefix='Мы уже',
                typed='готвы', expectedSpelling='готовы', contextHash='a' * 64) | changes


def ledger(complete=True):
    return dict(schema=1, keySchema=KEY_SCHEMA, publicDataOnly=True,
                coverage=dict(complete=complete, pending=[] if complete else ['historical import']),
                entries=[dict(id='public-test', usage='disclosed', bindings={'rows.jsonl': 'b' * 64},
                              keys={kind: sorted(keys_for([row()], kind)) for kind in KINDS}, missingAxes=[])])


class HoldoutLedgerTest(unittest.TestCase):
    def test_known_overlap_on_every_axis_is_rejected(self):
        for kind in KINDS:
            with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:' + kind):
                assert_disjoint([row()], ledger(), kinds=(kind,))

    def test_context_is_typo_independent_normalized_and_keeps_punctuation(self):
        changed = row(prefix=' МЫ\t УЖЕ ', typed='готовв', expectedSpelling='ГОТОВЫ')
        self.assertEqual(keys_for([row()], 'context'), keys_for([changed], 'context'))
        self.assertNotEqual(keys_for([row(prefix='Мы уже,')], 'context'), keys_for([row()], 'context'))
        self.assertEqual(keys_for([row(family='е\u0308лка', families=['е\u0308лка'])], 'family'),
                         keys_for([row(families=['ЁЛКА'])], 'family'))

    def test_disjoint_data_only_passes_complete_coverage(self):
        fresh = row(article='124', families=['новый'], prefix='Совсем иначе', contextHash='c' * 64)
        assert_disjoint([fresh], ledger(), kinds=KINDS)
        with self.assertRaisesRegex(ValueError, 'LEDGER_INCOMPLETE'):
            assert_disjoint([fresh], ledger(False), kinds=KINDS)
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP'):
            assert_disjoint([row()], ledger(False), kinds=KINDS)

    def test_evaluated_family_and_supervised_family_are_distinct_profiles(self):
        data = ledger()
        same_family = row(article='124', prefix='другое', contextHash='d' * 64)
        assert_disjoint([same_family], data, kinds=('family',), usages=('supervised',))
        training = dict(id='training', usage='supervised', bindings={'families.json': 'c' * 64},
                        keys={'family': sorted(keys_for([row()], 'family'))}, missingAxes=[])
        data['entries'].append(training)
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:family'):
            assert_disjoint([same_family], data, kinds=('family',), usages=('supervised',))

    def test_missing_or_malformed_identity_cannot_be_silently_skipped(self):
        for kind, value in [('article', row(article=None)), ('article', row(article='tatoeba:1')),
                            ('family', row(families=[])), ('sentence', row(contextHash='bad')),
                            ('context', row(expectedSpelling=None))]:
            with self.assertRaises(ValueError):
                keys_for([value], kind)
        with self.assertRaisesRegex(ValueError, 'LEDGER_EMPTY_ROWS'):
            assert_disjoint([], ledger(), kinds=KINDS)

    def test_schema_hashes_duplicates_and_false_complete_flags_are_rejected(self):
        cases = []
        x = ledger(); x['schema'] = True; cases.append(x)
        x = ledger(); x['entries'] *= 2; cases.append(x)
        x = ledger(); x['entries'][0]['keys']['family'] = ['x']; cases.append(x)
        x = ledger(); x['entries'][0]['keys']['family'] *= 2; cases.append(x)
        x = ledger(); del x['entries'][0]['keys']['article']; cases.append(x)
        x = ledger(); x['entries'][0]['generatorBindings'] = {'generator.py': 'bad'}; cases.append(x)
        x = ledger(False); x['coverage']['complete'] = True; cases.append(x)
        for value in cases:
            with self.assertRaises(ValueError):
                validate_ledger(value)

    def test_serialized_ledger_checks_work_without_original_corpora(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'ledger.json'
            path.write_text(json.dumps(ledger()))
            loaded = load_ledger(path)
            with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP'):
                assert_disjoint([row(typed='другаяопечатка')], loaded, kinds=('context',))

    def test_historical_missing_axes_cannot_be_declared_complete(self):
        data = ledger(False)
        entry = data['entries'][0]
        entry['keys'] = {'context': entry['keys']['context']}
        entry['missingAxes'] = ['article', 'family', 'sentence']
        validate_ledger(data)
        data['coverage'] = dict(complete=True, pending=[])
        with self.assertRaises(ValueError):
            validate_ledger(data)

    def test_invalid_or_consumable_profiles_cannot_hide_blocked_entries(self):
        for changes in (dict(kinds='family'), dict(kinds=()), dict(usages='disclosed'),
                        dict(usages=(u for u in ['disclosed'])), dict(require_complete='false')):
            args = dict(kinds=('family',)) | changes
            with self.assertRaises(ValueError):
                assert_disjoint([row()], ledger(), **args)


if __name__ == '__main__':
    unittest.main()
