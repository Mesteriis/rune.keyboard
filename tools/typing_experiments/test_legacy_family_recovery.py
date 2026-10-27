import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from holdout_ledger import KEY_SCHEMA, assert_disjoint, validate_ledger
from recover_legacy_families import build, recover_rows, sha


class Dictionary:
    def analyses(self, word):
        return [SimpleNamespace(lemma=f) for f in {'стали': ['стать', 'сталь', 'сталь'], 'слово': ['слово']}.get(word, [])]

    def receipt(self):
        return {'dictionaryOnly': True, 'packages': {}}


class FamilyRecoveryTest(unittest.TestCase):
    def test_all_dictionary_analyses_are_excluded_without_guessing_unknown_words(self):
        keys, counts = recover_rows([dict(id='a', expectedSpelling='стали'),
                                    dict(id='b', expectedSpelling='нераспознано')], Dictionary())
        from holdout_ledger import keys_for
        self.assertEqual(set(keys), keys_for([dict(families=['стать', 'сталь'])], 'family'))
        self.assertEqual(dict(rows=2, resolvedRows=1, unresolvedRows=['b']), counts)

    def test_correct_controls_use_typed_word_but_typos_require_a_target(self):
        self.assertEqual(1, recover_rows([dict(id='a', cohort='correct', typed='слово')], Dictionary())[1]['resolvedRows'])
        with self.assertRaisesRegex(ValueError, 'TARGET_MISSING'):
            recover_rows([dict(id='a', cohort='typo', typed='слово')], Dictionary())
        with self.assertRaisesRegex(ValueError, 'ROW_IDENTITY'):
            recover_rows([dict(id='a', expectedSpelling='слово')]*2, Dictionary())

    def test_addendum_preserves_parents_missing_axes_and_known_overlap_is_blocked(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for file in ('tools/morphology/ranker.py', 'tools/typing_experiments/recover_legacy_families.py'):
                (root/file).parent.mkdir(parents=True, exist_ok=True); (root/file).write_text('fixture')
            entries=[]
            for version in range(7,13):
                directory=root/str(version);directory.mkdir()
                (directory/'rows.jsonl').write_text(json.dumps(dict(id='a', expectedSpelling='стали'))+'\n')
                (directory/'manifest.json').write_text('{}')
                entries.append(dict(id=f'public-spelling-v{version}', usage='historical-exclusion', rowCount=1,
                    keys={'context':['c'*64]}, missingAxes=['article','family','sentence'],
                    bindings={str(p.relative_to(root)):sha(p) for p in directory.iterdir()}))
            base=dict(schema=1,keySchema=KEY_SCHEMA,publicDataOnly=True,
                      coverage=dict(complete=False,pending=['family recovery']),entries=entries)
            original=copy.deepcopy(base)
            enriched,receipt=build(root,base,Dictionary())
            self.assertEqual(original,base)
            self.assertEqual(original['entries'],enriched['entries'][:-1])
            self.assertFalse(enriched['coverage']['complete'])
            self.assertEqual(6,len(receipt['counts']))
            with self.assertRaisesRegex(ValueError,'LEDGER_OVERLAP:family'):
                assert_disjoint([dict(families=['сталь'])],enriched,kinds=('family',))
            with self.assertRaisesRegex(ValueError,'ALREADY_IMPORTED'):
                build(root,enriched,Dictionary())
            (root/'7/rows.jsonl').write_text('{}')
            with self.assertRaisesRegex(ValueError,'CORPUS_IDENTITY'):
                build(root,base,Dictionary())

    def test_family_only_addendum_cannot_hide_other_axes(self):
        entry=dict(id='partial', usage='historical-family-exclusion', bindings={'receipt':'a'*64},
                   keys={'context':['b'*64]},missingAxes=[])
        data=dict(schema=1,keySchema=KEY_SCHEMA,publicDataOnly=True,
                  coverage=dict(complete=False,pending=['pending']),entries=[entry])
        with self.assertRaisesRegex(ValueError,'FAMILY_SCOPE'):
            validate_ledger(data)


if __name__ == '__main__':
    unittest.main()
