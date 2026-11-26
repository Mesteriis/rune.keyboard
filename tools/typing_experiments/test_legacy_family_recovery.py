import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from holdout_ledger import KEY_SCHEMA, assert_disjoint, validate_ledger
from recover_legacy_families import build, recover_rows, sha
import import_word_history_families as word_history
import import_epoch_history_families as epoch_history
import audit_refinement_coverage as refinement_coverage


class Dictionary:
    def analyses(self, word):
        return [SimpleNamespace(lemma=f) for f in {'стали': ['стать', 'сталь', 'сталь'], 'слово': ['слово']}.get(word, [])]

    def receipt(self):
        return {'dictionaryOnly': True, 'packages': {}}


class FamilyRecoveryTest(unittest.TestCase):
    def test_refinement_audit_requires_training_scope_and_exact_unknown_quarantine(self):
        from holdout_ledger import keys_for
        from source_identities import unsupported_surface_key
        rows={}
        for part,split,target in [('train','calibration','стали'),('dev','diagnostic','стали'),('test','holdout','нераспознано')]:
            rows[part]=[dict(id=part,articleId='123',language='ru',partition=part,split=split,cohort='typo',
                             noAuto=False,expectedSpelling=target,typed='опечатка',prefix='мы')]
        flat=[r for group in rows.values() for r in group]
        keys={'article':sorted(keys_for([dict(article='123')],'article')),'context':sorted(keys_for(flat,'context'))}
        family=sorted(keys_for([dict(families=['стать','сталь'])],'family'))
        base=dict(schema=1,keySchema=KEY_SCHEMA,publicDataOnly=True,coverage=dict(complete=False,pending=['pending']),entries=[
            dict(id='source',usage='historical-exclusion',bindings={'source':'a'*64},keys=keys,missingAxes=['family','sentence'],
                 unsupportedSurfaceKeys=[unsupported_surface_key('нераспознано')]),
            dict(id='train',usage='supervised',bindings={'source':'a'*64},keys={'family':family},missingAxes=[])])
        with patch.object(refinement_coverage,'EXPECTED',{'train':1,'dev':1,'test':1}):
            result=refinement_coverage.audit(base,rows,Dictionary(),{'source':'a'*64})
            self.assertEqual(1,result['counts']['test']['unsupportedRows'])
            self.assertIs(False,result['independentQualification'])
            changed=copy.deepcopy(base);changed['entries'][1]['usage']='historical-family-exclusion'
            with self.assertRaisesRegex(ValueError,'REFINEMENT_COVERAGE_GAP:train'):
                refinement_coverage.audit(changed,rows,Dictionary(),{'source':'a'*64})
            changed=copy.deepcopy(base);changed['entries'][0].pop('unsupportedSurfaceKeys')
            with self.assertRaisesRegex(ValueError,'REFINEMENT_COVERAGE_GAP:test'):
                refinement_coverage.audit(changed,rows,Dictionary(),{'source':'a'*64})
            bad=copy.deepcopy(rows);bad['test'][0]['id']='train'
            with self.assertRaisesRegex(ValueError,'REFINEMENT_COVERAGE_IDS'):
                refinement_coverage.audit(base,bad,Dictionary(),{'source':'a'*64})
            bad=copy.deepcopy(rows);bad['test'][0]['split']='calibration'
            with self.assertRaisesRegex(ValueError,'REFINEMENT_COVERAGE_SCOPE'):
                refinement_coverage.audit(base,bad,Dictionary(),{'source':'a'*64})

    def test_extra_epoch_test_families_stay_distinct_from_supervised_training(self):
        from holdout_ledger import keys_for
        article=sorted(keys_for([dict(article='123')],'article'))
        base=dict(schema=1,keySchema=KEY_SCHEMA,publicDataOnly=True,coverage=dict(complete=False,pending=['pending']),entries=[
            dict(id=epoch_history.PARENT,usage='historical-exclusion',bindings={'source':'a'*64},
                 keys={'article':article},missingAxes=['family','sentence','context'])])
        original=copy.deepcopy(base)
        rows=[dict(id='a',articleId='123',language='ru',partition='test',split='holdout',cohort='typo',
                   noAuto=False,expectedSpelling='стали',typed='стмли')]
        updated,receipt=epoch_history.build(base,rows,Dictionary(),{'source':'b'*64})
        self.assertEqual(original,base);self.assertEqual(original['entries'],updated['entries'][:-1])
        self.assertEqual('historical-family-exclusion',updated['entries'][-1]['usage'])
        self.assertFalse(receipt['supervisedTrainingClaim'])
        with self.assertRaisesRegex(ValueError,'LEDGER_OVERLAP:family'):
            assert_disjoint([dict(families=['сталь'])],updated,kinds=('family',),require_complete=False)
        assert_disjoint([dict(families=['сталь'])],updated,kinds=('family',),
                        usages=('supervised','prepared-training-quarantine'),require_complete=False)
        with self.assertRaisesRegex(ValueError,'EPOCH_FAMILY_SCOPE'):
            epoch_history.build(base,[rows[0]|dict(partition='train')],Dictionary(),{'source':'b'*64})
        with self.assertRaisesRegex(ValueError,'EPOCH_FAMILY_ALREADY_IMPORTED'):
            epoch_history.build(updated,rows,Dictionary(),{'source':'b'*64})

    def test_word_history_quarantines_all_analyses_and_unknown_exact_surface(self):
        from holdout_ledger import keys_for
        from source_identities import unsupported_surface_key
        from test_public_corpus_preparation_v1 import candidate,controls
        from public_corpus_preparation_v1 import preflight
        article=sorted(keys_for([dict(article='123')],'article'))
        base=dict(schema=1,keySchema=KEY_SCHEMA,publicDataOnly=True,coverage=dict(complete=False,pending=['pending']),entries=[
            dict(id=word_history.PARENTS[0],usage='historical-exclusion',bindings={'rows':'a'*64},
                 keys={'article':article},missingAxes=['family','sentence','context']),
            dict(id=word_history.PARENTS[1],usage='historical-context-exclusion',bindings={'rows':'a'*64},
                 keys={'context':['b'*64]},missingAxes=[])])
        original=copy.deepcopy(base)
        rows=[dict(id='a',articleId='123',language='ru',partition='train',cohort='typo',noAuto=False,
                   expectedSpelling='стали',typed='стмли'),
              dict(id='b',articleId='123',language='ru',partition='dev',cohort='correct',noAuto=True,
                   expectedSpelling='нераспознано',typed='нераспознано')]
        updated,receipt=word_history.build(base,rows,Dictionary(),{'source':'c'*64})
        self.assertEqual(original,base);self.assertEqual(original['entries'],updated['entries'][:-1])
        self.assertEqual(1,receipt['counts']['unsupportedRows'])
        self.assertEqual(unsupported_surface_key('нераспознано'),updated['entries'][-1]['unsupportedSurfaceKeys'][0])
        with self.assertRaisesRegex(ValueError,'LEDGER_OVERLAP:family'):
            assert_disjoint([dict(families=['сталь'])],updated,kinds=('family',),
                            usages=('supervised','prepared-training-quarantine'),require_complete=False)
        result=preflight([candidate(typed='нераспознано',expectedSpelling='нераспознано')],
                         'spelling',updated,controls())
        self.assertEqual(1,result['unsupportedTargetOverlaps'])
        with self.assertRaisesRegex(ValueError,'WORD_FAMILY_ARTICLE'):
            word_history.derive([rows[0]|dict(articleId='124')],Dictionary(),set(article))
        with self.assertRaisesRegex(ValueError,'WORD_FAMILY_ROW_ID'):
            word_history.derive([rows[0],rows[0]],Dictionary(),set(article))
        with self.assertRaisesRegex(ValueError,'WORD_FAMILY_ALREADY_IMPORTED'):
            word_history.build(updated,rows,Dictionary(),{'source':'c'*64})

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
