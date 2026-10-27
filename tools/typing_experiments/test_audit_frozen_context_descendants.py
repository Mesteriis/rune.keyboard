import copy
from pathlib import Path
from types import SimpleNamespace
import unittest

from audit_frozen_context_descendants import (SPECS,entries_for,folder,verify_filtered,
    verify_pool_ancestry,verify_variants)
from audit_late_authored_history import archive_path
from holdout_ledger import keys_for
from right_context_training_exclusion import exclude_training_contexts


def variants(natural=False):
    base=dict(id='0',source='source',selectionHash='s',article='123',contextHash='a'*64,
        word='готовы',rival='готов',typed='готвоы',prefix='Они',rightContext=' были дома.',
        group='typo',noAuto=False,expectedSpelling='готовы',families=['готовый'],family='готовый')
    if natural:base['cohort']='typo'
    else:base['retainBaseline']=False
    forms=[('готвоы','typo',False,False,' были дома.')]
    if not natural:forms.append(('готвоы','unfinished',False,True,' были'))
    forms.extend([('готовы','correct',True,False,' были дома.'),('@готовы','protected',True,False,' были дома.')])
    rival=('готов','correct_rival',True,False,' были дома.')
    if natural:forms.insert(-1,rival)
    else:forms.append(rival)
    result=[]
    for i,(typed,group,control,retain,suffix) in enumerate(forms):
        row=base|dict(id=str(i),typed=typed,group=group,noAuto=control,rightContext=suffix,
            expectedSpelling=typed if control else base['word'])
        if natural:row['cohort']='correct' if control else 'typo'
        else:row['retainBaseline']=retain
        result.append(row)
    return result


class Dictionary:
    def analyses(self,word):return [SimpleNamespace(lemma='готовый')] if word in ('готовы','готов') else []


class FrozenDescendantTest(unittest.TestCase):
    def test_both_variant_constructions_preserve_input_and_source_capture(self):
        for natural in (False,True):
            rows=variants(natural);before=copy.deepcopy(rows)
            self.assertEqual([rows[0]],verify_variants(rows,natural));self.assertEqual(before,rows)

    def test_changed_protected_or_unfinished_variant_cannot_hide_under_same_context(self):
        for index,field,value in [(1,'rightContext',' были дома.'),(3,'expectedSpelling','готовы'),(4,'article','456')]:
            rows=variants();rows[index][field]=value
            with self.assertRaisesRegex(ValueError,'VARIANT_IDENTITY'):verify_variants(rows)

    def test_missing_duplicate_reordered_variants_fail(self):
        for rows in (variants()[:-1],variants()+[variants()[0]],list(reversed(variants()))):
            with self.assertRaises(ValueError):verify_variants(rows)

    def test_whole_context_filter_preserves_exact_parent_order_and_audit(self):
        parent=variants();other=[r|dict(id='other-'+r['id'],contextHash='b'*64,families=['другой'],family='другой') for r in variants()]
        parent+=other;kept,audit=exclude_training_contexts(parent,['готовый'])
        self.assertEqual(audit,verify_filtered(parent,kept,['готовый'],audit))
        for changed,changed_audit in [(list(reversed(kept)),audit),(kept,audit|dict(excludedRows=0)),(parent,audit)]:
            with self.assertRaisesRegex(ValueError,'FILTER_LINEAGE'):verify_filtered(parent,changed,['готовый'],changed_audit)

    def test_natural_capture_requires_exact_pinned_pool_ancestry(self):
        row=variants(True)[0];parent={k:row[k] for k in ('source','selectionHash','word','typed','prefix','rightContext','article')}
        verify_pool_ancestry([row],[parent])
        for changed in (parent|dict(prefix='Другой'),parent|dict(source='other')):
            with self.assertRaisesRegex(ValueError,'POOL_ANCESTRY'):verify_pool_ancestry([row],[changed])
        with self.assertRaisesRegex(ValueError,'POOL_DUPLICATES'):verify_pool_ancestry([row],[parent,parent])

    def test_dictionary_families_ignore_declared_stems_and_corrupt_protected_strings(self):
        rows=variants();rows=[r|dict(family='12345',families=['12345']) for r in rows]
        entries,counts=entries_for('fixture','holdout',rows,[rows[0]],Dictionary(),{'file':'b'*64})
        self.assertEqual(keys_for([dict(families=['готовый'])],'family'),set(entries[0]['keys']['family']))
        self.assertEqual([],counts['unresolved']);self.assertEqual(1,counts['dictionaryFamilies'])

    def test_unknown_canonical_candidate_keeps_family_coverage_incomplete(self):
        rows=variants();capture=rows[0]|dict(rival='неизвестно')
        entries,counts=entries_for('fixture','holdout',rows,[capture],Dictionary(),{'file':'b'*64})
        self.assertEqual(['family'],entries[0]['missingAxes']);self.assertEqual('rival',counts['unresolved'][0]['field'])
        self.assertEqual('historical-family-exclusion',entries[1]['usage'])

    def test_four_preparation_archives_survive_without_build(self):
        archive=Path(__file__).with_name('frozen_sources')
        for name,spec in SPECS.items():
            self.assertTrue(archive_path(archive,folder(name)+'/'+spec['script'],spec['scriptSha256']).is_file())


if __name__=='__main__':unittest.main()
